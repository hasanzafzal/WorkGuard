import json
import logging
import os
import queue
import threading
import uuid
from datetime import datetime, timezone

from system_identity import resolve_employee_identity

_log = logging.getLogger(__name__)


class SessionBuilder(threading.Thread):

    def __init__(
        self,
        config: dict,
        event_queue: "queue.Queue",
        sessions_dir: str = "sessions",
        on_session_created=None,
    ):
        super().__init__(name="SessionBuilder", daemon=True)

        self.event_queue = event_queue
        self.employee_id, self.employee_name = resolve_employee_identity(config)
        self.timeout_seconds = config.get("session_timeout_minutes", 30) * 60
        self.sessions_dir = sessions_dir
        self.on_session_created = on_session_created

        os.makedirs(self.sessions_dir, exist_ok=True)
        self._stop_event = threading.Event()
        self._active_session = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def _start_session(self, event: dict) -> None:
        now = datetime.now(timezone.utc)
        self._active_session = {
            "session_id": f"sess_{uuid.uuid4().hex[:12]}",
            "start_time": now,
            "events": [event],
            "last_event_time": now,
        }

    def _extend_session(self, event: dict) -> None:
        self._active_session["events"].append(event)
        self._active_session["last_event_time"] = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Derived summaries
    # ------------------------------------------------------------------

    def _compute_focus_summary(self, events: list, session_end: datetime) -> dict:
        """
        Calculate application focus durations (seconds) from pywin32 events.
        Open intervals at session end are closed against session_end.
        """
        totals: dict[str, float] = {}
        open_focus: dict[int, dict] = {}  # pid -> {process_name, start}

        for event in events:
            if event.get("source") != "pywin32":
                continue

            data = event["data"]
            pid  = data["pid"]
            name = data["process_name"]
            ts   = datetime.fromisoformat(event["timestamp"])

            if event["event_type"] == "application_focused":
                open_focus[pid] = {"process_name": name, "start": ts}

            elif event["event_type"] == "application_unfocused":
                interval = open_focus.pop(pid, None)
                if interval is not None:
                    duration = (ts - interval["start"]).total_seconds()
                    totals[interval["process_name"]] = (
                        totals.get(interval["process_name"], 0) + duration
                    )

        for pid, interval in open_focus.items():
            duration = (session_end - interval["start"]).total_seconds()
            totals[interval["process_name"]] = (
                totals.get(interval["process_name"], 0) + duration
            )

        return {name: round(secs, 1) for name, secs in totals.items()}

    def _compute_activity_summary(
        self, events: list, focus_summary: dict
    ) -> dict:
        """
        Build a structured high-level summary for fast agent consumption.

        Agents can answer "what did this employee do?" from this block
        alone without scanning every raw event.

        Structure
        ---------
        applications_used          Unique apps with measurable focus,
                                   sorted most-active first.
        application_focus_seconds  Seconds in each app (int, most-active first).
        process_activity           How many unique processes started/stopped
                                   and which ones (by name).
        file_activity              Aggregated from directory_activity events:
                                   directories touched, total file ops, and
                                   a per-extension operation count.
        """

        # ── applications_used ─────────────────────────────────────────────
        # Sort focus_summary by seconds descending so the most-active app
        # is first. Keep "Desktop" (idle) only when it is material (≥ 10s).
        applications_used: list[str] = [
            app
            for app, secs in sorted(
                focus_summary.items(), key=lambda x: x[1], reverse=True
            )
            if app != "Desktop" or secs >= 10
        ]

        # ── application_focus_seconds ─────────────────────────────────────
        # Integer-rounded mirror of focus_summary, most-active first.
        application_focus_seconds: dict[str, int] = {
            app: int(round(secs))
            for app, secs in sorted(
                focus_summary.items(), key=lambda x: x[1], reverse=True
            )
        }

        # ── process_activity ──────────────────────────────────────────────
        started_names: set[str] = set()
        stopped_count: int = 0

        for event in events:
            if event.get("source") != "psutil":
                continue
            if event["event_type"] == "application_started":
                started_names.add(event["data"]["process_name"])
            elif event["event_type"] == "application_stopped":
                stopped_count += 1

        process_activity: dict = {
            "started":   len(started_names),
            "stopped":   stopped_count,
            "processes": sorted(started_names),   # alphabetical for readability
        }

        # ── file_activity ─────────────────────────────────────────────────
        # Aggregate across all directory_activity events emitted by
        # file_monitor.py's _DirectoryAccumulator.
        directories: set[str]       = set()
        total_ops:   int            = 0
        extensions:  dict[str, int] = {}

        for event in events:
            if event.get("event_type") != "directory_activity":
                continue
            data = event["data"]
            directories.add(data.get("directory", ""))
            total_ops += data.get("total_operations", 0)
            for ext, count in data.get("file_types", {}).items():
                extensions[ext] = extensions.get(ext, 0) + count

        # Sort extensions by count descending so the dominant type is first.
        sorted_extensions = dict(
            sorted(extensions.items(), key=lambda x: x[1], reverse=True)
        )

        file_activity: dict = {
            "directories_affected": len(directories),
            "total_operations":     total_ops,
            "extensions":           sorted_extensions,
        }

        return {
            "applications_used":          applications_used,
            "application_focus_seconds":  application_focus_seconds,
            "process_activity":           process_activity,
            "file_activity":              file_activity,
        }

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _finalize_session(self) -> str | None:
        """Finalize and persist the active session to disk."""
        if self._active_session is None:
            return None

        session          = self._active_session
        start_time       = session["start_time"]
        end_time         = session["last_event_time"]
        duration_seconds = int((end_time - start_time).total_seconds())

        focus_summary    = self._compute_focus_summary(session["events"], end_time)
        activity_summary = self._compute_activity_summary(session["events"], focus_summary)

        payload = {
            "session_id":    session["session_id"],
            "employee_id":   self.employee_id,
            "employee_name": self.employee_name,
            "session": {
                "start_time":       start_time.isoformat(),
                "end_time":         end_time.isoformat(),
                "duration_seconds": duration_seconds,
            },

            # ── Quick-read block for agents ───────────────────────────────
            # Agents should read this first. Raw events below provide the
            # full timeline for deeper analysis when needed.
            "activity_summary": activity_summary,

            # ── Full event log ────────────────────────────────────────────
            "events": session["events"],

            # ── Pre-computed focus totals (float precision) ───────────────
            # "focus_summary": focus_summary,

            # ── Schema and field documentation ────────────────────────────
            "metadata": {
                "schema_version": "1.1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "event_type_guide": {
                    "application_focused":   (
                        "User switched foreground focus to this application."
                    ),
                    "application_unfocused": (
                        "User switched away from this application."
                    ),
                    "application_started":   (
                        "A process was launched during this session."
                    ),
                    "application_stopped":   (
                        "A process exited during this session."
                    ),
                    "directory_activity":    (
                        "Aggregated file-system operations within one directory. "
                        "'period_start' and 'period_end' bound when the activity "
                        "occurred. 'unique_file_count' is distinct files touched. "
                        "'operations' breaks down creates/modifies/deletes/moves. "
                        "'file_types' maps extension to operation count."
                    ),
                },
            },
        }

        path = os.path.join(self.sessions_dir, f"{session['session_id']}.json")

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError as e:
            _log.error(
                "[SessionBuilder] Could not save session %s: %s",
                session["session_id"], e,
            )
            return None

        _log.info(
            "[SessionBuilder] Saved session %s  (%d events, %ds)  ->  %s",
            session["session_id"], len(session["events"]), duration_seconds, path,
        )

        if self.on_session_created:
            try:
                self.on_session_created(path)
                _log.info(
                    "[SessionBuilder] Session queued for downstream: %s",
                    session["session_id"],
                )
            except Exception as e:
                _log.warning(
                    "[SessionBuilder] Session saved but downstream callback failed: %s", e,
                )

        self._active_session = None
        return path

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Process events until shutdown signal and queue is drained."""
        while True:
            if self._stop_event.is_set() and self.event_queue.empty():
                break

            try:
                event = self.event_queue.get(timeout=1.0)
            except queue.Empty:
                event = None

            with self._lock:
                if event is not None:
                    if self._active_session is None:
                        self._start_session(event)
                    else:
                        self._extend_session(event)
                elif self._active_session is not None:
                    elapsed = (
                        datetime.now(timezone.utc)
                        - self._active_session["last_event_time"]
                    ).total_seconds()
                    if elapsed >= self.timeout_seconds:
                        self._finalize_session()

        # Finalize any remaining session on shutdown.
        with self._lock:
            self._finalize_session()

    def stop(self) -> None:
        """Request graceful shutdown of the SessionBuilder thread."""
        self._stop_event.set()