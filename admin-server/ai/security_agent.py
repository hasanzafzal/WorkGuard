"""Conservative local security checks for verified session data."""

from ai.state import WorkGuardState


def security_agent(state: WorkGuardState) -> dict:
    """Report only objective data-integrity issues; no policy is assumed."""
    session = state.get("session", {})
    alerts = []

    duration = session.get("session", {}).get("duration_seconds")
    if not isinstance(duration, (int, float)) or duration < 0:
        alerts.append("Session duration is missing or invalid.")

    if not isinstance(session.get("events", []), list):
        alerts.append("Session events are not a list.")

    return {
        "security": {
            "risk_score": len(alerts),
            "alerts": alerts,
            "assessment": "review_required" if alerts else "no_data_integrity_alerts",
        },
        "workflow_stage": "reporting",
    }
