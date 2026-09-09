"""Unified hybrid retrieval service combining structured PostgreSQL queries and FAISS vector search."""

from __future__ import annotations

import logging
from typing import Any

from retrieval.semantic import search_employee_activity, search_knowledge
from retrieval.structured import (
    get_application_usage,
    get_daily_summary,
    get_employee,
    get_sessions,
)

logger = logging.getLogger(__name__)


def retrieve_context(
    query: str,
    employee_id: str | None = None,
    date: str | None = None,
    k: int = 5,
    doc_type: str | None = None,
) -> dict[str, Any]:
    """Assemble a rich hybrid context bundle for downstream LLM reasoning (Phase 4).

    Parameters
    ----------
    query : str
        The natural language question or topic.
    employee_id : str, optional
        Target employee ID or username (if known).
    date : str, optional
        Target date in 'YYYY-MM-DD' format (if known).
    k : int, default 5
        Maximum number of semantic document hits to include.
    doc_type : str, optional
        Filter semantic search by document type.

    Returns
    -------
    dict
        Structured bundle containing employee profile, exact statistics,
        top semantic document snippets, and a pre-formatted prompt text.
    """
    context_sections = []
    bundle: dict[str, Any] = {
        "query": query,
        "employee_id": employee_id,
        "date": date,
        "employee_profile": None,
        "structured_summary": None,
        "semantic_hits": [],
        "formatted_context": "",
    }

    # 1. Structured Channel: Employee profile
    if employee_id:
        emp = get_employee(employee_id)
        if emp:
            bundle["employee_profile"] = emp
            context_sections.append(
                f"=== EMPLOYEE PROFILE ===\n"
                f"Name: {emp['employee_name']} (Username: {emp['username']}, ID: {emp['employee_id']})\n"
                f"Machine: {emp['machine_name'] or 'N/A'}\n"
                f"Total Sessions: {emp['total_sessions']} | Total Work Time: {round(emp['total_work_seconds'] / 60, 1)}m"
            )

    # 2. Structured Channel: Daily summary (if date is specified)
    if employee_id and date:
        daily = get_daily_summary(employee_id, date)
        if daily and daily.get("total_sessions", 0) > 0:
            bundle["structured_summary"] = daily
            top_apps_str = ", ".join(
                f"{a['display_name']} ({round(a['focus_seconds'] / 60, 1)}m)"
                for a in daily.get("top_applications", [])
            )
            context_sections.append(
                f"=== STRUCTURED DAILY SUMMARY ({date}) ===\n"
                f"Sessions: {daily['total_sessions']} | Work Time: {round(daily['total_duration_seconds'] / 60, 1)}m\n"
                f"Productive Time: {round(daily['productive_seconds'] / 60, 1)}m ({daily['productive_pct']}%)\n"
                f"Top Apps: {top_apps_str or 'None'}\n"
                f"File Operations: {daily['total_file_operations']} ops | Processes Started: {daily['processes_started']}"
            )

    # 3. Semantic Channel: FAISS vector search
    hits = search_employee_activity(
        query=query,
        employee_id=employee_id,
        k=k,
        doc_type=doc_type,
    )
    bundle["semantic_hits"] = hits

    if hits:
        doc_snippets = []
        for i, hit in enumerate(hits, 1):
            doc_snippets.append(
                f"--- [Hit {i}] {hit['title']} (Score: {hit['score']:.2f}, Type: {hit['doc_type']}) ---\n"
                f"{hit['content']}"
            )
        context_sections.append(
            f"=== RELEVANT OBSERVED SESSIONS & ACTIVITIES (SEMANTIC SEARCH) ===\n"
            + "\n\n".join(doc_snippets)
        )

    bundle["formatted_context"] = "\n\n".join(context_sections)
    return bundle
