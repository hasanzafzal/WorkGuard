"""Parse decrypted session JSON and persist structured data into PostgreSQL.

This module maps the session JSON produced by employee clients to the
normalised ``workguard 2.0`` PostgreSQL schema.  Every call to
``parse_and_store`` runs inside a single transaction so that a partially
ingested session can never appear in the database.

Tables populated
----------------
employees, sessions, focus_timeline, process_events, directory_activity,
application_focus, session_activity_summary, application_catalog
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Json

from database.connection import get_connection

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_employee_name(raw: str) -> tuple[str, str | None, str | None]:
    """Extract *machine_name* and *username* from ``"MACHINE (user)"`` format.

    Returns ``(employee_name, machine_name, username)``.
    """
    match = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", raw)
    if match:
        machine_name = match.group(1).strip()
        username = match.group(2).strip()
        return raw, machine_name, username
    return raw, None, None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

UPSERT_EMPLOYEE = """\
INSERT INTO employees (employee_id, employee_name, machine_name, username, first_seen_at, last_seen_at)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (employee_id) DO UPDATE SET
    employee_name = EXCLUDED.employee_name,
    machine_name  = COALESCE(EXCLUDED.machine_name, employees.machine_name),
    username      = COALESCE(EXCLUDED.username, employees.username),
    last_seen_at  = EXCLUDED.last_seen_at;
