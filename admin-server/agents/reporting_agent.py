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

    sessions_list = get_sessions(employee_id=emp_id, date=date_str, limit=10)
    sources.append("PostgreSQL: sessions")

    # 3. Application Focus
    app_usage = get_application_usage(employee_id=emp_id, date=date_str, limit=8)
    sources.append("PostgreSQL: application_focus & application_catalog")

    # 4. Project File Activity
    file_activity = get_project_file_activity(employee_id=emp_id, limit=5)
    sources.append("PostgreSQL: directory_activity & process_events")

    # 5. Security Audit
    sec_eval = evaluate_security_telemetry(employee_id=emp_id, date_str=date_str)
    sources.append("PostgreSQL: security analytics rules")

    # Build formatted data bundle for the LLM
    sections = []

    # Section A: Target Info
    ename = state.get("employee_name") or (profile["employee_name"] if profile else "All Employees")
    sections.append(f"REPORT TARGET: {ename} (ID: {emp_id or 'Enterprise'})")
    if date_str:
        sections.append(f"TIMEFRAME: {date_str}")
    else:
        sections.append("TIMEFRAME: All Ingested Telemetry")

    # Section B: Session Overview
    total_duration = sum(s.get("duration_seconds", 0) for s in sessions_list)
    total_prod = sum(s.get("productive_seconds", 0) for s in sessions_list)
    prod_pct = round((total_prod / max(total_duration, 1)) * 100, 1)
    sections.append("\nWORK & PRODUCTIVITY METRICS:")
    sections.append(f"- Total Ingested Sessions: {len(sessions_list)}")
    sections.append(f"- Cumulative Session Duration: {round(total_duration/60, 1)} minutes ({total_duration}s)")
    sections.append(f"- Productive Active Focus Time: {round(total_prod/60, 1)} minutes ({total_prod}s)")
    sections.append(f"- Overall Productivity Index: {prod_pct}%")

    # Section C: Application Breakdown
    sections.append("\nAPPLICATION FOCUS BREAKDOWN:")
    for a in app_usage:
        app_name = a.get("display_name") or a.get("process_name")
        sec = a.get("total_focus_seconds", 0)
        pct = a.get("focus_percentage", 0.0)
        category = a.get("category", "uncataloged")
        sections.append(f"- {app_name} [{category}]: {round(sec/60, 1)}m ({sec}s, {pct}%)")

    # Section D: Project & File Operations
    sections.append("\nPROJECT & DIRECTORY ACTIVITY:")
    if file_activity:
        for f in file_activity:
            dpath = f.get("directory_path", "Root")
            sec = f.get("active_seconds", 0)
            sections.append(f"- Directory: `{dpath}` (Active Work: {round(sec/60, 1)}m, {sec}s)")
    else:
        sections.append("- No explicit project directory operations recorded.")

    # Section E: Security Findings
    r_score = sec_eval.get("risk_score", 0)
    r_level = sec_eval.get("risk_level", "LOW")
    findings = sec_eval.get("findings", [])
    sections.append(f"\nSECURITY & RISK COMPLIANCE POSTURE:")
    sections.append(f"- Risk Level: {r_level} (Score: {r_score}/100)")
    sections.append(f"- Total Detected Anomalies: {len(findings)}")
    for f in findings:
        sections.append(f"  * [{f.get('severity')}] {f.get('rule')}: {f.get('description')}")

    metrics_bundle = {
        "profile": profile,
        "daily_stats": daily_stats,
        "sessions_count": len(sessions_list),
        "total_duration_seconds": total_duration,
        "productive_seconds": total_prod,
        "productivity_percentage": prod_pct,
        "applications": app_usage,
        "file_activity": file_activity,
        "security": sec_eval,
    }

    return {
        "metrics_bundle": metrics_bundle,
        "formatted_report": "\n".join(sections),
        "sources": sources,
    }


def node_synthesize_report(state: ReportingAgentState) -> dict[str, Any]:
    """Node 3: Synthesize comprehensive Markdown report using Ollama."""
    query = state.get("query", "")
    context = state.get("formatted_report", "")
    ollama = get_ollama_client()

    prompt = f"""Administrator Request: {query}

Verified Forensic Workstation Telemetry:
\"\"\"
{context}
\"\"\"

Synthesize a comprehensive, executive forensic activity report in clean Markdown. Include:
1. Executive Summary (2-3 sentences overview)
2. Productivity Accounting (Metrics & breakdown)
3. Application & Focus Distribution
4. Security & Compliance Findings
5. Recommended Follow-up Actions"""

    try:
        report = ollama.generate_completion(
            prompt=prompt,
            system_prompt=REPORTING_SYSTEM_PROMPT,
            temperature=0.1,
            num_predict=350,
        )
    except Exception as e:
        logger.error("LLM report generation failed: %s", e)
        report = (
            f"# Forensic Activity Report\n\n"
            f"**Automated Summary from Database Telemetry:**\n\n"
            f"{context}"
        )

    return {
        "final_answer": report,
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
