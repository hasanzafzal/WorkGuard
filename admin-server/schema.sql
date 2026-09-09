-- =============================================================================
-- WorkGuard PostgreSQL Schema
-- Stores structured data extracted from session.json files.
--
-- Table hierarchy (dependency order):
--   employees
--   └── sessions
--       ├── session_activity_summary
--       ├── application_focus
--       ├── process_events
--       ├── directory_activity
--       └── focus_timeline
--   application_catalog  (referenced by views, populated during ingestion)
--
-- Views built on top for AI agents:
--   v_employee_app_usage        cross-session app preference per employee
--   v_employee_project_activity cross-session directory/project activity
--   mv_daily_employee_stats     materialized daily rollup (refresh on schedule)
-- =============================================================================


-- =============================================================================
-- EMPLOYEES
-- One row per monitored machine/user identity.
-- Populated on first session ingestion; updated on subsequent ones.
--
-- Source fields:
--   employee_id   → session_json.employee_id         "SYS-B56B4DEB06F6"
--   employee_name → session_json.employee_name        "AILAB_7881_W2 (arif.arshad)"
--   machine_name  → parsed: everything before " ("    "AILAB_7881_W2"
--   username      → parsed: between "(" and ")"       "arif.arshad"
-- =============================================================================
CREATE TABLE employees (
    employee_id     TEXT        PRIMARY KEY,
    employee_name   TEXT        NOT NULL,
    machine_name    TEXT,
    username        TEXT,
    first_seen_at   TIMESTAMPTZ,
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  employees              IS 'One row per monitored employee PC. Upserted on each session ingestion.';
COMMENT ON COLUMN employees.machine_name IS 'Hostname parsed from employee_name, e.g. AILAB_7881_W2';
COMMENT ON COLUMN employees.username     IS 'Windows username parsed from employee_name, e.g. arif.arshad';


-- =============================================================================
-- APPLICATION CATALOG
-- Registry of every process name ever seen, enriched with human-readable
-- metadata so agents can answer semantic questions ("what productivity tools
-- does this employee use?") without parsing exe names.
--
-- Populated automatically on ingestion (INSERT ... ON CONFLICT DO NOTHING).
-- category and is_productive are updated by admin / agent enrichment pass.
-- =============================================================================
CREATE TABLE application_catalog (
    id              SERIAL      PRIMARY KEY,
    process_name    TEXT        UNIQUE NOT NULL,
    display_name    TEXT,
    category        TEXT        CHECK (category IN (
                                    'development',
                                    'browser',
                                    'communication',
                                    'office',
                                    'media',
                                    'system',
                                    'ai_assistant',
                                    'other'
                                )),
    is_productive   BOOLEAN     DEFAULT TRUE,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes           TEXT
);

COMMENT ON TABLE  application_catalog              IS 'Registry of all process names seen. category/is_productive enriched post-ingestion.';
COMMENT ON COLUMN application_catalog.process_name IS 'Exact process name as reported by psutil, e.g. Code - Insiders.exe';
COMMENT ON COLUMN application_catalog.is_productive IS 'Used to compute productive_seconds in session_activity_summary.';

-- Seed common apps so the catalog is useful from the first session.
INSERT INTO application_catalog (process_name, display_name, category, is_productive) VALUES
    ('Code - Insiders.exe',  'VS Code Insiders',     'development',   TRUE),
    ('Code.exe',             'VS Code',              'development',   TRUE),
    ('python.exe',           'Python',               'development',   TRUE),
    ('pwsh.exe',             'PowerShell',           'development',   TRUE),
    ('cmd.exe',              'Command Prompt',       'development',   TRUE),
    ('WindowsTerminal.exe',  'Windows Terminal',     'development',   TRUE),
    ('chrome.exe',           'Google Chrome',        'browser',       TRUE),
    ('msedge.exe',           'Microsoft Edge',       'browser',       TRUE),
    ('firefox.exe',          'Firefox',              'browser',       TRUE),
    ('WINWORD.EXE',          'Microsoft Word',       'office',        TRUE),
    ('EXCEL.EXE',            'Microsoft Excel',      'office',        TRUE),
    ('POWERPNT.EXE',         'Microsoft PowerPoint', 'office',        TRUE),
    ('OUTLOOK.EXE',          'Microsoft Outlook',    'communication', TRUE),
    ('explorer.exe',         'File Explorer',        'system',        FALSE),
    ('Notepad.exe',          'Notepad',              'office',        TRUE),
    ('mspaint.exe',          'Paint',                'media',         FALSE),
    ('CalculatorApp.exe',    'Calculator',           'other',         FALSE),
    ('photolaunch.exe',      'Photo Viewer',         'media',         FALSE),
    ('Desktop',              'Desktop / Idle',       'system',        FALSE),
    ('M365Copilot.exe',      'Microsoft 365 Copilot','ai_assistant',  TRUE)
ON CONFLICT (process_name) DO NOTHING;


-- =============================================================================
-- SESSIONS
-- One row per session.json file received from a monitored PC.
--
-- Source fields:
--   session_id        → session_json.session_id
--   employee_id       → session_json.employee_id
--   start_time        → session_json.session.start_time
--   end_time          → session_json.session.end_time
--   duration_seconds  → session_json.session.duration_seconds
--   schema_version    → session_json.metadata.schema_version
-- =============================================================================
CREATE TABLE sessions (
    session_id          TEXT        PRIMARY KEY,
    employee_id         TEXT        NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    start_time          TIMESTAMPTZ NOT NULL,
    end_time            TIMESTAMPTZ NOT NULL,
    duration_seconds    INTEGER     NOT NULL CHECK (duration_seconds >= 0),
    schema_version      TEXT,
    session_file_path   TEXT,                       -- path to original .json for re-processing
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  sessions                   IS 'One row per session.json. Central FK anchor for all session data.';
COMMENT ON COLUMN sessions.session_file_path IS 'Absolute path to the source JSON on the admin server for re-ingestion if schema changes.';


-- =============================================================================
-- SESSION ACTIVITY SUMMARY
-- Flattened from session_json.activity_summary.
-- One row per session. Gives agents a single-row answer to
-- "what happened in this session?" without joining multiple tables.
--
-- Source fields:
--   applications_used       → activity_summary.applications_used
--   processes_started       → activity_summary.process_activity.started
--   processes_stopped       → activity_summary.process_activity.stopped
--   processes_used          → activity_summary.process_activity.processes
--   directories_affected    → activity_summary.file_activity.directories_affected
--   total_file_operations   → activity_summary.file_activity.total_operations
--   file_extensions         → activity_summary.file_activity.extensions
--   desktop_seconds         → activity_summary.application_focus_seconds["Desktop"]
--   productive_seconds      → computed: SUM focus seconds WHERE is_productive = TRUE
--   active_seconds          → duration_seconds - desktop_seconds
-- =============================================================================
CREATE TABLE session_activity_summary (
    session_id              TEXT    PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,

    -- Application usage
    applications_used       TEXT[],                         -- ["Code - Insiders.exe", ...]
    desktop_seconds         INTEGER     NOT NULL DEFAULT 0, -- idle / no focused window

    -- Process lifecycle
    processes_started       INTEGER     NOT NULL DEFAULT 0,
    processes_stopped       INTEGER     NOT NULL DEFAULT 0,
    processes_used          TEXT[],                         -- distinct names started this session

    -- File activity (from directory_activity events)
    directories_affected    INTEGER     NOT NULL DEFAULT 0,
    total_file_operations   INTEGER     NOT NULL DEFAULT 0,
    file_extensions         JSONB,                          -- {".py": 27, ".jpeg": 1483}

    -- Derived scores (computed at ingestion, can be recomputed)
    productive_seconds      INTEGER,    -- focus on is_productive = TRUE apps
    active_seconds          INTEGER     -- duration_seconds - desktop_seconds
);

COMMENT ON TABLE  session_activity_summary                  IS 'Flattened activity_summary block. Quick read for agents.';
COMMENT ON COLUMN session_activity_summary.desktop_seconds  IS 'Seconds the Desktop placeholder had focus — represents idle or away time.';
COMMENT ON COLUMN session_activity_summary.productive_seconds IS 'SUM of focus_seconds WHERE application_catalog.is_productive = TRUE.';
COMMENT ON COLUMN session_activity_summary.file_extensions  IS 'JSONB map of extension → operation count across all directory_activity events.';


-- =============================================================================
-- APPLICATION FOCUS
-- One row per application per session (from session_json.focus_summary).
-- This is the primary table for "what did the employee use and for how long?"
--
-- Source: focus_summary flat dict, e.g. {"Code - Insiders.exe": 378.0, ...}
-- =============================================================================
CREATE TABLE application_focus (
    id              BIGSERIAL   PRIMARY KEY,
    session_id      TEXT        NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    process_name    TEXT        NOT NULL,
    focus_seconds   NUMERIC(10,1) NOT NULL CHECK (focus_seconds >= 0),
    focus_pct       NUMERIC(5,2),   -- focus_seconds / session duration_seconds * 100

    UNIQUE (session_id, process_name)
);

COMMENT ON TABLE  application_focus           IS 'Per-app focus duration per session. Source: focus_summary block.';
COMMENT ON COLUMN application_focus.focus_pct IS 'Percentage of session duration this app was in the foreground.';


-- =============================================================================
-- PROCESS EVENTS
-- One row per application_started / application_stopped event.
-- Captures which tools the employee actively launched during the session.
-- Background/system processes are already filtered by StaticProcessFilter
-- before reaching the session JSON.
--
-- Source: session_json.events WHERE source = "psutil"
-- =============================================================================
CREATE TABLE process_events (
    id              BIGSERIAL   PRIMARY KEY,
    event_id        TEXT        UNIQUE NOT NULL,
    session_id      TEXT        NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    event_type      TEXT        NOT NULL CHECK (event_type IN ('application_started', 'application_stopped')),
    process_name    TEXT        NOT NULL,
    pid             INTEGER,
    executable      TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL
);

COMMENT ON TABLE  process_events            IS 'Process lifecycle events. Source: psutil events in session.json.';
COMMENT ON COLUMN process_events.executable IS 'Full executable path — useful for distinguishing python.exe from different venvs.';


-- =============================================================================
-- DIRECTORY ACTIVITY
-- One row per directory_activity event in the session.
-- Each row represents a burst of file operations in one directory.
-- These events are emitted by file_monitor._DirectoryAccumulator after
-- a directory goes quiet for FLUSH_INTERVAL seconds.
--
-- Source: session_json.events WHERE event_type = "directory_activity"
-- =============================================================================
CREATE TABLE directory_activity (
    id                  BIGSERIAL   PRIMARY KEY,
    event_id            TEXT        UNIQUE NOT NULL,
    session_id          TEXT        NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,

    directory_path      TEXT        NOT NULL,
    total_operations    INTEGER     NOT NULL DEFAULT 0,

    -- Operation breakdown
    ops_created         INTEGER     NOT NULL DEFAULT 0,
    ops_modified        INTEGER     NOT NULL DEFAULT 0,
    ops_deleted         INTEGER     NOT NULL DEFAULT 0,
    ops_moved           INTEGER     NOT NULL DEFAULT 0,

    unique_file_count   INTEGER     NOT NULL DEFAULT 0,
    file_extensions     JSONB,              -- {".jpeg": 1004}

    -- When did this burst of activity happen?
    period_start        TIMESTAMPTZ,
    period_end          TIMESTAMPTZ,

    -- Computed: seconds of file activity in this directory
    period_seconds      INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (period_end - period_start))::INTEGER
    ) STORED
);

COMMENT ON TABLE  directory_activity               IS 'Aggregated file activity per directory per session. Source: directory_activity watchdog events.';
COMMENT ON COLUMN directory_activity.period_seconds IS 'Duration of the file activity burst in seconds. Computed from period_start / period_end.';


-- =============================================================================
-- FOCUS TIMELINE
-- One row per application_focused / application_unfocused event.
-- Allows agents to reconstruct the exact attention timeline of a session
-- ("at 11:14:08 the employee switched from Edge to Notepad").
-- Highest volume table — consider partitioning monthly as data grows.
--
-- Source: session_json.events WHERE source = "pywin32"
-- =============================================================================
CREATE TABLE focus_timeline (
    id              BIGSERIAL   PRIMARY KEY,
    event_id        TEXT        UNIQUE NOT NULL,
    session_id      TEXT        NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    event_type      TEXT        NOT NULL CHECK (event_type IN ('application_focused', 'application_unfocused')),
    process_name    TEXT        NOT NULL,
    pid             INTEGER,
    occurred_at     TIMESTAMPTZ NOT NULL
);

COMMENT ON TABLE focus_timeline IS 'Raw focus/unfocus event log. Enables full attention timeline reconstruction. Highest-volume table.';


-- =============================================================================
-- INDEXES
-- =============================================================================

-- sessions — most queries filter by employee and/or time range
CREATE INDEX idx_sessions_employee_id       ON sessions (employee_id);
CREATE INDEX idx_sessions_start_time        ON sessions (start_time DESC);
CREATE INDEX idx_sessions_employee_time     ON sessions (employee_id, start_time DESC);

-- application_focus — agent queries group by app, filter by session
CREATE INDEX idx_app_focus_session          ON application_focus (session_id);
CREATE INDEX idx_app_focus_process          ON application_focus (process_name);
CREATE INDEX idx_app_focus_process_seconds  ON application_focus (process_name, focus_seconds DESC);

-- process_events
CREATE INDEX idx_process_events_session     ON process_events (session_id);
CREATE INDEX idx_process_events_process     ON process_events (process_name);
CREATE INDEX idx_process_events_occurred    ON process_events (occurred_at DESC);

-- directory_activity — agents often filter by directory pattern
CREATE INDEX idx_dir_activity_session       ON directory_activity (session_id);
CREATE INDEX idx_dir_activity_path          ON directory_activity (directory_path text_pattern_ops);
CREATE INDEX idx_dir_activity_period        ON directory_activity (period_start DESC);

-- focus_timeline — timeline reconstruction by session, chronological
CREATE INDEX idx_focus_timeline_session     ON focus_timeline (session_id, occurred_at ASC);
CREATE INDEX idx_focus_timeline_occurred    ON focus_timeline (occurred_at DESC);

-- session_activity_summary — GIN index for array and JSONB lookups
CREATE INDEX idx_summary_apps_used          ON session_activity_summary USING GIN (applications_used);
CREATE INDEX idx_summary_extensions         ON session_activity_summary USING GIN (file_extensions);
CREATE INDEX idx_dir_activity_extensions    ON directory_activity       USING GIN (file_extensions);


-- =============================================================================
-- VIEW: v_employee_app_usage
-- Cross-session application usage rolled up per employee.
-- Answers: "What apps does employee X use, and for how long total?"
-- Joined with application_catalog for semantic enrichment.
-- =============================================================================
CREATE VIEW v_employee_app_usage AS
SELECT
    s.employee_id,
    af.process_name,
    ac.display_name,
    ac.category,
    ac.is_productive,
    COUNT(DISTINCT s.session_id)        AS sessions_used_in,
    SUM(af.focus_seconds)               AS total_focus_seconds,
    ROUND(AVG(af.focus_pct), 1)         AS avg_focus_pct,
    MAX(s.start_time)                   AS last_used_at
FROM application_focus af
JOIN sessions s ON s.session_id = af.session_id
LEFT JOIN application_catalog ac ON ac.process_name = af.process_name
WHERE af.process_name != 'Desktop'
GROUP BY
    s.employee_id, af.process_name,
    ac.display_name, ac.category, ac.is_productive;

COMMENT ON VIEW v_employee_app_usage IS 'Cross-session app usage per employee. Join with employees for full context.';


-- =============================================================================
-- VIEW: v_employee_project_activity
-- Cross-session directory (project) activity per employee.
-- Answers: "What projects/folders does employee X work in most?"
-- =============================================================================
CREATE VIEW v_employee_project_activity AS
SELECT
    s.employee_id,
    da.directory_path,
    COUNT(DISTINCT s.session_id)        AS sessions_active_in,
    SUM(da.total_operations)            AS total_file_operations,
    SUM(da.unique_file_count)           AS total_unique_files,
    SUM(da.ops_created)                 AS total_created,
    SUM(da.ops_modified)                AS total_modified,
    SUM(da.ops_deleted)                 AS total_deleted,
    MIN(da.period_start)                AS first_activity_at,
    MAX(da.period_end)                  AS last_activity_at
FROM directory_activity da
JOIN sessions s ON s.session_id = da.session_id
GROUP BY s.employee_id, da.directory_path;

COMMENT ON VIEW v_employee_project_activity IS 'Cross-session file activity by directory per employee. Use directory_path patterns to identify projects.';


-- =============================================================================
-- MATERIALIZED VIEW: mv_daily_employee_stats
-- Pre-aggregated daily rollup per employee.
-- Refreshed on a schedule (e.g. nightly or after every batch ingestion).
-- Answers: "How productive was employee X on a given day?" in one row.
--
-- Refresh: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_employee_stats;
-- =============================================================================
CREATE MATERIALIZED VIEW mv_daily_employee_stats AS
WITH top_apps AS (
    -- Identify the single most-used app per employee per day, excluding Desktop
    SELECT
        s.employee_id,
        s.start_time::DATE          AS work_date,
        af.process_name,
        SUM(af.focus_seconds)       AS day_focus_seconds,
        ROW_NUMBER() OVER (
            PARTITION BY s.employee_id, s.start_time::DATE
            ORDER BY SUM(af.focus_seconds) DESC
        ) AS rn
    FROM application_focus af
    JOIN sessions s ON s.session_id = af.session_id
    WHERE af.process_name != 'Desktop'
    GROUP BY s.employee_id, s.start_time::DATE, af.process_name
)
SELECT
    s.employee_id,
    s.start_time::DATE                          AS work_date,
    COUNT(DISTINCT s.session_id)                AS total_sessions,
    SUM(s.duration_seconds)                     AS total_duration_seconds,
    COALESCE(SUM(sas.productive_seconds), 0)    AS total_productive_seconds,
    COALESCE(SUM(sas.desktop_seconds), 0)       AS total_idle_seconds,
    COALESCE(SUM(sas.total_file_operations), 0) AS total_file_operations,
    COALESCE(SUM(sas.directories_affected), 0)  AS directories_affected,
    COALESCE(SUM(sas.processes_started), 0)     AS processes_started,
    ta.process_name                             AS top_application
FROM sessions s
LEFT JOIN session_activity_summary sas  ON sas.session_id = s.session_id
LEFT JOIN top_apps ta
    ON  ta.employee_id = s.employee_id
    AND ta.work_date   = s.start_time::DATE
    AND ta.rn          = 1
GROUP BY s.employee_id, s.start_time::DATE, ta.process_name
ORDER BY s.employee_id, work_date DESC;

CREATE UNIQUE INDEX idx_mv_daily_stats_pk
    ON mv_daily_employee_stats (employee_id, work_date);

COMMENT ON MATERIALIZED VIEW mv_daily_employee_stats
    IS 'Daily rollup per employee. Refresh after batch ingestion: REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_employee_stats;';
