"""
file_monitor.py

Watches configured project directories using watchdog and emits events
onto the shared event queue.

Event model (LLM-insight focused)
----------------------------------
Individual file paths are NOT logged. Instead, file activity is
accumulated per directory and flushed as a single ``directory_activity``
summary event once the directory has been quiet for FLUSH_INTERVAL seconds.

This collapses "a Python script modified 5,000 JPEG files" from 5,000
identical-looking events into ONE meaningful event:

    {
      "event_type": "directory_activity",
      "source": "watchdog",
      "data": {
        "directory": "C:\\...\\MicroAI\\test_ugly\\colon_aca",
        "operations": {"modified": 1004},
        "file_types": {".jpeg": 1004},
        "unique_file_count": 1004,
        "period_start": "2026-09-01T04:57:00+00:00",
        "period_end":   "2026-09-01T05:04:41+00:00"
      }
    }

Exclusion layers (applied before accumulation)
----------------------------------------------
1. Path-prefix   — Windows system dirs, Program Files, ProgramData.
2. Dir-component — AppData, $RECYCLE.BIN, .git, __pycache__, etc.
3. Extension     — .tmp, .lock, .log, .pyc, etc.
4. Office temp   — basename starts with ~$.

Recommended monitored_directories
----------------------------------
    C:\\Users\\<name>\\Desktop
    C:\\Users\\<name>\\Documents
    C:\\Users\\<name>\\Downloads
    D:\\               (if D: is a work drive)

Avoid C:\\ or C:\\Users\\<name> at root — AppData alone produces
thousands of background changes per hour.
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from monitoring.common import make_event

_log = logging.getLogger(__name__)

# How long a directory must be quiet (seconds) before its accumulated
# activity is flushed as a summary event.
FLUSH_INTERVAL: float = 5.0

# ---------------------------------------------------------------------------
# Exclusion helpers
# ---------------------------------------------------------------------------

_EXCLUDED_PATH_PREFIXES: tuple[str, ...] = (
    r"c:\windows",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\programdata",
    r"c:\users\default",
)

_EXCLUDED_DIR_PARTS: frozenset[str] = frozenset({
    "$recycle.bin",
    "system volume information",
    "appdata",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".tox",
    ".venv", "venv", ".env",
    "dist", "build",
    ".git", ".svn", ".hg",
    "node_modules",
    ".idea", ".vscode",
})

_EXCLUDED_EXTENSIONS: frozenset[str] = frozenset({
    ".tmp", ".temp", ".part", ".crdownload", ".partial",
    ".lock", ".lck",
    ".log",
    ".pyc", ".pyo", ".pyd",
    ".swp", ".swo", ".bak",
    ".db-journal", ".db-wal", ".db-shm",
})


def _should_ignore(path: str) -> bool:
    if os.path.basename(path).startswith("~$"):
        return True
    path_lower = path.lower()
    if any(path_lower.startswith(p) for p in _EXCLUDED_PATH_PREFIXES):
        return True
    if os.path.splitext(path)[1].lower() in _EXCLUDED_EXTENSIONS:
        return True
    parts = set(path_lower.replace("\\", "/").split("/"))
    if parts & _EXCLUDED_DIR_PARTS:
        return True
    return False


# ---------------------------------------------------------------------------
# Directory activity accumulator
# ---------------------------------------------------------------------------

class _DirectoryAccumulator:
    """
    Accumulates file-system events per directory and flushes them as
    compact ``directory_activity`` summary events.

    Thread-safe: all mutations are protected by a single lock.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # dir_path (lower) -> activity dict
        self._windows: dict[str, dict] = {}

    # ------------------------------------------------------------------

    def record(self, event_type: str, path: str) -> None:
        """Add one file event to the accumulator."""
        dir_path = os.path.dirname(path)
        ext = os.path.splitext(path)[1].lower() or "(none)"
        now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        now_mono = time.monotonic()

        op = event_type.replace("file_", "")   # "created", "modified", etc.

        with self._lock:
            if dir_path not in self._windows:
                self._windows[dir_path] = {
                    "operations": {},
                    "file_types": {},
                    "unique_files": set(),
                    "period_start": now_iso,
                    "last_activity_mono": now_mono,
                    "last_activity_iso": now_iso,
                }
            w = self._windows[dir_path]
            w["operations"][op] = w["operations"].get(op, 0) + 1
            w["file_types"][ext] = w["file_types"].get(ext, 0) + 1
            w["unique_files"].add(os.path.basename(path))
            w["last_activity_mono"] = now_mono
            w["last_activity_iso"] = now_iso

    def flush_stale(self, event_queue) -> int:
        """
        Emit summary events for directories quiet for >= FLUSH_INTERVAL.
        Returns the number of summaries emitted.
        """
        now = time.monotonic()
        stale: list[str] = []
        with self._lock:
            for dir_path, w in self._windows.items():
                if now - w["last_activity_mono"] >= FLUSH_INTERVAL:
                    stale.append(dir_path)
            for dir_path in stale:
                w = self._windows.pop(dir_path)
                self._emit(event_queue, dir_path, w)
        return len(stale)

    def flush_all(self, event_queue) -> int:
        """Emit summary events for all remaining directories (on shutdown)."""
        with self._lock:
            dirs = list(self._windows.items())
            self._windows.clear()
        for dir_path, w in dirs:
            self._emit(event_queue, dir_path, w)
        return len(dirs)

    # ------------------------------------------------------------------

    @staticmethod
    def _emit(event_queue, dir_path: str, w: dict) -> None:
        total = sum(w["operations"].values())
        if total == 0:
            return
        event = make_event(
            event_type="directory_activity",
            source="watchdog",
            data={
                "directory":         dir_path,
                "total_operations":  total,
                "operations":        {k: v for k, v in w["operations"].items() if v > 0},
                "file_types":        w["file_types"],
                "unique_file_count": len(w["unique_files"]),
                "period_start":      w["period_start"],
                "period_end":        w["last_activity_iso"],
            },
        )
        event_queue.put(event)
        _log.debug(
            "[FileMonitor] directory_activity  %s  (%d ops)",
            dir_path, total,
        )


