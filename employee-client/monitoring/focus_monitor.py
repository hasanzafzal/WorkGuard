"""
focus_monitor.py

Tracks which user-facing application currently has window focus, using
pywin32's GetForegroundWindow(). psutil alone can only tell you a process is
running - it cannot tell you which one the user is actually looking at. This
monitor closes that gap by polling the OS for the active foreground window
and mapping it back to a non-background process.

Emits:
    application_focused    - a user-facing app gained foreground focus
    application_unfocused  - that app lost foreground focus

Desktop / idle tracking
-----------------------
When GetForegroundWindow() cannot be resolved to a trackable process (user is
at the desktop, all windows are minimised, lock screen transitions, etc.) the
monitor waits for a short configurable grace period before emitting a
synthetic ``application_focused`` event with process_name="Desktop" and
pid=0.  This prevents rapid window-switching from polluting the focus_summary
with spurious Desktop entries while still capturing genuine desktop/idle time.

The grace period is read from config["idle_grace_seconds"] (default: 3).
"Desktop" accumulates in focus_summary exactly like any real application.

Windows-only (uses pywin32).
"""

import logging
import threading
import time

import psutil
import win32gui      # type: ignore
import win32process  # type: ignore

from monitoring.common import make_event
from monitoring.process_filter import StaticProcessFilter

_log = logging.getLogger(__name__)

# Synthetic name used in events and focus_summary when no real application
# has window focus.  Must not collide with any real process name.
_DESKTOP_PROCESS_NAME = "Desktop"

# Default seconds of continuous "no focus" before a Desktop event is emitted.
_DEFAULT_IDLE_GRACE_SECONDS = 3.0


class FocusMonitor(threading.Thread):

    def __init__(self, config: dict, event_queue, poll_interval: float = 1.0):
        super().__init__(name="FocusMonitor", daemon=True)
        self.event_queue = event_queue
        self.poll_interval = poll_interval
        self.idle_grace_seconds: float = float(
            config.get("idle_grace_seconds", _DEFAULT_IDLE_GRACE_SECONDS)
        )

        self._program_filter: StaticProcessFilter = (
            config.get("program_filter") or StaticProcessFilter(config)
        )

        self._stop_event = threading.Event()
        # Currently tracked app (real or Desktop placeholder), or None.
        self._current: dict | None = None   # {"pid": int, "process_name": str}
        # Monotonic timestamp of when the foreground became unresolvable.
        self._no_focus_since: float | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_foreground_process(self) -> dict | None:
        """
        Return {"pid", "process_name"} for the foreground window's owning
        process, or None if it cannot be resolved or is a background process.

        Error handling is split into two layers:
          - psutil errors (NoSuchProcess, AccessDenied) are expected and
            silent — the process may have died between GetForegroundWindow
            and Process().
          - All other exceptions come from Win32 (COM errors, invalid handle
            races) and are logged at DEBUG level only.
        """
        try:
            hwnd = win32gui.GetForegroundWindow()
        except Exception:
            _log.debug("[FocusMonitor] GetForegroundWindow failed.", exc_info=True)
            return None

        if not hwnd:
            return None

        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
        except Exception:
            _log.debug(
                "[FocusMonitor] GetWindowThreadProcessId failed for hwnd=%s.", hwnd,
                exc_info=True,
            )
            return None

        try:
            proc = psutil.Process(pid)
            name = proc.name()
            try:
                exe = proc.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # exe() needs more privilege than name() on some systems.
                # Rules 1 and 3 of StaticProcessFilter still run.
                exe = ""
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

        if not self._program_filter.is_allowed(name, exe, pid=pid):
            return None

        return {"pid": pid, "process_name": name}

    def _emit(self, event_type: str, info: dict) -> None:
        event = make_event(
            event_type=event_type,
            source="pywin32",
            data={
                "pid": info["pid"],
                "process_name": info["process_name"],
            },
        )
        self.event_queue.put(event)
        _log.debug(
            "[FocusMonitor] %s  pid=%d  %s",
            event_type, info["pid"], info["process_name"],
        )

    # ------------------------------------------------------------------
    # Thread entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        _log.info(
            "[FocusMonitor] Started (poll_interval=%.1f s, idle_grace=%.1f s).",
            self.poll_interval,
            self.idle_grace_seconds,
        )

        while not self._stop_event.is_set():
            foreground = self._get_foreground_process()
            now = time.monotonic()

            if foreground is None:
                # ── No resolvable foreground window ───────────────────────

                # Record when we first lost focus.
                if self._no_focus_since is None:
                    self._no_focus_since = now

                # Immediately close out any real app that was being tracked.
                # (Desktop placeholder is left open until a real app returns.)
                if (
                    self._current is not None
                    and self._current["process_name"] != _DESKTOP_PROCESS_NAME
                ):
                    self._emit("application_unfocused", self._current)
                    self._current = None

                # After the grace period, synthesise a Desktop focus event
                # so the time gap appears in focus_summary.
                if (
                    self._current is None
                    and (now - self._no_focus_since) >= self.idle_grace_seconds
                ):
                    desktop_info: dict = {"pid": 0, "process_name": _DESKTOP_PROCESS_NAME}
                    self._emit("application_focused", desktop_info)
                    self._current = desktop_info

            else:
                # ── A real app is in the foreground ───────────────────────
                self._no_focus_since = None

                # Close whatever was tracked (real app or Desktop placeholder).
                if (
                    self._current is not None
                    and self._current["pid"] != foreground["pid"]
                ):
                    self._emit("application_unfocused", self._current)
                    self._current = None

                # Start tracking the newly focused app.
                if self._current is None:
                    self._emit("application_focused", foreground)
                    self._current = foreground

            self._stop_event.wait(self.poll_interval)

        # Emit a final unfocus on shutdown so session_builder can close the
        # open interval (real app or Desktop) and compute accurate durations.
        if self._current is not None:
            self._emit("application_unfocused", self._current)
            self._current = None

        _log.info("[FocusMonitor] Stopped.")

    def stop(self) -> None:
        self._stop_event.set()