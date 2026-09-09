"""Generate structured analysis documents from normalized session data."""

from __future__ import annotations

from processing.models import AnalysisDocument, NormalizedSession


def _format_duration(seconds: int | float) -> str:
    """Format seconds into human-readable minutes and seconds string."""
    secs = int(round(seconds))
    if secs < 60:
        return f"{secs}s"
    minutes = secs // 60
    rem_secs = secs % 60
    if minutes < 60:
        return f"{minutes}m {rem_secs}s" if rem_secs else f"{minutes}m"
    hours = minutes // 60
    rem_mins = minutes % 60
    return f"{hours}h {rem_mins}m"


def generate_session_overview_doc(ns: NormalizedSession) -> AnalysisDocument:
    """Generate high-level session overview document."""
    user_str = ns.username or ns.employee_name
    machine_str = f" on machine {ns.machine_name}" if ns.machine_name else ""
    date_str = ns.start_time.strftime("%Y-%m-%d")
    start_str = ns.start_time.strftime("%H:%M:%S UTC")
    end_str = ns.end_time.strftime("%H:%M:%S UTC")

    lines = [
        f"Session Overview for Employee {user_str} ({ns.employee_id}){machine_str}.",
        f"Date: {date_str}. Time window: {start_str} to {end_str} ({_format_duration(ns.duration_seconds)} total).",
        f"Active Work Time: {_format_duration(ns.active_seconds)} ({round(ns.active_seconds / ns.duration_seconds * 100, 1) if ns.duration_seconds else 0}% of session).",
        f"Idle / Desktop Time: {_format_duration(ns.desktop_seconds)} ({round(ns.desktop_seconds / ns.duration_seconds * 100, 1) if ns.duration_seconds else 0}% of session).",
    ]

    if ns.productive_seconds is not None and ns.duration_seconds:
        prod_pct = round(ns.productive_seconds / ns.duration_seconds * 100, 1)
        lines.append(f"Productive Time: {_format_duration(ns.productive_seconds)} ({prod_pct}% of session).")

    if ns.applications_used:
        lines.append(f"Applications Used ({len(ns.applications_used)}): {', '.join(ns.applications_used)}.")

    if ns.app_focus_items:
        top_app = ns.app_focus_items[0]
        top_name = top_app.display_name or top_app.process_name
        lines.append(
            f"Primary Application: {top_name} ({_format_duration(top_app.focus_seconds)}, "
            f"{top_app.focus_pct or 0}% focus)."
        )

    if ns.total_file_operations > 0:
        ext_summary = ", ".join(f"{cnt} {ext}" for ext, cnt in sorted(ns.file_extensions.items(), key=lambda x: -x[1]))
        lines.append(
            f"File Activity: {ns.total_file_operations} file operations across {ns.directories_affected} directories "
            f"({ext_summary})."
        )
    else:
        lines.append("File Activity: No file system modifications recorded.")

    if ns.processes_started > 0 or ns.processes_stopped > 0:
        lines.append(
            f"Processes: {ns.processes_started} started, {ns.processes_stopped} stopped "
            f"(Processes: {', '.join(ns.processes_used) if ns.processes_used else 'none'})."
        )

    content = "\n".join(lines)
    title = f"Session Overview: {user_str} on {date_str} ({_format_duration(ns.duration_seconds)})"

    metadata = {
        "doc_type": "session_overview",
        "session_id": ns.session_id,
        "employee_id": ns.employee_id,
        "username": ns.username,
        "date": date_str,
        "duration_seconds": ns.duration_seconds,
        "active_seconds": ns.active_seconds,
        "desktop_seconds": ns.desktop_seconds,
        "productive_seconds": ns.productive_seconds,
        "applications_used": ns.applications_used,
        "total_file_operations": ns.total_file_operations,
    }

    return AnalysisDocument(
        session_id=ns.session_id,
        employee_id=ns.employee_id,
        doc_type="session_overview",
        title=title,
        content=content,
        metadata=metadata,
    )


def generate_application_usage_doc(ns: NormalizedSession) -> AnalysisDocument:
    """Generate detailed application usage analysis document."""
    user_str = ns.username or ns.employee_name
    date_str = ns.start_time.strftime("%Y-%m-%d")

    lines = [
        f"Application Usage Breakdown for {user_str} during session {ns.session_id} on {date_str}.",
        f"Total Duration: {_format_duration(ns.duration_seconds)} | Active Time: {_format_duration(ns.active_seconds)} | Desktop / Idle Time: {_format_duration(ns.desktop_seconds)}.",
        "",
        "Applications breakdown:",
    ]

    apps_meta = []
    for item in ns.app_focus_items:
        display = item.display_name or item.process_name
        cat_str = f" [Category: {item.category}]" if item.category else ""
        prod_str = " (Productive)" if item.is_productive is True else (" (Non-productive)" if item.is_productive is False else "")
        pct_str = f"{item.focus_pct}%" if item.focus_pct is not None else "N/A"
        lines.append(
            f"- {display} ({item.process_name}): {_format_duration(item.focus_seconds)} "
            f"({pct_str} of session duration){cat_str}{prod_str}"
        )
        apps_meta.append({
            "process_name": item.process_name,
            "display_name": item.display_name,
            "category": item.category,
            "is_productive": item.is_productive,
            "focus_seconds": item.focus_seconds,
            "focus_pct": item.focus_pct,
        })

    content = "\n".join(lines)
    title = f"Application Usage: {user_str} ({len(ns.app_focus_items)} apps, {date_str})"

    metadata = {
        "doc_type": "application_usage",
        "session_id": ns.session_id,
        "employee_id": ns.employee_id,
        "username": ns.username,
        "date": date_str,
        "applications": apps_meta,
    }

    return AnalysisDocument(
        session_id=ns.session_id,
        employee_id=ns.employee_id,
        doc_type="application_usage",
        title=title,
        content=content,
        metadata=metadata,
    )


