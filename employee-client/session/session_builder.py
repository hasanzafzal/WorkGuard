import json
import os
import queue
import threading
import uuid
from datetime import datetime, timezone


class SessionBuilder(threading.Thread):

    def __init__(
        self,
        config: dict,
        event_queue: "queue.Queue",
        sessions_dir: str = "sessions",
        on_session_created=None
    ):
        super().__init__(
            name="SessionBuilder",
            daemon=True
        )

        self.event_queue = event_queue
        self.employee_id = config.get("employee_id", "UNKNOWN")
        self.employee_name = config.get("employee_name", "UNKNOWN")
        self.timeout_seconds = config.get("session_timeout_minutes", 30) * 60
        self.sessions_dir = sessions_dir
        self.on_session_created = on_session_created

        os.makedirs(self.sessions_dir, exist_ok=True)
        self._stop_event = threading.Event()
        self._active_session = None
        self._lock = threading.Lock()

    def _start_session(self, event: dict):
        now = datetime.now(timezone.utc)
        self._active_session = {
            "session_id": f"sess_{uuid.uuid4().hex[:12]}",
            "start_time": now,
            "events": [event],
            "last_event_time": now,
        }

    def _extend_session(self, event: dict):
        self._active_session["events"].append(event)
        self._active_session["last_event_time"] = datetime.now(timezone.utc)

    def _compute_focus_summary(self, events: list, session_end: "datetime") -> dict:
        """Calculate application focus durations from pywin32 events."""
        totals = {}
        open_focus = {}  # pid -> {"process_name": str, "start": datetime}

        for event in events:
            if event.get("source") != "pywin32":
                continue

            data = event["data"]
            pid = data["pid"]
            name = data["process_name"]
            ts = datetime.fromisoformat(event["timestamp"])

            if event["event_type"] == "application_focused":
                open_focus[pid] = {"process_name": name, "start": ts}

            elif event["event_type"] == "application_unfocused":
                interval = open_focus.pop(pid, None)
                if interval is not None:
                    duration = (ts - interval["start"]).total_seconds()
                    totals[interval["process_name"]] = (
                        totals.get(interval["process_name"], 0) + duration
                    )

        # Close any focus intervals that never received an unfocused event
        for pid, interval in open_focus.items():
            duration = (session_end - interval["start"]).total_seconds()
            totals[interval["process_name"]] = (
                totals.get(interval["process_name"], 0) + duration
            )

        return {name: round(seconds, 1) for name, seconds in totals.items()}

    def _finalize_session(self):
        """Finalize and persist the active session."""
        if self._active_session is None:
            return None

        session = self._active_session
        start_time = session["start_time"]
        end_time = session["last_event_time"]
        duration_seconds = int((end_time - start_time).total_seconds())

        payload = {
            "session_id": session["session_id"],
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "session": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration_seconds,
            },
            "events": session["events"],
            "focus_summary": self._compute_focus_summary(session["events"], end_time),
            "metadata": {
                "schema_version": "1.0",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        path = os.path.join(self.sessions_dir, f"{session['session_id']}.json")

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except OSError as e:
            print(
                f"[SessionBuilder] ERROR: "
                f"Could not save session {session['session_id']}: {e}"
            )
            return None

        print(
            f"[SessionBuilder] Saved session {session['session_id']} "
            f"({len(session['events'])} events, {duration_seconds}s) -> {path}"
        )

        if self.on_session_created:
            try:
                self.on_session_created(path)
                print(
                    f"[SessionBuilder] "
                    f"Session queued for downstream processing: {session['session_id']}"
                )
            except Exception as e:
                print(
                    f"[SessionBuilder] WARNING: "
                    f"Session was saved successfully, but downstream callback failed: {e}"
                )

        self._active_session = None
        return path

    def run(self):
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
                        datetime.now(timezone.utc) - self._active_session["last_event_time"]
                    ).total_seconds()
                    if elapsed >= self.timeout_seconds:
                        self._finalize_session()

        # Finalize any remaining session on shutdown
        with self._lock:
            self._finalize_session()

    def stop(self):
        """Request graceful shutdown of the SessionBuilder thread."""
        self._stop_event.set()