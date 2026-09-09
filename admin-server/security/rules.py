"""Deterministic Security Analytics Layer for WorkGuard.

Implements rule-based forensic detection against PostgreSQL session telemetry
following the principle:
    Detection   -> Deterministic Rules / Analytics
    Explanation -> LLM (Ollama)
"""

from __future__ import annotations

import logging
from datetime import datetime, time as dtime, timezone
from typing import Any

from database.connection import get_connection

logger = logging.getLogger(__name__)

# Standard operational hours window (07:00 to 20:00)
CORE_HOURS_START = dtime(7, 0)
CORE_HOURS_END = dtime(20, 0)


def detect_after_hours_activity(
    session_id: str | None = None,
    employee_id: str | None = None,
    date_str: str | None = None,
) -> list[dict[str, Any]]:
    """Detect sessions started or operated outside standard core hours."""
    findings = []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT s.session_id, s.employee_id, e.employee_name, e.username,
                       s.start_time, s.end_time, s.duration_seconds
                FROM sessions s
                LEFT JOIN employees e ON s.employee_id = e.employee_id
                WHERE 1=1
            """
            params: list[Any] = []
            if session_id:
                query += " AND s.session_id = %s"
                params.append(session_id)
            if employee_id:
                query += " AND (s.employee_id = %s OR e.username = %s)"
                params.extend([employee_id, employee_id])
            if date_str:
                query += " AND (DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)"
                params.extend([date_str, date_str])

            query += " ORDER BY s.start_time DESC LIMIT 50;"
            cur.execute(query, params)
            rows = cur.fetchall()

            for row in rows:
                sid, eid, ename, username, st, et, dur = row
                if not st:
                    continue
                # Check local or UTC time
                session_time = st.time() if hasattr(st, "time") else None
                if session_time:
                    is_after_hours = session_time < CORE_HOURS_START or session_time > CORE_HOURS_END
                    if is_after_hours:
                        findings.append({
                            "rule": "after_hours_activity",
                            "severity": "LOW" if (dur or 0) < 1800 else "MEDIUM",
                            "session_id": sid,
                            "employee_id": eid,
                            "employee_name": ename or username,
                            "description": (
                                f"Session started at {st.strftime('%H:%M:%S')} outside standard operational "
                                f"hours (07:00-20:00)."
                            ),
                            "evidence": {
                                "start_time": st.isoformat(),
                                "duration_seconds": dur,
                            },
                        })
    finally:
        conn.close()
    return findings


def detect_high_frequency_file_mutations(
    session_id: str | None = None,
    employee_id: str | None = None,
    date_str: str | None = None,
) -> list[dict[str, Any]]:
    """Detect abnormal volume or velocity of file operations."""
    findings = []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT s.session_id, s.employee_id, e.employee_name, e.username,
                       s.duration_seconds, a.total_file_operations, a.productive_seconds
                FROM sessions s
                JOIN session_activity_summary a ON s.session_id = a.session_id
                LEFT JOIN employees e ON s.employee_id = e.employee_id
                WHERE 1=1
            """
            params: list[Any] = []
            if session_id:
                query += " AND s.session_id = %s"
                params.append(session_id)
            if employee_id:
                query += " AND (s.employee_id = %s OR e.username = %s)"
                params.extend([employee_id, employee_id])
            if date_str:
                query += " AND (DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)"
                params.extend([date_str, date_str])

            query += " ORDER BY s.start_time DESC LIMIT 50;"
            cur.execute(query, params)
            rows = cur.fetchall()

            for row in rows:
                sid, eid, ename, username, dur, file_ops, prod_secs = row
                dur = dur or 1
                ops = file_ops or 0

                # High volume burst rule (>1000 ops in a short session or >5 ops/sec)
                ops_per_sec = ops / max(dur, 1)
                if ops >= 1000 or ops_per_sec >= 4.0:
                    severity = "HIGH" if (ops > 5000 or ops_per_sec > 10.0) else "MEDIUM"
                    findings.append({
                        "rule": "high_volume_file_mutations",
                        "severity": severity,
                        "session_id": sid,
                        "employee_id": eid,
                        "employee_name": ename or username,
                        "description": (
                            f"Rapid file operation rate detected: {ops} file operations across {dur}s "
                            f"({ops_per_sec:.2f} ops/sec)."
                        ),
                        "evidence": {
                            "total_file_operations": ops,
                            "duration_seconds": dur,
                            "velocity_ops_per_sec": round(ops_per_sec, 2),
                        },
                    })
    finally:
        conn.close()
    return findings


