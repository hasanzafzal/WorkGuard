"""
process_monitor.py

Detects application_started / application_stopped events for whitelisted
applications only, using psutil.

Design decisions (finalized):
    - Whitelist approach: only processes listed in
      config["monitored_applications"] are ever considered.
    - Baseline on startup: applications already running when the agent
      starts are recorded as a baseline and do NOT generate an
      application_started event. Only applications that appear after the
      baseline was captured generate events.
"""

import threading

import psutil

from monitoring.common import make_event


class ProcessMonitor(threading.Thread):
    """
    Polls running processes on an interval and emits application_started /
    application_stopped events onto the shared event queue for whitelisted
    applications only.
    """

    def __init__(self, config: dict, event_queue, poll_interval: float = 2.0):
        super().__init__(name="ProcessMonitor", daemon=True)
        self.event_queue = event_queue
        self.poll_interval = poll_interval

        whitelist = config.get("monitored_applications", [])
        # Lowercase for case-insensitive matching (important on Windows).
        self._whitelist = {name.lower() for name in whitelist}

        self._stop_event = threading.Event()
        # pid -> {"process_name": str, "executable": str}
        self._known_processes = {}

    def _snapshot_whitelisted_processes(self) -> dict:

    # Return {pid: info} for currently running whitelisted processes,
    # excluding internal child processes spawned by the same application
    # (e.g. Chrome/Edge/Firefox renderer, GPU, and utility subprocesses,
    # which share the same executable name as their parent). This keeps
    # genuine "app opened/closed" events without the noise of a
    # multi-process browser's internal subprocess churn.

        all_procs = {}
        for proc in psutil.process_iter(attrs=["pid", "ppid", "name", "exe"]):
            try:
                info = proc.info
                all_procs[info["pid"]] = info
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        snapshot = {}
        for pid, info in all_procs.items():
            name = info.get("name") or ""
            if name.lower() not in self._whitelist:
                continue

            parent_info = all_procs.get(info.get("ppid"))
            parent_name = (parent_info.get("name") or "") if parent_info else ""
            if parent_name.lower() == name.lower():
                # Child subprocess of the same application - skip it, it's
                # not a distinct "application opened" event.
                continue

            snapshot[pid] = {
                "process_name": name,
                "executable": info.get("exe") or "",
            }
        return snapshot

    def _establish_baseline(self):
        """Record already-running whitelisted apps without emitting events."""
        self._known_processes = self._snapshot_whitelisted_processes()

    def _emit(self, event_type: str, pid: int, info: dict):
        event = make_event(
            event_type=event_type,
            source="psutil",
            data={
                "pid": pid,
                "process_name": info["process_name"],
                "executable": info["executable"],
            },
        )
        self.event_queue.put(event)

    def run(self):
        self._establish_baseline()

        while not self._stop_event.is_set():
            current = self._snapshot_whitelisted_processes()

            # Newly appeared whitelisted processes.
            for pid, info in current.items():
                if pid not in self._known_processes:
                    self._emit("application_started", pid, info)

            # Whitelisted processes that disappeared since last poll.
            for pid, info in list(self._known_processes.items()):
                if pid not in current:
                    self._emit("application_stopped", pid, info)

            self._known_processes = current
            self._stop_event.wait(self.poll_interval)

    def stop(self):
        self._stop_event.set()
