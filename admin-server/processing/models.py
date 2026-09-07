"""Data models for the PostgreSQL-to-Processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AnalysisDocument:
    """A natural language document derived from structured PostgreSQL session records."""

    session_id: str
    employee_id: str
    doc_type: str  # 'session_overview', 'application_usage', 'file_activity', 'process_activity'
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApplicationFocusItem:
    process_name: str
    focus_seconds: float
    focus_pct: float | None
    display_name: str | None = None
    category: str | None = None
    is_productive: bool | None = None


@dataclass
class DirectoryActivityItem:
    directory_path: str
    total_operations: int
    ops_created: int
    ops_modified: int
    ops_deleted: int
    ops_moved: int
    unique_file_count: int
    file_extensions: dict[str, int] = field(default_factory=dict)
    period_start: datetime | None = None
    period_end: datetime | None = None
    period_seconds: int | None = None


@dataclass
class ProcessEventItem:
    event_id: str
    event_type: str
    process_name: str
    pid: int | None
    executable: str | None
    occurred_at: datetime | None


@dataclass
class NormalizedSession:
    """Complete aggregated session context fetched from PostgreSQL."""

    session_id: str
    employee_id: str
    employee_name: str
    machine_name: str | None
    username: str | None
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    schema_version: str | None
    session_file_path: str | None
    ingested_at: datetime

    # Aggregates from summary table
    applications_used: list[str] = field(default_factory=list)
    desktop_seconds: int = 0
    active_seconds: int = 0
    processes_started: int = 0
    processes_stopped: int = 0
    processes_used: list[str] = field(default_factory=list)
    directories_affected: int = 0
    total_file_operations: int = 0
    file_extensions: dict[str, int] = field(default_factory=dict)
    productive_seconds: int | None = None

    # Detailed related items
    app_focus_items: list[ApplicationFocusItem] = field(default_factory=list)
    dir_activity_items: list[DirectoryActivityItem] = field(default_factory=list)
    process_event_items: list[ProcessEventItem] = field(default_factory=list)
