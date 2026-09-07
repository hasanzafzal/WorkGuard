"""Structured retrieval layer querying PostgreSQL (workguard 2.0).

Provides deterministic, authoritative access to employee profiles, session histories,
application usage statistics, daily aggregates, and file system activity.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from database.connection import get_connection

logger = logging.getLogger(__name__)


def _serialize_dt(val: Any) -> Any:
    """Helper to convert datetime objects to ISO strings."""
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def get_employee(identifier: str) -> dict[str, Any] | None:
    """Find an employee by employee_id, username, machine_name, or display name."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.employee_id, e.employee_name, e.machine_name, e.username,
                    e.first_seen_at, e.last_seen_at, e.created_at,
                    COUNT(s.session_id) AS total_sessions,
                    COALESCE(SUM(s.duration_seconds), 0) AS total_work_seconds
                FROM employees e
                LEFT JOIN sessions s ON e.employee_id = s.employee_id
                WHERE e.employee_id = %s
                   OR e.username = %s
                   OR e.machine_name = %s
                   OR e.employee_name ILIKE %s
                GROUP BY e.employee_id, e.employee_name, e.machine_name, e.username,
                         e.first_seen_at, e.last_seen_at, e.created_at
                LIMIT 1;
                """,
                (identifier, identifier, identifier, f"%{identifier}%"),
            )
            row = cur.fetchone()
            if not row:
                return None

            cols = [
                "employee_id", "employee_name", "machine_name", "username",
                "first_seen_at", "last_seen_at", "created_at",
                "total_sessions", "total_work_seconds",
            ]
            result = dict(zip(cols, row))
            for k in ["first_seen_at", "last_seen_at", "created_at"]:
                result[k] = _serialize_dt(result[k])
            return result
    finally:
        conn.close()


def list_employees(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """List all registered employees with summary counts."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.employee_id, e.employee_name, e.machine_name, e.username,
                    e.first_seen_at, e.last_seen_at,
                    COUNT(s.session_id) AS total_sessions,
                    COALESCE(SUM(s.duration_seconds), 0) AS total_work_seconds
                FROM employees e
                LEFT JOIN sessions s ON e.employee_id = s.employee_id
                GROUP BY e.employee_id, e.employee_name, e.machine_name, e.username,
                         e.first_seen_at, e.last_seen_at
                ORDER BY e.last_seen_at DESC NULLS LAST
                LIMIT %s OFFSET %s;
                """,
                (limit, offset),
            )
            rows = cur.fetchall()
            cols = [
                "employee_id", "employee_name", "machine_name", "username",
                "first_seen_at", "last_seen_at", "total_sessions", "total_work_seconds",
            ]
            results = []
            for r in rows:
                item = dict(zip(cols, r))
                item["first_seen_at"] = _serialize_dt(item["first_seen_at"])
                item["last_seen_at"] = _serialize_dt(item["last_seen_at"])
                results.append(item)
            return results
    finally:
        conn.close()


def get_sessions(
    employee_id: str | None = None,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query sessions with employee and date filtering."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            conditions = []
            params: list[Any] = []

            if employee_id:
                # Support matching by employee_id or username
                conditions.append("(s.employee_id = %s OR e.username = %s)")
                params.extend([employee_id, employee_id])

            if date:
                conditions.append("(DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)")
                params.extend([date, date])
            else:
                if start_date:
                    conditions.append("s.start_time >= %s::timestamptz")
                    params.append(start_date)
                if end_date:
                    conditions.append("s.end_time <= %s::timestamptz")
                    params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
                SELECT
                    s.session_id, s.employee_id, e.employee_name, e.username, e.machine_name,
                    s.start_time, s.end_time, s.duration_seconds,
                    sas.active_seconds, sas.desktop_seconds, sas.productive_seconds,
                    sas.applications_used, sas.directories_affected, sas.total_file_operations,
                    sas.processes_started,
                    sps.status AS processing_status
                FROM sessions s
                JOIN employees e ON s.employee_id = e.employee_id
                LEFT JOIN session_activity_summary sas ON s.session_id = sas.session_id
                LEFT JOIN session_processing_status sps ON s.session_id = sps.session_id
                {where_clause}
                ORDER BY s.start_time DESC
                LIMIT %s OFFSET %s;
            """
            params.extend([limit, offset])

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            cols = [
                "session_id", "employee_id", "employee_name", "username", "machine_name",
                "start_time", "end_time", "duration_seconds",
                "active_seconds", "desktop_seconds", "productive_seconds",
                "applications_used", "directories_affected", "total_file_operations",
                "processes_started", "processing_status",
            ]
            results = []
            for r in rows:
                item = dict(zip(cols, r))
                item["start_time"] = _serialize_dt(item["start_time"])
                item["end_time"] = _serialize_dt(item["end_time"])
                item["applications_used"] = list(item["applications_used"] or [])
                results.append(item)
            return results
    finally:
        conn.close()


