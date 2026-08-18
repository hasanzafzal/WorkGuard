"""Persist outputs from the local WorkGuard AI workflow."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ai.workflow import run_workflow


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_SESSIONS_DIR = BASE_DIR / "processed_sessions"
REPORTS_DIR = BASE_DIR / "reports"


def _save_json(directory: Path, filename: str, data: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename
    descriptor, temporary_path = tempfile.mkstemp(
        dir=directory,
        prefix=".writing_",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, destination)
    except OSError:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise


def process_verified_session(session: dict) -> dict:
    """Run the graph and persist a processed session plus its report."""
    workflow_result = run_workflow(session)
    processed_at = datetime.now(timezone.utc).isoformat()
    filename = f"{uuid.uuid4().hex}.json"

    _save_json(
        PROCESSED_SESSIONS_DIR,
        filename,
        {
            "session_id": session.get("session_id"),
            "employee_id": session.get("employee_id"),
            "processed_at": processed_at,
            "workflow": workflow_result,
        },
    )
    _save_json(
        REPORTS_DIR,
        filename,
        workflow_result.get("report", {}),
    )

    return workflow_result
