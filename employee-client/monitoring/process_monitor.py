"""
process_monitor.py

Detects application_started / application_stopped events for user-facing
applications, using psutil.

Design decisions:
    - Exclusion approach: OS background processes are filtered out by
      StaticProcessFilter. Everything else is considered user activity.
    - Baseline on startup: applications already running when the agent
      starts are recorded as a baseline and do NOT generate an
      application_started event. Only applications that appear after the
      baseline was captured generate events.
    - Filter ordering: the parent-child check (free) runs before the
      StaticProcessFilter check so that browser sub-processes are
      discarded without any further work.
"""

import logging
import threading
import time

import psutil

from monitoring.common import make_event
from monitoring.process_filter import StaticProcessFilter

_log = logging.getLogger(__name__)


class ProcessMonitor(threading.Thread):
    """
    Polls running processes on an interval and emits application_started /
    application_stopped events onto the shared event queue for all
    non-background processes.
    """

    def __init__(self, config: dict, event_queue, poll_interval: float = 2.0):
        super().__init__(name="ProcessMonitor", daemon=True)
        self.event_queue = event_queue
        self.poll_interval = poll_interval

        # Accept an injected filter (for testing) or build the default one.
        self._program_filter: StaticProcessFilter = (
            config.get("program_filter") or StaticProcessFilter(config)
        )

        self._stop_event = threading.Event()
        # pid -> {"process_name": str, "executable": str}
        self._known_processes: dict[int, dict] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _snapshot_allowed_processes(self) -> dict[int, dict]:
        """
        Return {pid: info} for currently running non-background processes.

        Two filters are applied in order of cost (cheapest first):

          1. Parent-child deduplication (free string compare):
             Browser and Electron apps spawn many child processes with the
             same executable name as their parent. Only the root process of
             each such tree is kept so we do not generate spurious
             application_started / application_stopped events for every
             internal subprocess.

          2. StaticProcessFilter (O(1) set lookup + optional path check):
             Removes known Windows OS and background-service processes.
        """
        # Collect all running processes in one psutil pass.
        all_procs: dict[int, dict] = {}
        for proc in psutil.process_iter(attrs=["pid", "ppid", "name", "exe"]):
            try:
                info = proc.info
                all_procs[info["pid"]] = info
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        snapshot: dict[int, dict] = {}
        for pid, info in all_procs.items():
            name: str = info.get("name") or ""
            exe: str  = info.get("exe")  or ""

            # Filter 1: parent-child deduplication (free)
            parent_info = all_procs.get(info.get("ppid"))
            if parent_info:
                parent_name = (parent_info.get("name") or "").lower()
                if parent_name == name.lower():
                    # Internal subprocess of the same application - skip.
                    continue

            # Filter 2: background-process exclusion (O(1))
            if not self._program_filter.is_allowed(name, exe, pid=pid):
                continue

            snapshot[pid] = {"process_name": name, "executable": exe}

        return snapshot

    def _establish_baseline(self) -> None:
        """Record already-running apps without emitting events."""
        self._known_processes = self._snapshot_allowed_processes()
        _log.info(
            "[ProcessMonitor] Baseline captured: %d processes.",
            len(self._known_processes),
        )

    def _emit(self, event_type: str, pid: int, info: dict) -> None:
        event = make_event(
            event_type=event_type,
            source="psutil",
            data={
                "pid": pid,
                "process_name": info["process_name"],
                "executable":   info["executable"],
            },
        )
        self.event_queue.put(event)
        _log.debug(
            "[ProcessMonitor] %s  pid=%d  %s",
            event_type, pid, info["process_name"],
        )

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._establish_baseline()

        while not self._stop_event.is_set():
            t0 = time.monotonic()
            current = self._snapshot_allowed_processes()
            elapsed = time.monotonic() - t0

            # Warn if the snapshot itself is slow. Should never happen with
            # the static filter, but useful for catching regressions.
            if elapsed > self.poll_interval:
                _log.warning(
                    "[ProcessMonitor] Snapshot took %.2f s "
                    "(poll_interval=%.2f s) - consider increasing poll_interval.",
                    elapsed,
                    self.poll_interval,
                )

            # Newly appeared processes.
            for pid, info in current.items():
                if pid not in self._known_processes:
                    self._emit("application_started", pid, info)

            # Processes that disappeared since last poll.
            for pid, info in list(self._known_processes.items()):
                if pid not in current:
                    self._emit("application_stopped", pid, info)

            self._known_processes = current
            self._stop_event.wait(self.poll_interval)

    def stop(self) -> None:
        self._stop_event.set()