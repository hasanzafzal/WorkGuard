"""Phase 7: Security Intelligence Agent for WorkGuard.

Implements the forensic security intelligence workflow using LangGraph:
    PostgreSQL Telemetry
          │
          ▼
    Deterministic Security Rules / Analytics
          │
          ▼
    Structured Suspicious Events & Risk Score
          │
          ▼
    Ollama (Contextualization & Recommendations)

Key Principle:
    Detection   -> Rules / Analytics (PostgreSQL)
    Explanation -> LLM (Ollama)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langgraph.graph import StateGraph, END

from agents.state import SecurityAgentState
from llm.ollama_client import get_ollama_client
from security.rules import evaluate_security_telemetry
from database.connection import get_connection

logger = logging.getLogger(__name__)

SECURITY_SYSTEM_PROMPT = (
    "You are WorkGuard Security Intelligence Agent, an authoritative endpoint cybersecurity specialist. "
    "Your role is to explain, contextualize, and assess the risk of security findings detected across workstation telemetry.\n"
    "Strict Rules:\n"
    "1. Base your answer strictly on the detected findings, evidence, and risk score provided. Never hallucinate extra findings.\n"
    "2. If no anomalies were detected, clearly declare that all telemetry integrity and activity checks passed with LOW risk.\n"
    "3. Keep your response concise (3 to 6 sentences or bullet points), highly factual, and executive-ready.\n"
    "4. Always state the specific risk level, cite the exact numbers/timestamps, and provide clear next steps for the administrator."
)


def _resolve_target_entities(query: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Extract employee identifier, name, session ID, and date from query."""
    emp_id = None
    emp_name = None
    session_id = None
    date_str = None

    q = query.lower()

    # Match session ID pattern
    sess_match = re.search(r"\b(sess_[a-zA-Z0-9_]+)\b", query, re.IGNORECASE)
    if sess_match:
        session_id = sess_match.group(1)

    # Match ISO date pattern
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", query)
    if date_match:
        date_str = date_match.group(1)

    # Look up employee in PostgreSQL
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT employee_id, employee_name, username FROM employees;")
            for eid, ename, uname in cur.fetchall():
                e_lower = (ename or "").lower()
                u_lower = (uname or "").lower()
                id_lower = eid.lower()

                # Check if employee name, username, or ID is mentioned
                first_name = u_lower.split(".")[0] if "." in u_lower else u_lower
                if (
                    id_lower in q
                    or u_lower in q
                    or e_lower in q
                    or (first_name and len(first_name) >= 3 and first_name in q)
                ):
                    emp_id = eid
                    emp_name = ename or uname
                    break
    finally:
        conn.close()

    return emp_id, emp_name, session_id, date_str


def node_extract_security_target(state: SecurityAgentState) -> dict[str, Any]:
    """Node 1: Identify target employee, session, or date."""
    query = state.get("query", "")
    emp_id = state.get("employee_id")
    emp_name = state.get("employee_name")
    session_id = state.get("session_id")
    date_str = state.get("date")

    # If any are missing, parse from query
    if not emp_id or not session_id or not date_str:
        p_emp_id, p_emp_name, p_session_id, p_date = _resolve_target_entities(query)
        emp_id = emp_id or p_emp_id
        emp_name = emp_name or p_emp_name
        session_id = session_id or p_session_id
        date_str = date_str or p_date

    return {
        "employee_id": emp_id,
        "employee_name": emp_name,
        "session_id": session_id,
        "date": date_str,
    }