"""

INSERT_SESSION = """\
INSERT INTO sessions (
    session_id, employee_id, start_time, end_time,
    duration_seconds, schema_version, session_file_path
) VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (session_id) DO NOTHING;
"""

INSERT_FOCUS_TIMELINE = """\
INSERT INTO focus_timeline (
    event_id, session_id, event_type, process_name, pid, occurred_at
) VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING;
"""

INSERT_PROCESS_EVENT = """\
INSERT INTO process_events (
    event_id, session_id, event_type, process_name, pid, executable, occurred_at
) VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING;
"""

INSERT_DIRECTORY_ACTIVITY = """\
INSERT INTO directory_activity (
    event_id, session_id, directory_path, total_operations,
    ops_created, ops_modified, ops_deleted, ops_moved,
    unique_file_count, file_extensions, period_start, period_end
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING;
"""

INSERT_APPLICATION_FOCUS = """\
INSERT INTO application_focus (session_id, process_name, focus_seconds, focus_pct)
VALUES (%s, %s, %s, %s)
ON CONFLICT (session_id, process_name) DO NOTHING;
"""

UPSERT_SESSION_ACTIVITY_SUMMARY = """\
INSERT INTO session_activity_summary (
    session_id, applications_used, desktop_seconds,
    processes_started, processes_stopped, processes_used,
    directories_affected, total_file_operations, file_extensions,
    productive_seconds, active_seconds
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (session_id) DO NOTHING;
"""

UPSERT_APPLICATION_CATALOG = """\
INSERT INTO application_catalog (process_name, first_seen_at)
VALUES (%s, %s)
ON CONFLICT (process_name) DO NOTHING;
"""


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse_and_store(
    session: dict[str, Any],
    file_path: str | None = None,
) -> dict[str, Any]:
    """Parse a decrypted session dict and persist to PostgreSQL.

    Parameters
    ----------
    session : dict
        The full decrypted session JSON (as produced by the employee client).
    file_path : str, optional
        Path to the on-disk JSON file, stored in ``sessions.session_file_path``.

    Returns
    -------
    dict
        Summary of what was inserted (row counts per table).
    """
    session_id = session["session_id"]
    employee_id = session["employee_id"]
    employee_name_raw = session.get("employee_name", "")
    session_info = session.get("session", {})
    events = session.get("events", [])
    focus_summary = session.get("focus_summary", {})
    metadata = session.get("metadata", {})

    employee_name, machine_name, username = _parse_employee_name(employee_name_raw)
    start_time = session_info.get("start_time")
    end_time = session_info.get("end_time")
    duration_seconds = session_info.get("duration_seconds", 0)
    schema_version = metadata.get("schema_version")

    # Accumulators for the activity summary
    all_apps: set[str] = set()
    desktop_seconds = 0.0
    processes_started = 0
    processes_stopped = 0
    processes_used: set[str] = set()
    directories_affected: set[str] = set()
    total_file_operations = 0
    all_file_extensions: dict[str, int] = {}

    # Counters for the return summary
    counts = {
        "focus_timeline": 0,
        "process_events": 0,
        "directory_activity": 0,
        "application_focus": 0,
    }

    connection = get_connection()
    try:
        with connection.cursor() as cur:
            # 1. Upsert employee
            now = _now_utc()
            first_seen = start_time or now.isoformat()
            cur.execute(UPSERT_EMPLOYEE, (
                employee_id,
                employee_name,
                machine_name,
                username,
                first_seen,
                end_time or now.isoformat(),
            ))

            # 2. Insert session
            cur.execute(INSERT_SESSION, (
                session_id,
                employee_id,
                start_time,
                end_time,
                duration_seconds,
                schema_version,
                file_path,
            ))

            # 3. Route events
            for event in events:
                etype = event.get("event_type", "")
                eid = event.get("event_id", "")
                data = event.get("data", {})
                ts = event.get("timestamp")

                if etype in ("application_focused", "application_unfocused"):
                    proc = data.get("process_name", "")
                    pid = data.get("pid")
                    cur.execute(INSERT_FOCUS_TIMELINE, (
                        eid, session_id, etype, proc, pid, ts,
                    ))
                    counts["focus_timeline"] += 1
                    if proc and proc != "Desktop":
                        all_apps.add(proc)

                elif etype in ("application_started", "application_stopped"):
                    proc = data.get("process_name", "")
                    pid = data.get("pid")
                    exe = data.get("executable")
                    cur.execute(INSERT_PROCESS_EVENT, (
                        eid, session_id, etype, proc, pid, exe, ts,
                    ))
                    counts["process_events"] += 1
                    if etype == "application_started":
                        processes_started += 1
                    else:
                        processes_stopped += 1
                    if proc:
                        processes_used.add(proc)

                elif etype == "directory_activity":
                    ops = data.get("operations", {})
                    file_types = data.get("file_types", {})
                    p_start = data.get("period_start")
                    p_end = data.get("period_end")
                    dir_path = data.get("directory", "")

                    cur.execute(INSERT_DIRECTORY_ACTIVITY, (
                        eid,
                        session_id,
                        dir_path,
                        data.get("total_operations", 0),
                        ops.get("created", 0),
                        ops.get("modified", 0),
                        ops.get("deleted", 0),
                        ops.get("moved", 0),
                        data.get("unique_file_count", 0),
                        Json(file_types) if file_types else None,
                        p_start,
                        p_end,
                    ))
                    counts["directory_activity"] += 1
                    if dir_path:
                        directories_affected.add(dir_path)
                    total_file_operations += data.get("total_operations", 0)
                    for ext, cnt in file_types.items():
                        all_file_extensions[ext] = all_file_extensions.get(ext, 0) + cnt

                else:
                    logger.warning(
                        "Unrecognised event_type %r for event %s — skipped",
                        etype, eid,
                    )

            # 4. Application focus (from focus_summary)
            for proc_name, seconds in focus_summary.items():
                pct = round((seconds / duration_seconds) * 100, 2) if duration_seconds else None
                cur.execute(INSERT_APPLICATION_FOCUS, (
                    session_id, proc_name, seconds, pct,
                ))
                counts["application_focus"] += 1
                if proc_name and proc_name != "Desktop":
                    all_apps.add(proc_name)

            # 5. Compute desktop_seconds from focus_summary
            desktop_seconds = focus_summary.get("Desktop", 0)

            # 6. Session activity summary
            active_seconds = int(duration_seconds - desktop_seconds) if duration_seconds else None
            cur.execute(UPSERT_SESSION_ACTIVITY_SUMMARY, (
                session_id,
                sorted(all_apps) if all_apps else None,
                int(desktop_seconds),
                processes_started,
                processes_stopped,
                sorted(processes_used) if processes_used else None,
                len(directories_affected),
                total_file_operations,
                Json(all_file_extensions) if all_file_extensions else None,
                None,  # productive_seconds — requires catalog lookup, deferred
                active_seconds,
            ))

            # 7. Auto-populate application_catalog
            all_process_names = all_apps | processes_used
            for proc_name in all_process_names:
                cur.execute(UPSERT_APPLICATION_CATALOG, (proc_name, now))

        connection.commit()
        logger.info(
            "Session %s ingested: %s",
            session_id,
            ", ".join(f"{k}={v}" for k, v in counts.items()),
        )
    except Exception:
        connection.rollback()
        logger.exception("Failed to ingest session %s", session_id)
        raise
    finally:
        connection.close()

    return {
        "session_id": session_id,
        "employee_id": employee_id,
        "rows_inserted": counts,
    }
