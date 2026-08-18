"""Supervisor node that validates and routes a WorkGuard AI workflow."""

from ai.state import WorkGuardState


def supervisor_agent(state: WorkGuardState) -> dict:
    """Initialize workflow state before specialized agents run."""
    session = state.get("session")
    if not session:
        return {
            "workflow_stage": "failed",
            "errors": state.get("errors", [])
            + ["Supervisor received no verified session."],
        }

    return {
        "session_id": session.get("session_id", state.get("session_id", "")),
        "workflow_stage": "session_analysis",
    }
