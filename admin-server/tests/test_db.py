"""Initialize and inspect the WorkGuard PostgreSQL database."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import initialize_database
from database.repository import (
    fetch_dashboard_stats,
    fetch_employees,
    fetch_reports,
    fetch_sessions,
)


def main() -> None:
    initialize_database()
    print("Database schema initialized.")

    stats = fetch_dashboard_stats()
    print("Stats:", stats)

    sessions = fetch_sessions(limit=5)
    print("Recent sessions:", sessions)

    reports = fetch_reports(limit=5)
    print("Recent reports:", reports)

    employees = fetch_employees(limit=5)
    print("Employees:", employees)


if __name__ == "__main__":
    main()
