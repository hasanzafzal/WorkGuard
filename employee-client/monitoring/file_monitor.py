"""
file_monitor.py

Watches configured project directories using watchdog and emits
file_created / file_modified / file_deleted / file_moved events.

Design decision (finalized): only file activity METADATA is recorded
(path, extension) - never file contents.
"""

import os
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from monitoring.common import make_event


class _Handler(FileSystemEventHandler):
    """Translates raw watchdog events into the standard event schema."""

    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def _emit(self, event_type: str, path: str, extra: dict = None):
        data = {
            "path": path,
            "extension": os.path.splitext(path)[1],
        }
        if extra:
            data.update(extra)
        self.event_queue.put(make_event(event_type=event_type, source="watchdog", data=data))

    def on_created(self, event):
        if event.is_directory:
            return
        self._emit("file_created", event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        self._emit("file_modified", event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._emit("file_deleted", event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        self._emit("file_moved", event.dest_path, extra={"source_path": event.src_path})


class FileMonitor(threading.Thread):
    """
    Wraps a watchdog Observer to recursively monitor configured directories
    and push normalized events onto the shared event queue.
    """

    def __init__(self, config: dict, event_queue):
        super().__init__(name="FileMonitor", daemon=True)
        self.event_queue = event_queue
        self._directories = [
            d for d in config.get("monitored_directories", []) if os.path.isdir(d)
        ]
        self._observer = Observer()
        self._handler = _Handler(event_queue)

    def run(self):
        if not self._directories:
            # Nothing valid to watch - stay idle so the thread's lifecycle
            # stays consistent with the other monitors.
            print("[FileMonitor] No valid monitored_directories found; idling.")
            return

        for directory in self._directories:
            self._observer.schedule(self._handler, directory, recursive=True)

        self._observer.start()
        self._observer.join()  # Blocks until self._observer.stop() is called.

    def stop(self):
        if self._observer.is_alive():
            self._observer.stop()
