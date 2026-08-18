"""
focus_monitor.py

Tracks which whitelisted application currently has window focus, using
pywin32's GetForegroundWindow(). psutil alone can only tell you a process is
running - it can't tell you which one the user is actually looking at. This
monitor closes that gap by polling the OS for the active foreground window
and mapping it back to a whitelisted process.

Emits:
    application_focused    - a whitelisted app gained foreground focus
    application_unfocused  - that app lost foreground focus (user switched
                              to something else, whitelisted or not)

Windows-only (uses pywin32).
"""

import threading

import psutil
import win32gui # type: ignore
import win32process # type: ignore

from monitoring.common import make_event


class FocusMonitor(threading.Thread):
    def __init__(self, config: dict, event_queue, poll_interval: float = 1.0):
        super().__init__(name="FocusMonitor", daemon=True)
        self.event_queue = event_queue
        self.poll_interval = poll_interval

        whitelist = config.get("monitored_applications", [])
        self._whitelist = {name.lower() for name in whitelist}

        self._stop_event = threading.Event()
        # Currently focused whitelisted app, or None.
        self._current = None  # {"pid": int, "process_name": str}

    def _get_foreground_process(self):
        """Return {'pid', 'process_name'} for the foreground window's owning
        process, or None if it can't be resolved or isn't whitelisted."""
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            return None

        if name.lower() not in self._whitelist:
            return None

        return {"pid": pid, "process_name": name}

    def _emit(self, event_type: str, info: dict):
        event = make_event(
            event_type=event_type,
            source="pywin32",
            data={
                "pid": info["pid"],
                "process_name": info["process_name"],
            },
        )
        self.event_queue.put(event)

    def run(self):
        while not self._stop_event.is_set():
            foreground = self._get_foreground_process()

            # Foreground app changed (including changes to/from "nothing
            # whitelisted focused").
            if (foreground is None and self._current is not None) or (
                foreground is not None
                and self._current is not None
                and foreground["pid"] != self._current["pid"]
            ):
                self._emit("application_unfocused", self._current)
                self._current = None

            if foreground is not None and self._current is None:
                self._emit("application_focused", foreground)
                self._current = foreground

            self._stop_event.wait(self.poll_interval)

        # On shutdown, close out whatever was focused so duration can be computed.
        if self._current is not None:
            self._emit("application_unfocused", self._current)
            self._current = None

    def stop(self):
        self._stop_event.set()