def get_session_details(session_id: str) -> dict[str, Any] | None:
    """Fetch complete breakdown of a single session."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Base session and employee
            cur.execute(
                """
                SELECT
                    s.session_id, s.employee_id, e.employee_name, e.username, e.machine_name,
                    s.start_time, s.end_time, s.duration_seconds, s.schema_version, s.ingested_at,
                    sas.active_seconds, sas.desktop_seconds, sas.productive_seconds,
                    sas.applications_used, sas.directories_affected, sas.total_file_operations,
                    sas.processes_started, sas.processes_stopped, sas.file_extensions,
                    sps.status AS processing_status, sps.documents_count
                FROM sessions s
                JOIN employees e ON s.employee_id = e.employee_id
                LEFT JOIN session_activity_summary sas ON s.session_id = sas.session_id
                LEFT JOIN session_processing_status sps ON s.session_id = sps.session_id
                WHERE s.session_id = %s;
                """,
                (session_id,),
            )
            base_row = cur.fetchone()
            if not base_row:
                return None

            cols = [
                "session_id", "employee_id", "employee_name", "username", "machine_name",
                "start_time", "end_time", "duration_seconds", "schema_version", "ingested_at",
                "active_seconds", "desktop_seconds", "productive_seconds",
                "applications_used", "directories_affected", "total_file_operations",
                "processes_started", "processes_stopped", "file_extensions",
                "processing_status", "documents_count",
            ]
            session_info = dict(zip(cols, base_row))
            session_info["start_time"] = _serialize_dt(session_info["start_time"])
            session_info["end_time"] = _serialize_dt(session_info["end_time"])
            session_info["ingested_at"] = _serialize_dt(session_info["ingested_at"])
            session_info["applications_used"] = list(session_info["applications_used"] or [])

            # 2. Application focus
            cur.execute(
                """
                SELECT af.process_name, af.focus_seconds, af.focus_pct,
                       ac.display_name, ac.category, ac.is_productive
                FROM application_focus af
                LEFT JOIN application_catalog ac ON af.process_name = ac.process_name
                WHERE af.session_id = %s
                ORDER BY af.focus_seconds DESC;
                """,
                (session_id,),
            )
            apps = [
                {
                    "process_name": r[0],
                    "focus_seconds": float(r[1]),
                    "focus_pct": float(r[2]) if r[2] is not None else None,
                    "display_name": r[3],
                    "category": r[4],
                    "is_productive": r[5],
                }
                for r in cur.fetchall()
            ]

            # 3. Directory activity
            cur.execute(
                """
                SELECT directory_path, total_operations, ops_created, ops_modified,
                       ops_deleted, ops_moved, unique_file_count, file_extensions,
                       period_start, period_end, period_seconds
                FROM directory_activity
                WHERE session_id = %s
                ORDER BY total_operations DESC;
                """,
                (session_id,),
            )
            directories = [
                {
                    "directory_path": r[0],
                    "total_operations": r[1],
                    "ops_created": r[2],
                    "ops_modified": r[3],
                    "ops_deleted": r[4],
                    "ops_moved": r[5],
                    "unique_file_count": r[6],
                    "file_extensions": r[7] if isinstance(r[7], dict) else {},
                    "period_start": _serialize_dt(r[8]),
                    "period_end": _serialize_dt(r[9]),
                    "period_seconds": r[10],
                }
                for r in cur.fetchall()
            ]

            # 4. Process events
            cur.execute(
                """
                SELECT event_id, event_type, process_name, pid, executable, occurred_at
                FROM process_events
                WHERE session_id = %s
                ORDER BY occurred_at ASC;
                """,
                (session_id,),
            )
            processes = [
                {
                    "event_id": r[0],
                    "event_type": r[1],
                    "process_name": r[2],
                    "pid": r[3],
                    "executable": r[4],
                    "occurred_at": _serialize_dt(r[5]),
                }
                for r in cur.fetchall()
            ]

            # 5. Analysis documents titles
            cur.execute(
                "SELECT id, doc_type, title FROM analysis_documents WHERE session_id = %s ORDER BY id ASC;",
                (session_id,),
            )
            documents = [
                {"id": r[0], "doc_type": r[1], "title": r[2]}
                for r in cur.fetchall()
            ]

            return {
                "session": session_info,
                "applications": apps,
                "directories": directories,
                "process_events": processes,
                "analysis_documents": documents,
            }
    finally:
        conn.close()


def get_application_usage(
    employee_id: str | None = None,
    date: str | None = None,
    process_name: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve aggregated application usage statistics.

    Answers questions like: 'How much time did employee X spend on VS Code?'
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            conditions = ["af.process_name != 'Desktop'"]
            params: list[Any] = []

            if employee_id:
                conditions.append("(s.employee_id = %s OR e.username = %s)")
                params.extend([employee_id, employee_id])

            if date:
                conditions.append("(DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)")
                params.extend([date, date])

            if process_name:
                conditions.append("(af.process_name ILIKE %s OR ac.display_name ILIKE %s)")
                params.extend([f"%{process_name}%", f"%{process_name}%"])

            where_clause = f"WHERE {' AND '.join(conditions)}"

            query = f"""
                SELECT
                    af.process_name,
                    COALESCE(ac.display_name, af.process_name) AS display_name,
                    ac.category,
                    ac.is_productive,
                    COUNT(DISTINCT s.session_id) AS sessions_used_in,
                    ROUND(SUM(af.focus_seconds)::numeric, 1) AS total_focus_seconds,
                    ROUND(AVG(af.focus_pct)::numeric, 1) AS avg_focus_pct,
                    MAX(s.start_time) AS last_used_at
                FROM application_focus af
                JOIN sessions s ON af.session_id = s.session_id
                JOIN employees e ON s.employee_id = e.employee_id
                LEFT JOIN application_catalog ac ON af.process_name = ac.process_name
                {where_clause}
                GROUP BY af.process_name, ac.display_name, ac.category, ac.is_productive
                ORDER BY total_focus_seconds DESC
                LIMIT %s;
            """
            params.append(limit)

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            cols = [
                "process_name", "display_name", "category", "is_productive",
                "sessions_used_in", "total_focus_seconds", "avg_focus_pct", "last_used_at",
            ]
            results = []
            for r in rows:
                item = dict(zip(cols, r))
                item["total_focus_seconds"] = float(item["total_focus_seconds"]) if item["total_focus_seconds"] else 0.0
                item["avg_focus_pct"] = float(item["avg_focus_pct"]) if item["avg_focus_pct"] else 0.0
                item["last_used_at"] = _serialize_dt(item["last_used_at"])
                results.append(item)
            return results
    finally:
        conn.close()


def get_daily_summary(employee_id: str, date: str) -> dict[str, Any] | None:
    """Aggregate all sessions for an employee on a specific date (YYYY-MM-DD).

    Answers questions like: 'What did employee X do yesterday?'
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Base employee verification
            cur.execute(
                """
                SELECT employee_id, employee_name, username, machine_name
                FROM employees
                WHERE employee_id = %s OR username = %s LIMIT 1;
                """,
                (employee_id, employee_id),
            )
            emp_row = cur.fetchone()
            if not emp_row:
                return None

            emp_id, emp_name, username, machine_name = emp_row

            # 2. Aggregates over the day's sessions (supports UTC or local date)
            cur.execute(
                """
                SELECT
                    COUNT(s.session_id) AS total_sessions,
                    COALESCE(SUM(s.duration_seconds), 0) AS total_duration_seconds,
                    COALESCE(SUM(sas.active_seconds), 0) AS active_seconds,
                    COALESCE(SUM(sas.desktop_seconds), 0) AS desktop_seconds,
                    COALESCE(SUM(sas.productive_seconds), 0) AS productive_seconds,
                    COALESCE(SUM(sas.total_file_operations), 0) AS total_file_operations,
                    COALESCE(SUM(sas.processes_started), 0) AS processes_started,
                    MIN(s.start_time) AS earliest_start,
                    MAX(s.end_time) AS latest_end
                FROM sessions s
                LEFT JOIN session_activity_summary sas ON s.session_id = sas.session_id
                WHERE s.employee_id = %s
                  AND (DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date);
                """,
                (emp_id, date, date),
            )
            agg = cur.fetchone()
            if not agg or agg[0] == 0:
                return {
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "username": username,
                    "machine_name": machine_name,
                    "date": date,
                    "total_sessions": 0,
                    "total_duration_seconds": 0,
                    "active_seconds": 0,
                    "desktop_seconds": 0,
                    "productive_seconds": 0,
                    "productive_pct": 0.0,
                    "earliest_start": None,
                    "latest_end": None,
                    "total_file_operations": 0,
                    "processes_started": 0,
                    "top_applications": [],
                    "top_directories": [],
                    "message": f"No sessions recorded for {username or emp_id} on {date}.",
                }

            (
                total_sessions, total_duration, active_secs, desktop_secs,
                prod_secs, file_ops, proc_started, earliest, latest
            ) = agg

            # 3. Top applications used that day
            cur.execute(
                """
                SELECT
                    af.process_name,
                    COALESCE(ac.display_name, af.process_name) AS display_name,
                    ac.category,
                    ac.is_productive,
                    ROUND(SUM(af.focus_seconds)::numeric, 1) AS total_seconds
                FROM application_focus af
                JOIN sessions s ON af.session_id = s.session_id
                LEFT JOIN application_catalog ac ON af.process_name = ac.process_name
                WHERE s.employee_id = %s
                  AND (DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)
                  AND af.process_name != 'Desktop'
                GROUP BY af.process_name, ac.display_name, ac.category, ac.is_productive
                ORDER BY total_seconds DESC
                LIMIT 5;
                """,
                (emp_id, date, date),
            )

            top_apps = [
                {
                    "process_name": r[0],
                    "display_name": r[1],
                    "category": r[2],
                    "is_productive": r[3],
                    "focus_seconds": float(r[4]),
                }
                for r in cur.fetchall()
            ]

            # 4. Top directories affected that day
            cur.execute(
                """
                SELECT da.directory_path, SUM(da.total_operations) AS total_ops
                FROM directory_activity da
                JOIN sessions s ON da.session_id = s.session_id
                WHERE s.employee_id = %s
                  AND (DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)
                GROUP BY da.directory_path
                ORDER BY total_ops DESC
                LIMIT 5;
                """,
                (emp_id, date, date),
            )
            top_dirs = [{"directory_path": r[0], "operations": r[1]} for r in cur.fetchall()]

            prod_pct = round(prod_secs / total_duration * 100, 1) if total_duration else 0.0

            return {
                "employee_id": emp_id,
                "employee_name": emp_name,
                "username": username,
                "machine_name": machine_name,
                "date": date,
                "total_sessions": total_sessions,
                "total_duration_seconds": total_duration,
                "active_seconds": active_secs,
                "desktop_seconds": desktop_secs,
                "productive_seconds": prod_secs,
                "productive_pct": prod_pct,
                "earliest_start": _serialize_dt(earliest),
                "latest_end": _serialize_dt(latest),
                "total_file_operations": file_ops,
                "processes_started": proc_started,
                "top_applications": top_apps,
                "top_directories": top_dirs,
            }
    finally:
        conn.close()


