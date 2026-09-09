"""Session Analysis Agent implemented with LangGraph and local Ollama (llama3).

Answers administrator queries about employee computer activity, application focus,
productive time, and file system operations using PostgreSQL tools and FAISS vector retrieval.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from agents.state import SessionAgentState
from llm.ollama_client import get_ollama_client
from retrieval.semantic import search_employee_activity
from retrieval.service import retrieve_context
from retrieval.structured import (
    get_application_usage,
    get_daily_summary,
    get_employee,
    get_project_file_activity,
    get_session_details,
    get_sessions,
    list_employees,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the WorkGuard Session Analysis Agent, a senior forensic and productivity analyst.
Your task is to answer administrators' questions about employee computer activity strictly and factually based ONLY on the provided context retrieved from PostgreSQL and the FAISS vector index.

Guidelines:
1. Be direct, authoritative, and concise.
2. Cite specific measurements when available: exact durations (minutes, seconds), focus percentages, active work time versus desktop/idle time, file operation counts, and application names.
3. Distinguish clearly between productive work (e.g., development in VS Code) and non-productive or idle time (e.g., Desktop idle).
4. If the retrieved context indicates no recorded sessions or no matching data, clearly state that without speculating or making assumptions.
5. Do NOT reference database tables or internal query schemas. Speak in business terms (e.g. 'Employee Jane worked for 30 minutes in VS Code...').
"""


def _detect_employee(query: str) -> dict[str, Any] | None:
    """Scan query for employee names, usernames, or IDs matching known employees in PostgreSQL."""
    known_employees = list_employees(limit=100)
    query_lower = query.lower()

    for emp in known_employees:
        uname = (emp.get("username") or "").lower()
        ename = (emp.get("employee_name") or "").lower()
        eid = (emp.get("employee_id") or "").lower()
        mname = (emp.get("machine_name") or "").lower()

        # Check for first name or parts of username (e.g. 'arif', 'jane')
        first_name = uname.split(".")[0] if "." in uname else uname

        if uname and uname in query_lower:
            return emp
        if first_name and len(first_name) >= 3 and first_name in query_lower:
            return emp
        if eid and eid in query_lower:
            return emp
        if mname and mname in query_lower:
            return emp
        if any(part in query_lower for part in ename.split() if len(part) >= 4):
            return emp

    return None


def _detect_date(query: str) -> str | None:
    """Extract dates formatted as YYYY-MM-DD or relative dates from query."""
    # Match YYYY-MM-DD
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", query)
    if match:
        return match.group(1)

    # If query mentions 'yesterday' or specific day
    query_lower = query.lower()
    if "2026-09-01" in query_lower or "september 1" in query_lower or "sep 1" in query_lower:
        return "2026-09-01"
    if "2026-09-02" in query_lower or "september 2" in query_lower or "sep 2" in query_lower:
        return "2026-09-02"
    if "2026-09-03" in query_lower or "september 3" in query_lower or "sep 3" in query_lower or "today" in query_lower:
        return "2026-09-03"

    return None


def _detect_app_filter(query: str) -> str | None:
    """Extract application names mentioned in query."""
    query_lower = query.lower()
    if "vs code" in query_lower or "vscode" in query_lower or "code" in query_lower:
        return "Code"
    if "python" in query_lower:
        return "python"
    if "photo" in query_lower or "wps" in query_lower or "photolaunch" in query_lower:
        return "photolaunch"
    if "chrome" in query_lower:
        return "chrome"
    return None


# ---------------------------------------------------------------------------
# LangGraph Nodes
# ---------------------------------------------------------------------------

def node_extract_parameters(state: SessionAgentState) -> dict[str, Any]:
    """Node 1: Extract employee, date, and intent from the query."""
    query = state["query"]
    employee_id = state.get("employee_id")
    date = state.get("date")

    # Detect employee if not explicitly provided
    emp = None
    if not employee_id:
        emp = _detect_employee(query)
        if emp:
            employee_id = emp["employee_id"]
    else:
        emp = get_employee(employee_id)

    # Detect date if not explicitly provided
    if not date:
        date = _detect_date(query)

    # Identify general intent
    q_low = query.lower()
    if any(k in q_low for k in ["how much time", "how long", "spend on", "app usage", "application"]):
        intent = "app_usage"
    elif any(k in q_low for k in ["summary", "what did", "do yesterday", "overview", "activity"]):
        intent = "daily_summary"
    elif any(k in q_low for k in ["file", "directory", "folder", "project"]):
        intent = "file_activity"
    else:
        intent = "general"

    return {
        "employee_id": employee_id,
        "employee_name": emp["employee_name"] if emp else None,
        "date": date,
        "intent": intent,
    }


