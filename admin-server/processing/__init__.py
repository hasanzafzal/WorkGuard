"""PostgreSQL-to-Processing Pipeline package."""

from processing.document_generator import (
    generate_all_documents,
    generate_application_usage_doc,
    generate_file_activity_doc,
    generate_process_activity_doc,
    generate_session_overview_doc,
)
from processing.models import (
    AnalysisDocument,
    ApplicationFocusItem,
    DirectoryActivityItem,
    NormalizedSession,
    ProcessEventItem,
)
from processing.normalizer import (
    calculate_and_update_productive_seconds,
    fetch_normalized_session,
)
from processing.pipeline import (
    get_pending_sessions,
    process_all_pending,
    process_session,
)

__all__ = [
    "AnalysisDocument",
    "ApplicationFocusItem",
    "DirectoryActivityItem",
    "NormalizedSession",
    "ProcessEventItem",
    "calculate_and_update_productive_seconds",
    "fetch_normalized_session",
    "generate_all_documents",
    "generate_application_usage_doc",
    "generate_file_activity_doc",
    "generate_process_activity_doc",
    "generate_session_overview_doc",
    "get_pending_sessions",
    "process_all_pending",
    "process_session",
]
