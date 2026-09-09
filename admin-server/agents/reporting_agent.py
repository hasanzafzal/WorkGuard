"""Phase 8: Reporting Agent for WorkGuard.

Implements the forensic reporting workflow using LangGraph:
    PostgreSQL
        │
        ├── Daily statistics (get_daily_summary)
        ├── Application statistics (get_application_usage)
        ├── Session statistics (get_sessions)
        └── Security events (security.rules)
                │
                ▼
          Reporting Agent (LangGraph)
                │
                ▼
              Ollama
                │
                ▼
        Executive Markdown Report

Key Principle:
    Consumes structured statistics and relevant retrieved information rather
    than arbitrary raw database tables.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langgraph.graph import StateGraph, END

from agents.state import ReportingAgentState
from llm.ollama_client import get_ollama_client
from retrieval.structured import (
    get_employee,
    list_employees,
    get_sessions,
    get_application_usage,
    get_daily_summary,
    get_project_file_activity,
)
from security.rules import evaluate_security_telemetry
from database.connection import get_connection

logger = logging.getLogger(__name__)

REPORTING_SYSTEM_PROMPT = (
    "You are WorkGuard Executive Reporting Agent. Your task is to compile a formal, high-impact "
    "forensic activity report for corporate leadership based strictly on verified workstation telemetry.\n"
    "Strict Guidelines:\n"
    "1. Quote exact numbers, durations, percentages, and metrics provided in the context. Never invent data.\n"
    "2. Format your response cleanly in GitHub-style Markdown with clear headings (Executive Summary, "
    "Work Breakdown, Applications, Project Files, Security & Risk, Recommendations).\n"
    "3. Keep your tone objective, professional, and audit-ready."
)


def _resolve_employee(query: str) -> tuple[str | None, str | None]:
    """Extract employee ID and display name from natural language query."""
    q = query.lower()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT employee_id, employee_name, username FROM employees;")
            for eid, ename, uname in cur.fetchall():
                e_lower = (ename or "").lower()
                u_lower = (uname or "").lower()
                id_lower = eid.lower()
                first_name = u_lower.split(".")[0] if "." in u_lower else u_lower

                if (
                    id_lower in q
                    or u_lower in q
                    or e_lower in q
                    or (first_name and len(first_name) >= 3 and first_name in q)
                ):
                    return eid, (ename or uname)
    finally:
        conn.close()
    return None, None


def node_prepare_report_scope(state: ReportingAgentState) -> dict[str, Any]:
    """Node 1: Identify the employee, date, and scope for the report."""
    query = state.get("query", "")
    emp_id = state.get("employee_id")
    emp_name = state.get("employee_name")
    date_str = state.get("date")

    # Extract date if present
    if not date_str:
        d_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", query)
        if d_match:
            date_str = d_match.group(1)

    # Extract employee if present
    if not emp_id:
        p_id, p_name = _resolve_employee(query)
        emp_id = p_id
        emp_name = p_name

    scope = "employee" if emp_id else "enterprise"
    return {
        "employee_id": emp_id,
        "employee_name": emp_name,
        "date": date_str,
        "scope": scope,
    }


def node_aggregate_report_metrics(state: ReportingAgentState) -> dict[str, Any]:
    """Node 2: Retrieve structured statistics from PostgreSQL."""
    emp_id = state.get("employee_id")
    date_str = state.get("date")
    sources = []

    # 1. Employee Profile
    profile = None
    if emp_id:
        profile = get_employee(emp_id)
        if profile:
            sources.append(f"PostgreSQL: employees ({emp_id})")

    # 2. Daily Summary or Total Sessions
    daily_stats = None
    if emp_id and date_str:
        daily_stats = get_daily_summary(emp_id, date_str)
        sources.append(f"PostgreSQL: daily_summary ({date_str})")

    sessions_list = get_sessions(employee_id=emp_id, date=date_str, limit=20)
    sources.append("PostgreSQL: sessions")

    # 3. Application Focus
    app_usage = get_application_usage(employee_id=emp_id, date=date_str, limit=15)
    sources.append("PostgreSQL: application_focus & application_catalog")

    # 4. Project File Activity
    file_activity = get_project_file_activity(employee_id=emp_id, limit=8)
    sources.append("PostgreSQL: directory_activity & process_events")

    # 5. Security Audit
    sec_eval = evaluate_security_telemetry(employee_id=emp_id, date_str=date_str)
    sources.append("PostgreSQL: security analytics rules")

    # 6. Retrieve distinct processes executed
    all_processes: list[str] = []
    total_started = 0
    total_stopped = 0
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if emp_id:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(processes_started), 0), COALESCE(SUM(processes_stopped), 0)
                    FROM session_activity_summary sas
                    JOIN sessions s ON sas.session_id = s.session_id
                    WHERE s.employee_id = %s;
                    """,
                    (emp_id,),
                )
                p_counts = cur.fetchone()
                if p_counts:
                    total_started = int(p_counts[0])
                    total_stopped = int(p_counts[1])

                cur.execute(
                    """
                    SELECT DISTINCT process_name
                    FROM process_events pe
                    JOIN sessions s ON pe.session_id = s.session_id
                    WHERE s.employee_id = %s
                    ORDER BY process_name ASC
                    LIMIT 25;
                    """,
                    (emp_id,),
                )
                all_processes = [r[0] for r in cur.fetchall() if r[0]]
    except Exception as exc:
        logger.warning("Could not fetch detailed process telemetry: %s", exc)
    finally:
        conn.close()

    total_duration = sum(s.get("duration_seconds", 0) for s in sessions_list)
    total_prod = sum(s.get("productive_seconds") or 0 for s in sessions_list)
    # If productive_seconds wasn't computed on session level, sum from app_usage
    if total_prod == 0 and app_usage:
        total_prod = int(sum(
            a.get("total_focus_seconds", 0)
            for a in app_usage
            if a.get("is_productive") is True or (a.get("is_productive") is None and a.get("process_name") != "Desktop")
        ))
    prod_pct = round((total_prod / max(total_duration, 1)) * 100, 1)

    # Recalculate focus percentages relative to total duration
    formatted_apps = []
    for a in app_usage:
        sec = a.get("total_focus_seconds", 0)
        pct = round((sec / max(total_duration, 1)) * 100, 1)
        formatted_apps.append({
            **a,
            "calculated_pct": pct,
        })

    ename = state.get("employee_name") or (profile["employee_name"] if profile else "Enterprise-Wide")

    metrics_bundle = {
        "profile": profile,
        "daily_stats": daily_stats,
        "sessions_count": len(sessions_list),
        "sessions": sessions_list,
        "total_duration_seconds": total_duration,
        "productive_seconds": total_prod,
        "productivity_percentage": prod_pct,
        "applications": formatted_apps,
        "processes_used": all_processes,
        "processes_started": total_started,
        "processes_stopped": total_stopped,
        "file_activity": file_activity,
        "security": sec_eval,
    }

    return {
        "metrics_bundle": metrics_bundle,
        "sources": sources,
    }


