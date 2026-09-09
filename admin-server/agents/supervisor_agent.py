"""Phase 6: Supervisor Agent for WorkGuard.

Implements the multi-agent orchestrator using LangGraph:
                    Admin Inquiries
                          │
                          ▼
                   Supervisor Agent
                          │
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
 Session Agent      Security Agent     Reporting Agent
  (Phase 5)           (Phase 7)           (Phase 8)
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ▼
                Unified Admin Response

Key Responsibility:
    Understand the request and decide which specialized agent should handle it.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from langgraph.graph import StateGraph, END

from agents.state import SupervisorAgentState
from agents.session_agent import run_session_agent
from agents.security_agent import run_security_agent
from agents.reporting_agent import run_reporting_agent
from retrieval.semantic import search_knowledge
from database.connection import get_connection

logger = logging.getLogger(__name__)


def classify_intent(query: str) -> tuple[str, str, float]:
    """Classify the incoming query into one of: 'reporting', 'security', 'session', 'knowledge'."""
    q = query.lower()

    # 1. Reporting patterns
    report_patterns = [
        r"\breport\b",
        r"\bbriefing\b",
        r"\bsummarize\s+all\b",
        r"\bgenerate\s+(a\s+)?summary\b",
        r"\bgenerate\s+(an?\s+)?report\b",
        r"\bactivity\s+report\b",
        r"\bweekly\s+report\b",
        r"\bdaily\s+report\b",
        r"\bperformance\s+report\b",
        r"\bexecutive\s+summary\b",
        r"\baudit\s+report\b",
    ]
    if any(re.search(p, q) for p in report_patterns):
        return "reporting", "Query requests a formal telemetry summary or forensic activity report.", 0.95

    # 2. Security patterns
    security_patterns = [
        r"\bsecur(e|ity)\b",
        r"\bsuspicious\b",
        r"\balert(s)?\b",
        r"\brisk\b",
        r"\bviolation(s)?\b",
        r"\banomal(y|ies)\b",
        r"\bcompromise(d)?\b",
        r"\bthreat(s)?\b",
        r"\bunauthorized\b",
        r"\btamper(ing)?\b",
        r"\bmalicious\b",
        r"\bsafe\b",
        r"\bafter[- ]hours\b",
    ]
    if any(re.search(p, q) for p in security_patterns):
        return "security", "Query asks about security risk, anomalies, alerts, or policy violations.", 0.95

    # 3. Knowledge / Policy patterns
    knowledge_patterns = [
        r"\bpolicy\b",
        r"\bhandbook\b",
        r"\bguideline(s)?\b",
        r"\brules?\s+say\b",
        r"\bcompliance\s+standard\b",
        r"\bacceptable\s+use\b",
        r"\bprocedure\b",
    ]
    if any(re.search(p, q) for p in knowledge_patterns):
        return "knowledge", "Query asks about organizational policy, compliance guidelines, or handbooks.", 0.90

    # 4. Default: Session Analysis Agent (Activity, app usage, durations, timestamps)
    return "session", "Query asks about specific workstation activity, application usage, or time accounting.", 0.85


def _resolve_entities(query: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Resolve employee ID, employee name, session ID, and date from query."""
    emp_id = None
    emp_name = None
    session_id = None
    date_str = None

    q = query.lower()

    # Session ID
    s_match = re.search(r"\b(sess_[a-zA-Z0-9_]+)\b", query, re.IGNORECASE)
    if s_match:
        session_id = s_match.group(1)

    # Date
    d_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", query)
    if d_match:
        date_str = d_match.group(1)

    # Employee lookup in PostgreSQL
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
                    emp_id = eid
                    emp_name = ename or uname
                    break
    finally:
        conn.close()

    return emp_id, emp_name, session_id, date_str


