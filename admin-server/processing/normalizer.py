"""Normalizer for reading and augmenting session data from PostgreSQL."""

from __future__ import annotations

import logging
from typing import Any

from database.connection import get_connection
from processing.models import (
    ApplicationFocusItem,
    DirectoryActivityItem,
    NormalizedSession,
    ProcessEventItem,
)

logger = logging.getLogger(__name__)


def fetch_normalized_session(session_id: str) -> NormalizedSession | None:
    """Fetch complete session context from PostgreSQL relational tables."""
    connection = get_connection()
    try:
        with connection.cursor() as cur:
            # 1. Fetch session + employee
            cur.execute(
                """
                SELECT
                    s.session_id, s.employee_id, s.start_time, s.end_time,
                    s.duration_seconds, s.schema_version, s.session_file_path, s.ingested_at,
                    e.employee_name, e.machine_name, e.username
                FROM sessions s
                JOIN employees e ON s.employee_id = e.employee_id
                WHERE s.session_id = %s;
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if not row:
                logger.warning("Session %s not found in database", session_id)
                return None

            (
                s_id, emp_id, start_time, end_time, duration_seconds,
                schema_version, session_file_path, ingested_at,
                emp_name, machine_name, username
            ) = row

            # 2. Fetch session_activity_summary
            cur.execute(
                """
                SELECT
                    applications_used, desktop_seconds, active_seconds,
                    processes_started, processes_stopped, processes_used,
                    directories_affected, total_file_operations, file_extensions,
                    productive_seconds
                FROM session_activity_summary
                WHERE session_id = %s;
                """,
                (session_id,),
            )
            summary_row = cur.fetchone()
            if summary_row:
                (
                    apps_used, desktop_secs, active_secs,
                    proc_started, proc_stopped, proc_used,
                    dirs_affected, total_file_ops, file_exts,
                    prod_secs
                ) = summary_row
            else:
                apps_used = []
                desktop_secs = 0
                active_secs = duration_seconds
                proc_started = 0
                proc_stopped = 0
                proc_used = []
                dirs_affected = 0
                total_file_ops = 0
                file_exts = {}
                prod_secs = None

            # 3. Fetch application_focus joined with application_catalog
            cur.execute(
                """
                SELECT
                    af.process_name, af.focus_seconds, af.focus_pct,
                    ac.display_name, ac.category, ac.is_productive
                FROM application_focus af
                LEFT JOIN application_catalog ac ON af.process_name = ac.process_name
                WHERE af.session_id = %s
                ORDER BY af.focus_seconds DESC;
                """,
                (session_id,),
            )
            app_focus_items = [
                ApplicationFocusItem(
                    process_name=r[0],
                    focus_seconds=float(r[1]),
                    focus_pct=float(r[2]) if r[2] is not None else None,
                    display_name=r[3],
                    category=r[4],
                    is_productive=r[5],
                )
                for r in cur.fetchall()
            ]

            # 4. Fetch directory_activity
            cur.execute(
                """
                SELECT
                    directory_path, total_operations, ops_created, ops_modified,
                    ops_deleted, ops_moved, unique_file_count, file_extensions,
                    period_start, period_end, period_seconds
                FROM directory_activity
                WHERE session_id = %s
                ORDER BY total_operations DESC;
                """,
                (session_id,),
            )
            dir_activity_items = [
                DirectoryActivityItem(
                    directory_path=r[0],
                    total_operations=r[1],
                    ops_created=r[2],
                    ops_modified=r[3],
                    ops_deleted=r[4],
                    ops_moved=r[5],
                    unique_file_count=r[6],
                    file_extensions=r[7] if isinstance(r[7], dict) else {},
                    period_start=r[8],
                    period_end=r[9],
                    period_seconds=r[10],
                )
                for r in cur.fetchall()
            ]

            # 5. Fetch process_events
            cur.execute(
                """
                SELECT event_id, event_type, process_name, pid, executable, occurred_at
                FROM process_events
                WHERE session_id = %s
                ORDER BY occurred_at ASC;
                """,
                (session_id,),
            )
            proc_event_items = [
                ProcessEventItem(
                    event_id=r[0],
                    event_type=r[1],
                    process_name=r[2],
                    pid=r[3],
                    executable=r[4],
                    occurred_at=r[5],
                )
                for r in cur.fetchall()
            ]

            return NormalizedSession(
                session_id=s_id,
                employee_id=emp_id,
                employee_name=emp_name,
                machine_name=machine_name,
                username=username,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                schema_version=schema_version,
                session_file_path=session_file_path,
                ingested_at=ingested_at,
                applications_used=list(apps_used or []),
                desktop_seconds=int(desktop_secs or 0),
                active_seconds=int(active_secs or 0),
                processes_started=int(proc_started or 0),
                processes_stopped=int(proc_stopped or 0),
                processes_used=list(proc_used or []),
                directories_affected=int(dirs_affected or 0),
                total_file_operations=int(total_file_ops or 0),
                file_extensions=file_exts or {},
                productive_seconds=prod_secs,
                app_focus_items=app_focus_items,
                dir_activity_items=dir_activity_items,
                process_event_items=proc_event_items,
            )
    finally:
        connection.close()


def calculate_and_update_productive_seconds(
    session_id: str,
    app_focus_items: list[ApplicationFocusItem],
) -> int:
    """Calculate productive seconds from application catalog classifications and persist to DB."""
    productive_total = 0.0

    for item in app_focus_items:
        # If catalog explicitly marks as productive, or if not marked but not Desktop
        if item.is_productive is True:
            productive_total += item.focus_seconds
        elif item.is_productive is None and item.process_name != "Desktop":
            # Default unclassified apps (other than Desktop) to productive
            productive_total += item.focus_seconds

    productive_seconds = int(round(productive_total))

    connection = get_connection()
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                UPDATE session_activity_summary
                SET productive_seconds = %s
                WHERE session_id = %s;
                """,
                (productive_seconds, session_id),
            )
        connection.commit()
    finally:
        connection.close()

    return productive_seconds