def node_synthesize_report(state: ReportingAgentState) -> dict[str, Any]:
    """Node 3: Synthesize comprehensive executive Markdown report."""
    query = state.get("query", "")
    mb = state.get("metrics_bundle", {})
    emp_id = state.get("employee_id") or "Enterprise"
    emp_name = state.get("employee_name") or "Employee"
    date_str = state.get("date")

    total_dur = mb.get("total_duration_seconds", 0)
    dur_min = round(total_dur / 60, 1)
    prod_sec = mb.get("productive_seconds", 0)
    prod_min = round(prod_sec / 60, 1)
    prod_pct = mb.get("productivity_percentage", 0.0)
    sess_count = mb.get("sessions_count", 0)
    apps = mb.get("applications", [])
    processes = mb.get("processes_used", [])
    sec = mb.get("security", {})
    r_level = sec.get("risk_level", "LOW")
    r_score = sec.get("risk_score", 0)
    findings = sec.get("findings", [])
    sessions = mb.get("sessions", [])

    # Productivity evaluation badge
    if prod_pct >= 70:
        prod_badge = "Optimal (High Engagement)"
    elif prod_pct >= 45:
        prod_badge = "Standard Engagement"
    else:
        prod_badge = "Low / Diverted Engagement"

    # Attempt fast qualitative summary via Ollama with 12s timeout
    ollama_summary = ""
    ollama_recs = []
    top_apps = [a.get("display_name") or a.get("process_name") for a in apps[:4]]
    prompt = (
        f"Employee: {emp_name} ({emp_id})\n"
        f"Telemetry: {sess_count} sessions, {dur_min}m duration, {prod_min}m productive ({prod_pct}%).\n"
        f"Top tools: {', '.join(top_apps) if top_apps else 'Uncataloged'}.\n"
        f"Risk: {r_level} ({r_score}/100), {len(findings)} anomalies.\n\n"
        f"Provide:\n"
        f"1. Executive Summary (2-3 sentences)\n"
        f"2. Three actionable recommendations"
    )

    try:
        ollama = get_ollama_client()
        resp = ollama.generate_completion(
            prompt=prompt,
            system_prompt=REPORTING_SYSTEM_PROMPT,
            temperature=0.2,
            num_predict=300,
            timeout=5,
        )
        if resp and len(resp) > 60:
            ollama_summary = resp
    except Exception as exc:
        logger.info("Fast Ollama summary skipped (%s) — using deterministic executive synthesis", exc)

    # Fallback / Deterministic executive summary
    if not ollama_summary:
        exec_summary_text = (
            f"This executive activity report synthesizes verified forensic workstation telemetry for **{emp_name}** "
            f"covering **{sess_count} ingested sessions** with a cumulative duration of **{dur_min} minutes** ({total_dur}s). "
            f"Active productive engagement was measured at **{prod_min} minutes** ({prod_pct}% of session duration), "
            f"with primary focus observed in **{', '.join(top_apps) if top_apps else 'system utilities'}**. "
            f"The overall compliance and security posture is rated **{r_level}** with a risk score of **{r_score}/100**."
        )
    else:
        exec_summary_text = ollama_summary

    # Build comprehensive GitHub-flavored Markdown
    md_lines = []
    md_lines.append(f"# Executive Activity & Forensic Report: {emp_name}")
    md_lines.append(f"**Target ID:** `{emp_id}` | **Audit Date:** {date_str or 'All Ingested Telemetry'} | **Status:** `Verified Authoritative`")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## Executive Summary")
    md_lines.append(exec_summary_text)
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("## Workstation Productivity Accounting")
    md_lines.append("")
    md_lines.append("| Metric | Measured Value | Evaluation & Context |")
    md_lines.append("| :--- | :--- | :--- |")
    md_lines.append(f"| **Total Monitored Sessions** | **{sess_count}** | Complete ingested packages |")
    md_lines.append(f"| **Cumulative Workstation Time** | **{dur_min} min** ({total_dur}s) | Total elapsed clock time |")
    md_lines.append(f"| **Productive Focus Work Time** | **{prod_min} min** ({prod_sec}s) | Active foreground software work |")
    md_lines.append(f"| **Productivity Index** | **{prod_pct}%** | `{prod_badge}` |")
    md_lines.append(f"| **Processes Started / Stopped** | **{mb.get('processes_started', 0)} / {mb.get('processes_stopped', 0)}** | Operational process lifecycle |")
    md_lines.append("")

    # Application Breakdown Table
    md_lines.append("## Application & Focus Distribution")
    md_lines.append("")
    if apps:
        md_lines.append("| Application | Process | Category | Focus Time | Focus Share | Productive |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for a in apps:
            disp = a.get("display_name") or a.get("process_name")
            pname = a.get("process_name")
            cat = (a.get("category") or "general").capitalize()
            f_sec = a.get("total_focus_seconds", 0)
            f_min = round(f_sec / 60, 1)
            pct = a.get("calculated_pct", 0.0)
            is_prod = "Yes" if a.get("is_productive") is True or (a.get("is_productive") is None and pname != "Desktop") else "Neutral"
            md_lines.append(f"| **{disp}** | `{pname}` | {cat} | {f_min}m ({int(f_sec)}s) | **{pct}%** | {is_prod} |")
    else:
        md_lines.append("*No foreground application telemetry recorded for this timeframe.*")
    md_lines.append("")

    # Process Telemetry & Operational Activity
    md_lines.append("## Process Execution & Tool Activity")
    md_lines.append("")
    if processes:
        md_lines.append(f"A total of **{len(processes)} unique processes** were executed during the observed period:")
        md_lines.append("")
        proc_badges = [f"`{p}`" for p in processes]
        md_lines.append(" - ".join(proc_badges))
    else:
        md_lines.append("*No standalone process execution events captured.*")
    md_lines.append("")

    # Session Timeline Breakdown
    if sessions:
        md_lines.append("## Session Timeline & Audit Trail")
        md_lines.append("")
        md_lines.append("| Session ID | Start Timestamp | Duration | Active Time | Primary Applications |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for s in sessions[:8]:
            sid = s.get("session_id", "")
            st = (s.get("start_time") or "")[:19].replace("T", " ")
            dur = round((s.get("duration_seconds") or 0) / 60, 1)
            act = round((s.get("active_seconds") or s.get("duration_seconds") or 0) / 60, 1)
            s_apps = s.get("applications_used") or []
            app_str = ", ".join(s_apps[:3]) if s_apps else "System"
            md_lines.append(f"| `{sid[:12]}` | {st} | {dur}m | {act}m | {app_str} |")
        md_lines.append("")

    # Security & Compliance Section
    md_lines.append("## Security & Compliance Audit")
    md_lines.append("")
    md_lines.append(f"- **Calculated Risk Level:** `{r_level}`")
    md_lines.append(f"- **Composite Risk Score:** **{r_score} / 100**")
    md_lines.append(f"- **Policy Anomalies Detected:** **{len(findings)}**")
    md_lines.append("")
    if findings:
        for f in findings:
            md_lines.append(f"- **[{f.get('severity', 'INFO')}] {f.get('rule')}:** {f.get('description')}")
    else:
        md_lines.append("[Clean Audit] **No policy violations or abnormal behavioral indicators detected.** All sessions operated within authorized corporate workstation guidelines.")
    md_lines.append("")

    # Recommendations
    md_lines.append("## Recommended Leadership Actions")
    md_lines.append("")
    if prod_pct >= 70:
        md_lines.append("1. **Maintain Current Workflow**: Employee demonstrates high active engagement in primary development and productivity tooling.")
        md_lines.append("2. **Periodic Reviews**: Continue automated routine telemetry tracking without requiring targeted supervision.")
        md_lines.append("3. **Tool Access**: Ensure uninterrupted licensing and system resources for primary development software.")
    elif prod_pct >= 45:
        md_lines.append("1. **Workflow Alignment**: Conduct periodic check-ins to ensure tooling configuration aligns with primary project milestones.")
        md_lines.append("2. **Catalog Refinement**: Review uncataloged processes to verify if additional internal tooling should be marked as productive.")
        md_lines.append("3. **Focus Optimization**: Encourage dedicated focus blocks to minimize application switching.")
    else:
        md_lines.append("1. **Engagement Assessment**: Review task distribution and work assignment to understand low active workstation engagement.")
        md_lines.append("2. **Telemetry Validation**: Confirm employee workstation client is active during working shifts and not running idle.")
        md_lines.append("3. **Direct Check-in**: Align expectations on deliverables and monitored project requirements.")

    final_report = "\n".join(md_lines)

    return {
        "final_answer": final_report,
    }


def get_reporting_agent():
    """Build and compile the LangGraph Reporting Agent."""
    builder = StateGraph(ReportingAgentState)
    builder.add_node("prepare_scope", node_prepare_report_scope)
    builder.add_node("aggregate_metrics", node_aggregate_report_metrics)
    builder.add_node("synthesize_report", node_synthesize_report)

    builder.set_entry_point("prepare_scope")
    builder.add_edge("prepare_scope", "aggregate_metrics")
    builder.add_edge("aggregate_metrics", "synthesize_report")
    builder.add_edge("synthesize_report", END)

    return builder.compile()


def run_reporting_agent(
    query: str,
    employee_id: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Entry point to execute the Reporting Agent."""
    app = get_reporting_agent()
    initial_state: ReportingAgentState = {
        "query": query,
        "employee_id": employee_id,
        "date": date,
    }

    final_state = app.invoke(initial_state)

    return {
        "query": query,
        "employee_id": final_state.get("employee_id"),
        "employee_name": final_state.get("employee_name"),
        "date": final_state.get("date"),
        "scope": final_state.get("scope"),
        "answer": final_state.get("final_answer", ""),
        "sources": final_state.get("sources", []),
        "metrics": final_state.get("metrics_bundle", {}),
    }