def generate_file_activity_doc(ns: NormalizedSession) -> AnalysisDocument:
    """Generate project directory and file system activity analysis document."""
    user_str = ns.username or ns.employee_name
    date_str = ns.start_time.strftime("%Y-%m-%d")

    lines = [
        f"Project and File Activity for {user_str} during session {ns.session_id} on {date_str}.",
        f"Total File Operations: {ns.total_file_operations} across {ns.directories_affected} directories.",
    ]

    if ns.file_extensions:
        ext_list = [f"{ext}: {cnt} operations" for ext, cnt in sorted(ns.file_extensions.items(), key=lambda x: -x[1])]
        lines.append(f"File Types Breakdown: {', '.join(ext_list)}.")

    lines.append("")
    lines.append("Directory Details:")

    dirs_meta = []
    for item in ns.dir_activity_items:
        op_types = []
        if item.ops_modified:
            op_types.append(f"{item.ops_modified} modified")
        if item.ops_created:
            op_types.append(f"{item.ops_created} created")
        if item.ops_deleted:
            op_types.append(f"{item.ops_deleted} deleted")
        if item.ops_moved:
            op_types.append(f"{item.ops_moved} moved")

        op_str = ", ".join(op_types) if op_types else f"{item.total_operations} operations"
        ext_str = ", ".join(f"{cnt} {ext}" for ext, cnt in item.file_extensions.items()) if item.file_extensions else "unspecified"

        time_window = ""
        if item.period_start and item.period_end:
            time_window = f" (Window: {item.period_start.strftime('%H:%M:%S')} - {item.period_end.strftime('%H:%M:%S')} UTC)"

        lines.append(
            f"- Directory: {item.directory_path}\n"
            f"  Operations: {item.total_operations} ({op_str}) on {item.unique_file_count} unique files "
            f"[{ext_str}]{time_window}"
        )
        dirs_meta.append({
            "directory_path": item.directory_path,
            "total_operations": item.total_operations,
            "unique_file_count": item.unique_file_count,
            "file_extensions": item.file_extensions,
        })

    if not ns.dir_activity_items:
        lines.append("No file system operations detected during this session.")

    content = "\n".join(lines)
    title = f"File Activity: {user_str} ({ns.total_file_operations} ops, {ns.directories_affected} dirs, {date_str})"

    metadata = {
        "doc_type": "file_activity",
        "session_id": ns.session_id,
        "employee_id": ns.employee_id,
        "username": ns.username,
        "date": date_str,
        "total_file_operations": ns.total_file_operations,
        "directories_affected": ns.directories_affected,
        "file_extensions": ns.file_extensions,
        "top_directories": [d["directory_path"] for d in dirs_meta[:5]],
    }

    return AnalysisDocument(
        session_id=ns.session_id,
        employee_id=ns.employee_id,
        doc_type="file_activity",
        title=title,
        content=content,
        metadata=metadata,
    )


def generate_process_activity_doc(ns: NormalizedSession) -> AnalysisDocument:
    """Generate process executions and lifecycle activity document."""
    user_str = ns.username or ns.employee_name
    date_str = ns.start_time.strftime("%Y-%m-%d")

    lines = [
        f"Process Execution and Lifecycle Events for {user_str} during session {ns.session_id} on {date_str}.",
        f"Summary: {ns.processes_started} processes started, {ns.processes_stopped} processes stopped.",
    ]

    if ns.processes_used:
        lines.append(f"Distinct executables invoked: {', '.join(ns.processes_used)}.")

    lines.append("")
    lines.append("Process Events Timeline:")

    events_meta = []
    for evt in ns.process_event_items:
        ts_str = evt.occurred_at.strftime("%H:%M:%S UTC") if evt.occurred_at else "Unknown time"
        pid_str = f"PID {evt.pid}" if evt.pid else "PID unknown"
        exe_str = f" [Path: {evt.executable}]" if evt.executable else ""
        action = "Started" if evt.event_type == "application_started" else "Stopped"

        lines.append(f"- [{ts_str}] {action} {evt.process_name} ({pid_str}){exe_str}")
        events_meta.append({
            "event_id": evt.event_id,
            "event_type": evt.event_type,
            "process_name": evt.process_name,
            "pid": evt.pid,
            "executable": evt.executable,
        })

    if not ns.process_event_items:
        lines.append("No process start or stop events recorded during this session.")

    content = "\n".join(lines)
    title = f"Process Activity: {user_str} ({len(ns.process_event_items)} events, {date_str})"

    metadata = {
        "doc_type": "process_activity",
        "session_id": ns.session_id,
        "employee_id": ns.employee_id,
        "username": ns.username,
        "date": date_str,
        "processes_started": ns.processes_started,
        "processes_stopped": ns.processes_stopped,
        "processes_used": ns.processes_used,
        "event_count": len(ns.process_event_items),
    }

    return AnalysisDocument(
        session_id=ns.session_id,
        employee_id=ns.employee_id,
        doc_type="process_activity",
        title=title,
        content=content,
        metadata=metadata,
    )


def generate_all_documents(ns: NormalizedSession) -> list[AnalysisDocument]:
    """Generate complete suite of analysis documents for a session."""
    return [
        generate_session_overview_doc(ns),
        generate_application_usage_doc(ns),
        generate_file_activity_doc(ns),
        generate_process_activity_doc(ns),
    ]
