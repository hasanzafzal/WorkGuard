"""PostgreSQL tools forwarding to retrieval layer for backward compatibility and agent access."""

from __future__ import annotations

from typing import Any

from retrieval.structured import (
    get_application_usage as fetch_app_usage,
    get_daily_summary as fetch_daily_summary,
    get_employee as fetch_employee,
    get_project_file_activity as fetch_project_activity,
    get_session_details as fetch_session_details,
    get_sessions as fetch_sessions,
    list_employees as fetch_all_employees,
)


def get_employee(identifier: str) -> dict[str, Any] | None:
    """Retrieve employee details by ID, username, machine, or name."""
    return fetch_employee(identifier)


def list_employees(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    """Retrieve registered employees list."""
    return fetch_all_employees(limit=limit, offset=offset)


def get_session(session_id: str) -> dict[str, Any] | None:
    """Retrieve detailed session context by session ID."""
    return fetch_session_details(session_id)


def list_sessions(
    employee_id: str | None = None,
    date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Retrieve sessions matching employee and date filters."""
    return fetch_sessions(employee_id=employee_id, date=date, limit=limit, offset=offset)


def get_session_context(session_id: str) -> dict[str, Any]:
    """Retrieve full session context including applications, directory ops, and processes."""
    res = fetch_session_details(session_id)
    return res or {}


def get_application_usage(
    employee_id: str | None = None,
    date: str | None = None,
    process_name: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve application usage statistics."""
    return fetch_app_usage(employee_id=employee_id, date=date, process_name=process_name)


def get_daily_summary(employee_id: str, date: str) -> dict[str, Any] | None:
    """Retrieve an employee's aggregated daily activity summary."""
    return fetch_daily_summary(employee_id=employee_id, date=date)


def get_project_file_activity(
    employee_id: str | None = None,
    directory_path: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve directory and file modification statistics."""
    return fetch_project_activity(employee_id=employee_id, directory_path=directory_path, limit=limit)