def node_route_intent(state: SupervisorAgentState) -> dict[str, Any]:
    """Node 1: Analyze query and determine the specialized agent to dispatch."""
    query = state.get("query", "")
    emp_id = state.get("employee_id")
    emp_name = state.get("employee_name")
    session_id = state.get("session_id")
    date_str = state.get("date")

    # Resolve entities if missing
    p_id, p_name, p_sess, p_date = _resolve_entities(query)
    emp_id = emp_id or p_id
    emp_name = emp_name or p_name
    session_id = session_id or p_sess
    date_str = date_str or p_date

    # Classify intent
    routed_agent, reason, confidence = classify_intent(query)

    logger.info("Supervisor routed query '%s' -> %s (confidence: %.2f)", query, routed_agent, confidence)

    return {
        "employee_id": emp_id,
        "employee_name": emp_name,
        "session_id": session_id,
        "date": date_str,
        "routed_agent": routed_agent,
        "routing_reason": reason,
        "confidence": confidence,
    }


def node_dispatch_agent(state: SupervisorAgentState) -> dict[str, Any]:
    """Node 2: Dispatch query to the specialized agent."""
    query = state.get("query", "")
    routed_agent = state.get("routed_agent", "session")
    emp_id = state.get("employee_id")
    session_id = state.get("session_id")
    date_str = state.get("date")

    answer = ""
    sources: list[str] = []
    agent_result: dict[str, Any] = {}

    try:
        if routed_agent == "reporting":
            agent_result = run_reporting_agent(query=query, employee_id=emp_id, date=date_str)
            answer = agent_result.get("answer", "")
            sources = agent_result.get("sources", [])

        elif routed_agent == "security":
            agent_result = run_security_agent(
                query=query,
                employee_id=emp_id,
                session_id=session_id,
                date=date_str,
            )
            answer = agent_result.get("answer", "")
            sources = agent_result.get("sources", [])

        elif routed_agent == "knowledge":
            # Semantic search across policies and analysis documents
            hits = search_knowledge(query, k=3)
            sources = ["FAISS Vector Store: Organizational Knowledge & Policies"]
            if hits:
                snippets = "\n\n".join(f"- {h.get('snippet', '')}" for h in hits)
                answer = f"Relevant organizational guidance and policy records:\n\n{snippets}"
            else:
                answer = "No explicit policy documents matched your inquiry in the knowledge base."
            agent_result = {"hits": hits}

        else:  # default: session
            agent_result = run_session_agent(query=query, employee_id=emp_id, date=date_str)
            answer = agent_result.get("answer", "")
            sources = agent_result.get("sources", [])

    except Exception as exc:
        logger.error("Error executing dispatched agent '%s': %s", routed_agent, exc)
        answer = f"The {routed_agent.capitalize()} Agent encountered an error processing your inquiry: {exc}"
        sources = ["Supervisor Fallback Handler"]

    return {
        "final_answer": answer,
        "sources": sources,
        "agent_result": agent_result,
    }


def get_supervisor_agent():
    """Build and compile the LangGraph Supervisor Agent."""
    builder = StateGraph(SupervisorAgentState)
    builder.add_node("route_intent", node_route_intent)
    builder.add_node("dispatch_agent", node_dispatch_agent)

    builder.set_entry_point("route_intent")
    builder.add_edge("route_intent", "dispatch_agent")
    builder.add_edge("dispatch_agent", END)

    return builder.compile()


def run_supervisor_agent(
    query: str,
    employee_id: str | None = None,
    session_id: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Entry point for the Supervisor Agent orchestrating all sub-agents."""
    app = get_supervisor_agent()
    initial_state: SupervisorAgentState = {
        "query": query,
        "employee_id": employee_id,
        "session_id": session_id,
        "date": date,
    }

    final_state = app.invoke(initial_state)

    return {
        "query": query,
        "routed_agent": final_state.get("routed_agent"),
        "routing_reason": final_state.get("routing_reason"),
        "confidence": final_state.get("confidence", 0.0),
        "employee_id": final_state.get("employee_id"),
        "employee_name": final_state.get("employee_name"),
        "answer": final_state.get("final_answer", ""),
        "sources": final_state.get("sources", []),
        "agent_result": final_state.get("agent_result", {}),
    }
