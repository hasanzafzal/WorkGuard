"""State definitions for LangGraph agents in WorkGuard."""

from __future__ import annotations

from typing import Any, TypedDict


class SessionAgentState(TypedDict, total=False):
    """State passed across the nodes of the Session Analysis Agent."""

    query: str
    employee_id: str | None
    employee_name: str | None
    date: str | None
    time_window: str | None
    intent: str | None
    structured_data: dict[str, Any]
    semantic_hits: list[dict[str, Any]]
    formatted_context: str
    final_answer: str
    sources: list[str]
    error: str | None


class SecurityAgentState(TypedDict, total=False):
    """State for the Security Intelligence Agent (Phase 7)."""

    query: str
    employee_id: str | None
    employee_name: str | None
    session_id: str | None
    date: str | None
    security_eval: dict[str, Any]
    formatted_findings: str
    final_answer: str
    sources: list[str]
    risk_score: int
    risk_level: str
    error: str | None


class ReportingAgentState(TypedDict, total=False):
    """State for the Reporting Agent (Phase 8)."""

    query: str
    employee_id: str | None
    employee_name: str | None
    date: str | None
    scope: str | None
    metrics_bundle: dict[str, Any]
    formatted_report: str
    final_answer: str
    sources: list[str]
    error: str | None


class SupervisorAgentState(TypedDict, total=False):
    """State for the Supervisor Agent (Phase 6)."""

    query: str
    employee_id: str | None
    employee_name: str | None
    date: str | None
    session_id: str | None
    routed_agent: str | None  # "session" | "security" | "reporting" | "knowledge"
    confidence: float
    routing_reason: str | None
    agent_result: dict[str, Any]
    final_answer: str
    sources: list[str]
    error: str | None