def detect_unapproved_or_unknown_applications(
    session_id: str | None = None,
    employee_id: str | None = None,
    date_str: str | None = None,
) -> list[dict[str, Any]]:
    """Detect execution of uncataloged or non-approved applications."""
    findings = []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT s.session_id, s.employee_id, e.employee_name, e.username,
                       f.process_name, f.focus_seconds,
                       c.id AS catalog_id, c.display_name, c.is_productive, c.category
                FROM application_focus f
                JOIN sessions s ON f.session_id = s.session_id
                LEFT JOIN employees e ON s.employee_id = e.employee_id
                LEFT JOIN application_catalog c ON LOWER(f.process_name) = LOWER(c.process_name)
                WHERE 1=1
            """
            params: list[Any] = []
            if session_id:
                query += " AND s.session_id = %s"
                params.append(session_id)
            if employee_id:
                query += " AND (s.employee_id = %s OR e.username = %s)"
                params.extend([employee_id, employee_id])
            if date_str:
                query += " AND (DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)"
                params.extend([date_str, date_str])

            cur.execute(query, params)
            rows = cur.fetchall()

            for row in rows:
                sid, eid, ename, username, proc, focus_sec, cat_id, dname, is_prod, category = row
                # Ignore standard benign desktop/explorer/idle processes
                if proc.lower() in ("desktop", "explorer.exe", "system"):
                    continue

                if cat_id is None:
                    findings.append({
                        "rule": "uncataloged_application_execution",
                        "severity": "LOW",
                        "session_id": sid,
                        "employee_id": eid,
                        "employee_name": ename or username,
                        "description": (
                            f"Uncataloged executable '{proc}' ran for {round(focus_sec or 0)}s "
                            f"without an organizational catalog entry."
                        ),
                        "evidence": {
                            "executable": proc,
                            "focus_seconds": focus_sec,
                        },
                    })
                elif is_prod is False and category in ("restricted", "security_risk"):
                    findings.append({
                        "rule": "restricted_application_policy_violation",
                        "severity": "HIGH",
                        "session_id": sid,
                        "employee_id": eid,
                        "employee_name": ename or username,
                        "description": f"Restricted software '{dname or proc}' ({category}) active for {round(focus_sec or 0)}s.",
                        "evidence": {
                            "executable": proc,
                            "category": category,
                            "focus_seconds": focus_sec,
                        },
                    })
    finally:
        conn.close()
    return findings


def detect_excessive_idle_ratio(
    session_id: str | None = None,
    employee_id: str | None = None,
    date_str: str | None = None,
) -> list[dict[str, Any]]:
    """Detect sessions with disproportionate idle or unmonitored desktop time."""
    findings = []
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT s.session_id, s.employee_id, e.employee_name, e.username,
                       s.duration_seconds, a.active_seconds, a.productive_seconds, a.desktop_seconds
                FROM sessions s
                JOIN session_activity_summary a ON s.session_id = a.session_id
                LEFT JOIN employees e ON s.employee_id = e.employee_id
                WHERE s.duration_seconds >= 600
            """
            params: list[Any] = []
            if session_id:
                query += " AND s.session_id = %s"
                params.append(session_id)
            if employee_id:
                query += " AND (s.employee_id = %s OR e.username = %s)"
                params.extend([employee_id, employee_id])
            if date_str:
                query += " AND (DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)"
                params.extend([date_str, date_str])

            cur.execute(query, params)
            rows = cur.fetchall()

            for row in rows:
                sid, eid, ename, username, dur, active_sec, prod_sec, desktop_sec = row
                dur = dur or 1
                active_sec = active_sec or 0
                idle_sec = desktop_sec if (desktop_sec and desktop_sec > 0) else max(0, dur - active_sec)
                idle_ratio = idle_sec / dur

                if idle_ratio >= 0.70:
                    findings.append({
                        "rule": "excessive_idle_ratio",
                        "severity": "LOW",
                        "session_id": sid,
                        "employee_id": eid,
                        "employee_name": ename or username,
                        "description": (
                            f"Elevated idle time: {round(idle_ratio*100, 1)}% ({round(idle_sec)}s) "
                            f"of the {round(dur)}s session was inactive or at desktop."
                        ),
                        "evidence": {
                            "duration_seconds": dur,
                            "idle_seconds": idle_sec,
                            "idle_percentage": round(idle_ratio * 100, 1),
                        },
                    })
    finally:
        conn.close()
    return findings


def evaluate_security_telemetry(
    session_id: str | None = None,
    employee_id: str | None = None,
    date_str: str | None = None,
) -> dict[str, Any]:
    """Execute all deterministic security rules and compute an aggregate risk assessment."""
    findings: list[dict[str, Any]] = []

    # Run deterministic rules
    findings.extend(detect_after_hours_activity(session_id, employee_id, date_str))
    findings.extend(detect_high_frequency_file_mutations(session_id, employee_id, date_str))
    findings.extend(detect_unapproved_or_unknown_applications(session_id, employee_id, date_str))
    findings.extend(detect_excessive_idle_ratio(session_id, employee_id, date_str))

    # Calculate weighted risk score
    score = 0
    severity_weights = {
        "LOW": 10,
        "MEDIUM": 25,
        "HIGH": 50,
        "CRITICAL": 80,
    }
    for f in findings:
        score += severity_weights.get(f.get("severity", "LOW"), 10)

    risk_score = min(score, 100)

    if risk_score >= 80:
        risk_level = "CRITICAL"
    elif risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 20:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Count distinct sessions evaluated
    conn = get_connection()
    target_info = {"employee_id": employee_id, "session_id": session_id, "date": date_str}
    sessions_evaluated = 0
    try:
        with conn.cursor() as cur:
            q = "SELECT COUNT(*), MAX(e.employee_name) FROM sessions s LEFT JOIN employees e ON s.employee_id = e.employee_id WHERE 1=1"
            p: list[Any] = []
            if session_id:
                q += " AND s.session_id = %s"
                p.append(session_id)
            if employee_id:
                q += " AND (s.employee_id = %s OR e.username = %s)"
                p.extend([employee_id, employee_id])
            if date_str:
                q += " AND (DATE(s.start_time AT TIME ZONE 'UTC') = %s::date OR DATE(s.start_time) = %s::date)"
                p.extend([date_str, date_str])
            cur.execute(q, p)
            row = cur.fetchone()
            sessions_evaluated = row[0] or 0
            if row[1]:
                target_info["employee_name"] = row[1]
    finally:
        conn.close()

    return {
        "target": target_info,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "total_findings": len(findings),
        "findings": findings,
        "sessions_evaluated": sessions_evaluated,
        "requires_admin_review": risk_score >= 20,
    }