def node_run_security_rules(state: SecurityAgentState) -> dict[str, Any]:
    """Node 2: Execute deterministic security rules against PostgreSQL."""
    emp_id = state.get("employee_id")
    session_id = state.get("session_id")
    date_str = state.get("date")

    sec_eval = evaluate_security_telemetry(
        session_id=session_id,
        employee_id=emp_id,
        date_str=date_str,
    )

    risk_score = sec_eval.get("risk_score", 0)
    risk_level = sec_eval.get("risk_level", "LOW")
    findings = sec_eval.get("findings", [])
    target = sec_eval.get("target", {})
    sessions_evaluated = sec_eval.get("sessions_evaluated", 0)

    # Format findings into compact LLM context
    target_desc = []
    if target.get("employee_name") or target.get("employee_id"):
        target_desc.append(f"Employee: {target.get('employee_name')} ({target.get('employee_id')})")
    if target.get("session_id"):
        target_desc.append(f"Session: {target.get('session_id')}")
    if target.get("date"):
        target_desc.append(f"Date: {target.get('date')}")
    target_header = " | ".join(target_desc) if target_desc else "Scope: Enterprise-wide Telemetry"

    lines = [
        f"Security Assessment Target: {target_header}",
        f"Sessions Evaluated: {sessions_evaluated}",
        f"Calculated Risk Score: {risk_score}/100 ({risk_level} Risk)",
        f"Total Deterministic Findings: {len(findings)}",
    ]

    if findings:
        lines.append("\nDetected Telemetry Findings:")
        for idx, f in enumerate(findings, 1):
            rule = f.get("rule", "anomaly")
            sev = f.get("severity", "LOW")
            desc = f.get("description", "")
            evidence = f.get("evidence", {})
            lines.append(f"{idx}. [{sev}] {rule}: {desc} (Evidence: {evidence})")
    else:
        lines.append("\nFindings: Zero anomalous events detected. All duration, process, and file checks within normal thresholds.")

    sources = [
        "PostgreSQL: sessions & session_activity_summary",
        "PostgreSQL: application_focus & application_catalog",
        "Deterministic Rules Engine: security.rules",
    ]

    return {
        "security_eval": sec_eval,
        "formatted_findings": "\n".join(lines),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "sources": sources,
    }


def node_explain_security_findings(state: SecurityAgentState) -> dict[str, Any]:
    """Node 3: Contextualize findings and advise using Ollama."""
    query = state.get("query", "")
    context = state.get("formatted_findings", "")
    risk_score = state.get("risk_score", 0)
    risk_level = state.get("risk_level", "LOW")
    ollama = get_ollama_client()

    prompt = f"""Administrator Inquiry: {query}

Verified Security Analytics Findings from Database:
\"\"\"
{context}
\"\"\"

Explain the security assessment clearly in 2 to 4 sentences. Address:
1. The overall risk level ({risk_level}, score {risk_score}/100).
2. The specific detected findings and why they do or do not warrant concern.
3. Recommended administrator action items or verification steps."""

    try:
        answer = ollama.generate_completion(
            prompt=prompt,
            system_prompt=SECURITY_SYSTEM_PROMPT,
            temperature=0.1,
            num_predict=180,
        )
    except Exception as e:
        logger.error("LLM security explanation failed: %s", e)
        answer = (
            f"Security Rule Evaluation: {risk_level} Risk (Score: {risk_score}/100).\n\n"
            f"Automated Findings Summary:\n{context}"
        )

    return {
        "final_answer": answer,
    }


def get_security_agent():
    """Build and compile the LangGraph Security Intelligence Agent."""
    builder = StateGraph(SecurityAgentState)
    builder.add_node("extract_target", node_extract_security_target)
    builder.add_node("run_rules", node_run_security_rules)
    builder.add_node("explain_findings", node_explain_security_findings)

    builder.set_entry_point("extract_target")
    builder.add_edge("extract_target", "run_rules")
    builder.add_edge("run_rules", "explain_findings")
    builder.add_edge("explain_findings", END)

    return builder.compile()


def run_security_agent(
    query: str,
    employee_id: str | None = None,
    session_id: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Entry point to execute the Security Intelligence Agent."""
    app = get_security_agent()
    initial_state: SecurityAgentState = {
        "query": query,
        "employee_id": employee_id,
        "session_id": session_id,
        "date": date,
    }

    final_state = app.invoke(initial_state)
    sec_eval = final_state.get("security_eval", {})

    return {
        "query": query,
        "employee_id": final_state.get("employee_id"),
        "employee_name": final_state.get("employee_name"),
        "session_id": final_state.get("session_id"),
        "date": final_state.get("date"),
        "risk_score": final_state.get("risk_score", 0),
        "risk_level": final_state.get("risk_level", "LOW"),
        "total_findings": sec_eval.get("total_findings", 0),
        "findings": sec_eval.get("findings", []),
        "answer": final_state.get("final_answer", ""),
        "sources": final_state.get("sources", []),
    }
