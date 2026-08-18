"""Reporting node that combines specialized-agent findings."""

from datetime import datetime, timezone

from ai.state import WorkGuardState


def reporting_agent(state: WorkGuardState) -> dict:
    """Create one structured local report from the agent outputs."""
    session = state.get("session", {})

    return {
        "report": {
            "session_id": session.get("session_id", state.get("session_id")),
            "employee_id": session.get("employee_id"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "session_analysis": state.get("session_analysis", {}),
            "knowledge": state.get("knowledge", {}),
            "security": state.get("security", {}),
            "errors": state.get("errors", []),
        },
        "workflow_stage": "complete",
    }
