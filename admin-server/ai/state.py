from typing import TypedDict


class WorkGuardState(TypedDict, total=False):
    """Data passed between WorkGuard's LangGraph agents."""

    session: dict
    session_id: str

    session_analysis: dict
    knowledge: dict
    security: dict
    report: dict

    workflow_stage: str

    errors: list[str]
