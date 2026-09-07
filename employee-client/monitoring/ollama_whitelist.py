"""Blacklist default Windows background tasks with a local Ollama model."""

import json
import threading
from typing import Any

import requests


KNOWN_WINDOWS_BACKGROUND_PROCESSES = {
    "audiodg.exe",
    "csrss.exe",
    "dwm.exe",
    "lsass.exe",
    "services.exe",
    "smss.exe",
    "spoolsv.exe",
    "svchost.exe",
    "wininit.exe",
    "winlogon.exe",
}


class OllamaWhitelist:
    """Cache background-task decisions while allowing user applications."""

    def __init__(self, config: dict[str, Any]):
        fallback = config.get("monitored_applications", [])
        self._fallback = {str(name).lower() for name in fallback}
        self._cache: dict[str, bool] = {}
        self._lock = threading.Lock()
        self._enabled = config.get("whitelist_mode", "ollama") == "ollama"
        self._model = config.get("ollama_model", "llama3:latest")
        self._url = config.get(
            "ollama_url",
            "http://127.0.0.1:11434/api/generate",
        )
        self._timeout = float(config.get("ollama_timeout_seconds", 8))

    def is_allowed(self, process_name: str, executable: str = "") -> bool:
        """Return whether a process should contribute events to sessions."""
        key = process_name.lower()
        with self._lock:
            if key in self._cache:
                return self._cache[key]

        if not self._enabled:
            allowed = self._fallback_decision(key)
            decision_source = "configured list"
        else:
            try:
                model_allowed = self._ask_model(process_name, executable)
                process_is_known_background = (
                    key in KNOWN_WINDOWS_BACKGROUND_PROCESSES
                )
                # Ollama may classify, but it cannot blacklist an unknown
                # process. This prevents false positives for user software.
                allowed = model_allowed or not process_is_known_background
                decision_source = f"Ollama ({self._model})"
            except (OSError, ValueError, requests.RequestException) as error:
                # Ollama mode is an exclusion policy: an unavailable model must
                # not silently turn the allowlist back into the old static list.
                allowed = True
                decision_source = "allow-by-default fallback"
                print(
                    f"[OllamaWhitelist] {process_name}: {error}; "
                    "allowing because Ollama mode only blacklists background tasks"
                )

        with self._lock:
            self._cache[key] = allowed
        print(
            f"[OllamaWhitelist] {process_name}: "
            f"{'allowed' if allowed else 'blocked'} by {decision_source}"
        )
        return allowed

    def _fallback_decision(self, process_name: str) -> bool:
        return process_name in self._fallback

    def _ask_model(self, process_name: str, executable: str) -> bool:
        prompt = f"""You are a Windows background-task blacklist for an employee activity monitor.
    The default policy is to allow every program. Block a program only when it is a
    standard Windows background task or operating-system service that normally runs
    without a user-facing window. User applications, development tools, office
    software, terminals, browsers, games, media players, security tools, unknown
    programs, and anything with a normal user interface must be allowed.
    Return JSON only in exactly this format: {{"background_task": true}} or
    {{"background_task": false}}.

Program name: {process_name}
Executable path: {executable or "unknown"}
"""
        response = requests.post(
            self._url,
            json={
                "model": self._model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        body = response.json()
        result = json.loads(body.get("response", "{}"))
        if not isinstance(result.get("background_task"), bool):
            raise ValueError("Ollama returned no boolean 'background_task' value")
        return not result["background_task"]