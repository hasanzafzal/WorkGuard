"""Repository helpers for WorkGuard PostgreSQL tables."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Json

from database.connection import get_connection


UPSERT_EMPLOYEE = """
INSERT INTO employees (employee_id, employee_name, first_seen, last_seen)
VALUES (%s, %s, %s, %s)
ON CONFLICT (employee_id) DO UPDATE SET
    employee_name = EXCLUDED.employee_name,
    last_seen = EXCLUDED.last_seen;
"""

INSERT_SESSION = """
INSERT INTO sessions (
    session_id, employee_id, start_time, end_time, duration_seconds,
    focus_summary, metadata, received_at, status
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (session_id) DO NOTHING;
"""

INSERT_SESSION_EVENT = """
INSERT INTO session_events (
    event_id, session_id, event_type, source, timestamp, data
) VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (event_id) DO NOTHING;
"""

UPDATE_SESSION_PROCESSED = """
UPDATE sessions SET
    processed_at = %s,
    status = 'processed',
    updated_at = %s
WHERE session_id = %s;
"""

INSERT_REPORT = """
INSERT INTO reports (
    session_id, employee_id, summary, productivity_assessment,
    key_activities, focus_observations, recommended_follow_up,
    knowledge, security, errors, generated_at
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (session_id) DO UPDATE SET
    summary = EXCLUDED.summary,
    productivity_assessment = EXCLUDED.productivity_assessment,
    key_activities = EXCLUDED.key_activities,
    focus_observations = EXCLUDED.focus_observations,
    recommended_follow_up = EXCLUDED.recommended_follow_up,
    knowledge = EXCLUDED.knowledge,
    security = EXCLUDED.security,
    errors = EXCLUDED.errors,
    generated_at = EXCLUDED.generated_at;
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def persist_session(
    session: dict[str, Any],
    employee_name: str | None = None,
) -> None:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                UPSERT_EMPLOYEE,
                (
                    session.get("employee_id", ""),
                    employee_name or session.get("employee_name"),
                    _now(),
                    _now(),
                ),
            )

            session_data = session.get("session", {})
            cursor.execute(
                INSERT_SESSION,
                (
                    session.get("session_id", ""),
                    session.get("employee_id", ""),
                    session_data.get("start_time"),
                    session_data.get("end_time"),
                    session_data.get("duration_seconds"),
                    Json(session.get("focus_summary", {})),
                    Json(session.get("metadata", {})),
                    _now(),
                    "received",
                ),
            )

            for event in session.get("events", []):
                cursor.execute(
                    INSERT_SESSION_EVENT,
                    (
                        event.get("event_id", ""),
                        session.get("session_id", ""),
                        event.get("event_type", ""),
                        event.get("source", ""),
                        event.get("timestamp"),
                        Json(event.get("data", {})),
                    ),
                )
        connection.commit()
    finally:
        connection.close()


def mark_session_processed(session_id: str) -> None:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(UPDATE_SESSION_PROCESSED, (_now(), _now(), session_id))
        connection.commit()
    finally:
        connection.close()


def persist_report(report: dict[str, Any]) -> None:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                INSERT_REPORT,
                (
                    report.get("session_id", ""),
                    report.get("employee_id", ""),
                    report.get("session_analysis", {}).get("summary"),
                    report.get("session_analysis", {}).get("productivity_assessment"),
                    Json(report.get("session_analysis", {}).get("key_activities", [])),
                    Json(report.get("session_analysis", {}).get("focus_observations", [])),
                    Json(report.get("session_analysis", {}).get("recommended_follow_up", [])),
                    Json(report.get("knowledge", {})),
                    Json(report.get("security", {})),
                    Json(report.get("errors", [])),
                    report.get("generated_at"),
                ),
            )
        connection.commit()
    finally:
        connection.close()


def fetch_sessions(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, employee_id, start_time, end_time,
                       duration_seconds, focus_summary, metadata,
                       received_at, processed_at, status
                FROM sessions
                ORDER BY start_time DESC
                LIMIT %s OFFSET %s;
                """,
                (limit, offset),
            )
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    finally:
        connection.close()


def fetch_session(session_id: str) -> dict[str, Any] | None:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, employee_id, start_time, end_time,
                       duration_seconds, focus_summary, metadata,
                       received_at, processed_at, status
                FROM sessions
                WHERE session_id = %s;
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
    finally:
        connection.close()


def fetch_employees(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT employee_id, employee_name, first_seen, last_seen
                FROM employees
                ORDER BY last_seen DESC
                LIMIT %s OFFSET %s;
                """,
                (limit, offset),
            )
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    finally:
        connection.close()


def fetch_reports(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, employee_id, summary, productivity_assessment,
                       key_activities, focus_observations, recommended_follow_up,
                       knowledge, security, errors, generated_at
                FROM reports
                ORDER BY generated_at DESC
                LIMIT %s OFFSET %s;
                """,
                (limit, offset),
            )
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    finally:
        connection.close()


def fetch_report(session_id: str) -> dict[str, Any] | None:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, employee_id, summary, productivity_assessment,
                       key_activities, focus_observations, recommended_follow_up,
                       knowledge, security, errors, generated_at
                FROM reports
                WHERE session_id = %s;
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
    finally:
        connection.close()


def fetch_dashboard_stats() -> dict[str, Any]:
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE s.status = 'received') AS pending_sessions,
                    COUNT(*) FILTER (WHERE s.status = 'processed') AS processed_sessions,
                    COUNT(DISTINCT s.employee_id) AS total_employees,
                    COUNT(DISTINCT r.session_id) AS reports_generated,
                    AVG(s.duration_seconds) AS avg_duration_seconds,
                    MAX(s.start_time) AS latest_session_start
                FROM sessions s
                LEFT JOIN reports r ON r.session_id = s.session_id;
                """
            )
            row = cursor.fetchone()
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
            for key, value in result.items():
                if value is None:
                    result[key] = 0 if key != "latest_session_start" else None
            return result
    finally:
        connection.close()