# ---------------------------------------------------------------------------
# Watchdog event handler
# ---------------------------------------------------------------------------

class _Handler(FileSystemEventHandler):
    """Routes watchdog callbacks into the directory accumulator."""

    def __init__(self, accumulator: _DirectoryAccumulator):
        super().__init__()
        self._acc = accumulator

    def _record(self, event_type: str, path: str) -> None:
        if _should_ignore(path):
            return
        self._acc.record(event_type, path)

    def on_created(self, event) -> None:
        if not event.is_directory:
            self._record("file_created", event.src_path)

    def on_modified(self, event) -> None:
        if not event.is_directory:
            self._record("file_modified", event.src_path)

    def on_deleted(self, event) -> None:
        if not event.is_directory:
            self._record("file_deleted", event.src_path)

    def on_moved(self, event) -> None:
        if not event.is_directory:
            # Record at destination; source is noted implicitly via the
            # lower file_created count vs. actual unique files touched.
            self._record("file_moved", event.dest_path)


# ---------------------------------------------------------------------------
# Monitor thread
# ---------------------------------------------------------------------------

class FileMonitor(threading.Thread):
    """
    Wraps a watchdog Observer to recursively monitor configured directories
    and push ``directory_activity`` summary events onto the shared queue.
    """

    def __init__(self, config: dict, event_queue, flush_interval: float = FLUSH_INTERVAL):
        super().__init__(name="FileMonitor", daemon=True)
        self.event_queue = event_queue
        self._flush_interval = flush_interval
        self._configured_directories = config.get("monitored_directories", [])
        base_dir = config.get("_base_dir", os.getcwd())

        self._directories: list[str] = []
        for directory in self._configured_directories:
            resolved = (
                directory
                if os.path.isabs(directory)
                else os.path.join(base_dir, directory)
            )
            if os.path.isdir(resolved):
                self._directories.append(resolved)
            else:
                _log.warning(
                    "[FileMonitor] Directory does not exist, skipping: %s", resolved,
                )

        self._accumulator = _DirectoryAccumulator()
        self._handler = _Handler(self._accumulator)
        self._observer = Observer()
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------

    def run(self) -> None:
        if not self._directories:
            _log.warning(
                "[FileMonitor] No valid monitored_directories; "
                "file monitoring is disabled. Configured: %s",
                self._configured_directories,
            )
            return

        for directory in self._directories:
            self._observer.schedule(self._handler, directory, recursive=True)

        _log.info(
            "[FileMonitor] Watching %d director%s: %s",
            len(self._directories),
            "y" if len(self._directories) == 1 else "ies",
            self._directories,
        )

        self._observer.start()

        # Flush loop — periodically emit directory summaries for
        # directories that have gone quiet.
        while not self._stop_event.is_set():
            self._stop_event.wait(self._flush_interval)
            flushed = self._accumulator.flush_stale(self.event_queue)
            if flushed:
                _log.debug("[FileMonitor] Flushed %d directory summary/summaries.", flushed)

        # Final flush on shutdown — emit whatever is still accumulated.
        remaining = self._accumulator.flush_all(self.event_queue)
        if remaining:
            _log.info("[FileMonitor] Flushed %d remaining summary/summaries on shutdown.", remaining)

        if self._observer.is_alive():
            self._observer.stop()
        self._observer.join()
        _log.info("[FileMonitor] Stopped.")

    def stop(self) -> None:
        self._stop_event.set()