def get_project_file_activity(
    employee_id: str | None = None,
    directory_path: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve directory and project-level file modification statistics."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            conditions = []
            params: list[Any] = []

            if employee_id:
                conditions.append("(s.employee_id = %s OR e.username = %s)")
                params.extend([employee_id, employee_id])

            if directory_path:
                conditions.append("da.directory_path ILIKE %s")
                params.append(f"%{directory_path}%")

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
                SELECT
                    da.directory_path,
                    COUNT(DISTINCT s.session_id) AS sessions_count,
                    SUM(da.total_operations) AS total_operations,
                    SUM(da.ops_created) AS total_created,
                    SUM(da.ops_modified) AS total_modified,
                    SUM(da.ops_deleted) AS total_deleted,
                    SUM(da.unique_file_count) AS total_unique_files,
                    MIN(da.period_start) AS first_activity_at,
                    MAX(da.period_end) AS last_activity_at
                FROM directory_activity da
                JOIN sessions s ON da.session_id = s.session_id
                JOIN employees e ON s.employee_id = e.employee_id
                {where_clause}
                GROUP BY da.directory_path
                ORDER BY total_operations DESC
                LIMIT %s;
            """
            params.append(limit)

            cur.execute(query, tuple(params))
            rows = cur.fetchall()
            cols = [
                "directory_path", "sessions_count", "total_operations",
                "total_created", "total_modified", "total_deleted",
                "total_unique_files", "first_activity_at", "last_activity_at",
            ]
            results = []
            for r in rows:
                item = dict(zip(cols, r))
                item["first_activity_at"] = _serialize_dt(item["first_activity_at"])
                item["last_activity_at"] = _serialize_dt(item["last_activity_at"])
                results.append(item)
            return results
    finally:
        conn.close()
