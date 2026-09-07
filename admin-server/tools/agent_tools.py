"""Pre-packaged agent tools ready for LangGraph agents (Phase 5).

Each tool has complete type hints and descriptive docstrings explaining its purpose,
parameters, and output format for LLM function/tool calling.
"""

from __future__ import annotations

from typing import Any

from retrieval.semantic import search_employee_activity
from retrieval.structured import (
    get_application_usage,
    get_daily_summary,
    get_employee,
    get_project_file_activity,
    get_session_details,
    get_sessions,
    list_employees,
)


def tool_get_employee(identifier: str) -> dict[str, Any]:
    """Retrieve profile and employment information for an employee.

    Use this tool when you need to know who an employee is, their machine name,
    username, when they were first or last seen, or their total recorded sessions.

    Parameters
    ----------
    identifier : str
        Employee ID (e.g. 'SYS-B56B4DEB06F6'), username (e.g. 'arif.arshad'),
        or partial employee name.

    Returns
    -------
    dict
        Profile information or a message if not found.
    """
    res = get_employee(identifier)
    if not res:
        return {"error": f"Employee '{identifier}' not found in the system."}
    return res


def tool_list_employees(limit: int = 50) -> list[dict[str, Any]]:
    """List registered employees in the organization with session summaries.

    Use this tool when the user asks 'Who are the employees?', 'List all workers',
    or needs an overview of active machines and users.

    Parameters
    ----------
    limit : int, default 50
        Maximum number of employees to return.

    Returns
    -------
    list of dict
        List of employee profiles with total session counts and last active dates.
    """
    return list_employees(limit=limit)


def tool_get_sessions(
    employee_id: str | None = None,
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Query chronological session logs filtered by employee or date range.

    Use this tool when asked: 'Show me sessions for employee X', 'What sessions occurred on YYYY-MM-DD?',
    or to inspect recent work sessions.

    Parameters
    ----------
    employee_id : str, optional
        Target employee ID or username.
    date : str, optional
        Target date in 'YYYY-MM-DD' format.
    start_date : str, optional
        ISO timestamp or date for beginning of search window.
    end_date : str, optional
        ISO timestamp or date for end of search window.
    limit : int, default 20
        Maximum number of sessions to return.

    Returns
    -------
    list of dict
        List of session summaries including durations, active/desktop time, and apps used.
    """
    return get_sessions(
        employee_id=employee_id,
        date=date,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


def tool_get_session_details(session_id: str) -> dict[str, Any]:
    """Retrieve in-depth activity details for a specific session ID.

    Use this tool when you need granular insight into a single session: exactly which
    applications were focused, which directories and files were touched, and process starts/stops.

    Parameters
    ----------
    session_id : str
        Unique session identifier (e.g. 'sess_306d14030496').

    Returns
    -------
    dict
        Comprehensive breakdown of the session, applications, file ops, and processes.
    """
    res = get_session_details(session_id)
    if not res:
        return {"error": f"Session '{session_id}' not found."}
    return res


def tool_get_application_usage(
    employee_id: str | None = None,
    date: str | None = None,
    process_name: str | None = None,
) -> list[dict[str, Any]]:
    """Query aggregated application usage time and focus percentages.

    Use this tool to answer: 'How much time did employee X spend on VS Code?',
    'What apps were used yesterday?', or 'Who used Chrome?'.

    Parameters
    ----------
    employee_id : str, optional
        Target employee ID or username.
    date : str, optional
        Target date in 'YYYY-MM-DD' format.
    process_name : str, optional
        Specific app name to filter by (e.g. 'Code', 'python.exe', 'photolaunch.exe').

    Returns
    -------
    list of dict
        List of applications with total focus seconds, percentage, category, and productivity flag.
    """
    return get_application_usage(
        employee_id=employee_id,
        date=date,
        process_name=process_name,
    )


def tool_get_daily_summary(employee_id: str, date: str) -> dict[str, Any]:
    """Retrieve an employee's aggregated daily activity summary for a specific date.

    Use this tool to answer: 'What did employee X do yesterday?', 'Give me a summary of X on YYYY-MM-DD',
    or to assess daily productive time versus idle time.

    Parameters
    ----------
    employee_id : str
        Target employee ID or username.
    date : str
        Date in 'YYYY-MM-DD' format.

    Returns
    -------
    dict
        Daily summary containing total work time, active time, productive time, top applications,
        and total file operations.
    """
    res = get_daily_summary(employee_id, date)
    if not res:
        return {"error": f"No employee found matching '{employee_id}'."}
    return res


def tool_get_project_file_activity(
    employee_id: str | None = None,
    directory_path: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve project directory file modifications and operation breakdowns.

    Use this tool when asked: 'What projects or folders did employee X work on?',
    'Were any files deleted or modified?', or 'Show activity in directory Y'.

    Parameters
    ----------
    employee_id : str, optional
        Target employee ID or username.
    directory_path : str, optional
        Sub-path or folder name to filter by (e.g. 'MicroAI', 'lung_n').
    limit : int, default 20
        Maximum number of directories to return.

    Returns
    -------
    list of dict
        Directory paths with operation breakdown (created, modified, deleted) and unique file counts.
    """
    return get_project_file_activity(
        employee_id=employee_id,
        directory_path=directory_path,
        limit=limit,
    )


def tool_search_employee_activity(
    query: str,
    employee_id: str | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Perform semantic natural language search over observed session activities and documents.

    Use this tool for open-ended, descriptive, or fuzzy queries like: 'batch image processing',
    'medical dataset changes', 'script executions', or 'debugging sessions'.

    Parameters
    ----------
    query : str
        Natural language description of the activity to look for.
    employee_id : str, optional
        Target employee ID or username to restrict the search.
    k : int, default 5
        Number of top matching documents to return.

    Returns
    -------
    list of dict
        List of matching document snippets with relevance scores and metadata.
    """
    return search_employee_activity(
        query=query,
        employee_id=employee_id,
        k=k,
    )


# Registry of all agent tools for easy programmatic access and inspection
ALL_AGENT_TOOLS = [
    tool_get_employee,
    tool_list_employees,
    tool_get_sessions,
    tool_get_session_details,
    tool_get_application_usage,
    tool_get_daily_summary,
    tool_get_project_file_activity,
    tool_search_employee_activity,
]