def node_retrieve_tools(state: SessionAgentState) -> dict[str, Any]:
    """Node 2: Execute structured PostgreSQL tools and FAISS semantic search."""
    query = state["query"]
    employee_id = state.get("employee_id")
    date = state.get("date")
    intent = state.get("intent")

    structured_data: dict[str, Any] = {}
    sources: list[str] = []

    # 1. Employee profile
    if employee_id:
        emp = get_employee(employee_id)
        if emp:
            structured_data["employee"] = emp
            sources.append(f"PostgreSQL: employees ({emp['employee_id']})")

    # 2. Targeted structured queries based on intent
    app_filter = _detect_app_filter(query)
    if app_filter or intent == "app_usage":
        apps = get_application_usage(
            employee_id=employee_id,
            date=date,
            process_name=app_filter,
        )
        structured_data["application_usage"] = apps
        sources.append("PostgreSQL: application_focus & application_catalog")

    if date or intent == "daily_summary":
        if employee_id and date:
            daily = get_daily_summary(employee_id, date)
            if daily:
                structured_data["daily_summary"] = daily
                sources.append(f"PostgreSQL: daily summary ({date})")

    if intent == "file_activity" or "file" in query.lower() or "directory" in query.lower():
        files = get_project_file_activity(employee_id=employee_id, limit=5)
        structured_data["project_activity"] = files
        sources.append("PostgreSQL: directory_activity")

    # Always fetch recent sessions for context
    if employee_id:
        sessions = get_sessions(employee_id=employee_id, date=date, limit=3)
        structured_data["recent_sessions"] = sessions
        sources.append("PostgreSQL: sessions")

    # 3. Hybrid context assembly (includes FAISS semantic hits)
    hybrid_bundle = retrieve_context(
        query=query,
        employee_id=employee_id,
        date=date,
        k=3,
    )

    formatted_context = hybrid_bundle.get("formatted_context", "")

    # If structured data has specific app or file info not in formatted_context, append it
    extra_details = []
    if structured_data.get("application_usage"):
        app_lines = [
            f"- {a['display_name']} ({a['process_name']}): {round(a['total_focus_seconds'] / 60, 1)}m "
            f"({a['avg_focus_pct']}% focus, Productive: {a['is_productive']})"
            for a in structured_data["application_usage"]
        ]
        extra_details.append("=== SPECIFIC APPLICATION FOCUS ===\n" + "\n".join(app_lines))

    if structured_data.get("project_activity"):
        dir_lines = [
            f"- {d['directory_path']}: {d['total_operations']} operations ({d['total_modified']} modified)"
            for d in structured_data["project_activity"]
        ]
        extra_details.append("=== PROJECT DIRECTORY MODIFICATIONS ===\n" + "\n".join(dir_lines))

    if extra_details:
        formatted_context = "\n\n".join([formatted_context, *extra_details]).strip()

    if hybrid_bundle.get("semantic_hits"):
        sources.append(f"FAISS: {len(hybrid_bundle['semantic_hits'])} semantic vector matches")

    return {
        "structured_data": structured_data,
        "semantic_hits": hybrid_bundle.get("semantic_hits", []),
        "formatted_context": formatted_context,
        "sources": sources,
    }


def node_generate_answer(state: SessionAgentState) -> dict[str, Any]:
    """Node 3: Synthesize final answer via local Ollama LLM."""
    query = state["query"]
    context = state.get("formatted_context", "")
    ollama = get_ollama_client()

    prompt = f"""Question: {query}

Retrieved Forensic Activity Context:
\"\"\"
{context if context else "No relevant activity records or documents found in the database."}
\"\"\"

Answer the administrator's question concisely in 2-4 sentences based strictly on the retrieved observations above."""

    try:
        answer = ollama.generate_completion(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.1,
            num_predict=120,
        )
    except Exception as e:
        logger.error("LLM answer generation failed: %s", e)
        answer = (
            f"I was able to retrieve the forensic records, but encountered an issue generating "
            f"the natural language synthesis from Ollama: {e}\n\n"
            f"Here is the raw retrieved context:\n{context}"
        )

    return {
        "final_answer": answer,
    }


# ---------------------------------------------------------------------------
# Build and Compile LangGraph Workflow
# ---------------------------------------------------------------------------

def create_session_agent_graph():
    """Create the compiled LangGraph workflow for the Session Analysis Agent."""
    workflow = StateGraph(SessionAgentState)

    workflow.add_node("extract_parameters", node_extract_parameters)
    workflow.add_node("retrieve_tools", node_retrieve_tools)
    workflow.add_node("generate_answer", node_generate_answer)

    workflow.set_entry_point("extract_parameters")
    workflow.add_edge("extract_parameters", "retrieve_tools")
    workflow.add_edge("retrieve_tools", "generate_answer")
    workflow.add_edge("generate_answer", END)

    return workflow.compile()


# Compiled agent singleton
_compiled_agent = None


def get_session_agent():
    """Get or compile the global Session Analysis Agent instance."""
    global _compiled_agent
    if _compiled_agent is None:
        _compiled_agent = create_session_agent_graph()
    return _compiled_agent


def run_session_agent(
    query: str,
    employee_id: str | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Execute the Session Analysis Agent for a user inquiry.

    Parameters
    ----------
    query : str
        The administrator's natural language question.
    employee_id : str, optional
        Explicit employee ID or username (if known).
    date : str, optional
        Explicit date in YYYY-MM-DD format (if known).

    Returns
    -------
    dict
        Dictionary with 'answer', 'employee_id', 'date', 'sources', and 'retrieved_data'.
    """
    agent = get_session_agent()
    initial_state: SessionAgentState = {
        "query": query,
        "employee_id": employee_id,
        "date": date,
    }

    final_state = agent.invoke(initial_state)

    return {
        "query": query,
        "answer": final_state.get("final_answer", ""),
        "employee_id": final_state.get("employee_id"),
        "employee_name": final_state.get("employee_name"),
        "date": final_state.get("date"),
        "intent": final_state.get("intent"),
        "sources": final_state.get("sources", []),
        "retrieved_data": final_state.get("structured_data", {}),
    }
