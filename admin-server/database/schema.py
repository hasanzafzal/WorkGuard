"""PostgreSQL schema and initialization for WorkGuard."""

from __future__ import annotations

CREATE_EMPLOYEES = """
CREATE TABLE IF NOT EXISTS employees (
    employee_id VARCHAR(255) PRIMARY KEY,
    employee_name VARCHAR(255),
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    employee_id VARCHAR(255) NOT NULL REFERENCES employees(employee_id),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_seconds INTEGER NOT NULL,
    focus_summary JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'processed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_SESSION_EVENTS = """
CREATE TABLE IF NOT EXISTS session_events (
    event_id VARCHAR(255) PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id),
    event_type VARCHAR(100) NOT NULL,
    source VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_REPORTS = """
CREATE TABLE IF NOT EXISTS reports (
    report_id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id),
    employee_id VARCHAR(255) NOT NULL,
    summary TEXT,
    productivity_assessment VARCHAR(50),
    key_activities JSONB DEFAULT '[]',
    focus_observations JSONB DEFAULT '[]',
    recommended_follow_up JSONB DEFAULT '[]',
    knowledge JSONB DEFAULT '{}',
    security JSONB DEFAULT '{}',
    errors JSONB DEFAULT '[]',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(session_id)
);
"""

CREATE_VECTOR_METADATA = """
CREATE TABLE IF NOT EXISTS vector_metadata (
    vector_id INTEGER PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL REFERENCES sessions(session_id),
    employee_id VARCHAR(255) NOT NULL,
    embedding_model VARCHAR(255) NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_employee_id ON sessions(employee_id);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_session_events_session_id ON session_events(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_session_events_timestamp ON session_events(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_reports_employee_id ON reports(employee_id);",
    "CREATE INDEX IF NOT EXISTS idx_vector_metadata_session_id ON vector_metadata(session_id);",
]

SCHEMA_STATEMENTS = [
    CREATE_EMPLOYEES,
    CREATE_SESSIONS,
    CREATE_SESSION_EVENTS,
    CREATE_REPORTS,
    CREATE_VECTOR_METADATA,
    *INDEXES,
]

EMPLOYEES_MIGRATIONS = [
    ("first_seen", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
    ("last_seen", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
]

SESSIONS_MIGRATIONS = [
    ("focus_summary", "JSONB NOT NULL DEFAULT '{}'"),
    ("metadata", "JSONB NOT NULL DEFAULT '{}'"),
    ("received_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
    ("processed_at", "TIMESTAMPTZ"),
    ("status", "VARCHAR(50) NOT NULL DEFAULT 'received' CHECK (status IN ('received', 'processed', 'failed'))"),
    ("updated_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
]


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = %s AND column_name = %s
        );
        """,
        (table, column),
    )
    return cursor.fetchone()[0]


def _add_missing_employee_columns(cursor) -> None:
    for column, definition in EMPLOYEES_MIGRATIONS:
        if not _column_exists(cursor, "employees", column):
            cursor.execute(
                f"ALTER TABLE employees ADD COLUMN {column} {definition};"
            )


def _add_missing_session_columns(cursor) -> None:
    for column, definition in SESSIONS_MIGRATIONS:
        if not _column_exists(cursor, "sessions", column):
            cursor.execute(
                f"ALTER TABLE sessions ADD COLUMN {column} {definition};"
            )


CREATE_SESSION_PROCESSING_STATUS = """
CREATE TABLE IF NOT EXISTS session_processing_status (
    session_id TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    documents_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_ANALYSIS_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS analysis_documents (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    doc_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_VECTOR_METADATA = """
CREATE TABLE IF NOT EXISTS vector_metadata (
    vector_id INTEGER PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES analysis_documents(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    employee_id TEXT NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    doc_type TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

PROCESSING_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_analysis_docs_session_id ON analysis_documents(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_docs_employee_id ON analysis_documents(employee_id);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_docs_doc_type ON analysis_documents(doc_type);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_docs_created_at ON analysis_documents(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_proc_status_status ON session_processing_status(status);",
    "CREATE INDEX IF NOT EXISTS idx_vector_meta_doc_id ON vector_metadata(document_id);",
    "CREATE INDEX IF NOT EXISTS idx_vector_meta_session_id ON vector_metadata(session_id);",
    "CREATE INDEX IF NOT EXISTS idx_vector_meta_employee_id ON vector_metadata(employee_id);",
    "CREATE INDEX IF NOT EXISTS idx_vector_meta_doc_type ON vector_metadata(doc_type);",
]

PROCESSING_SCHEMA_STATEMENTS = [
    CREATE_SESSION_PROCESSING_STATUS,
    CREATE_ANALYSIS_DOCUMENTS,
    CREATE_VECTOR_METADATA,
    *PROCESSING_INDEXES,
]


def ensure_processing_tables(connection) -> None:
    """Create session_processing_status, analysis_documents, and vector_metadata tables if not present."""
    with connection.cursor() as cursor:
        for statement in PROCESSING_SCHEMA_STATEMENTS:
            cursor.execute(statement)
    connection.commit()



def initialize_schema(connection) -> None:
    """Create all WorkGuard tables and migrate existing tables."""
    with connection.cursor() as cursor:
        for statement in SCHEMA_STATEMENTS:
            cursor.execute(statement)
        _add_missing_employee_columns(cursor)
        _add_missing_session_columns(cursor)
        for statement in PROCESSING_SCHEMA_STATEMENTS:
            cursor.execute(statement)
    connection.commit()

