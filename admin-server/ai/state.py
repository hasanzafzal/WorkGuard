from typing import Any, TypedDict


class WorkGuardState(TypedDict, total=False):
    """Data passed between WorkGuard's LangGraph agents."""

    session: dict[str, Any]
    session_id: str

    session_analysis: dict[str, Any]
    knowledge: dict[str, Any]
    security: dict[str, Any]
    report: dict[str, Any]

    workflow_stage: str

    errors: list[str]
