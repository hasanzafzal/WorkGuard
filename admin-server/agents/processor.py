"""Process verified sessions through the agent workflow."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from database.repository import mark_session_processed, persist_report
from agents.workflow import run_workflow


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_SESSIONS_DIR = BASE_DIR / "processed_sessions"


def _save_json(directory: Path, filename: str, data: dict) -> None:
    """Atomically persist JSON to prevent incomplete writes."""
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
    """Run the agent workflow and persist results."""
    workflow_result = run_workflow(session)
    
    # Save processed session for audit trail
    processed_at = datetime.now(timezone.utc).isoformat()
    filename = f"{uuid.uuid4().hex}.json"
    
    _save_json(
        PROCESSED_SESSIONS_DIR,
        filename,
        {
            "session_id": session.get("session_id"),
            "processed_at": processed_at,
            "workflow_result": workflow_result,
        },
    )
    
    return workflow_result
