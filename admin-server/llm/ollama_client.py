"""Ollama client for local LLM inference in WorkGuard."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3:latest"


class OllamaClient:
    """HTTP client for Ollama API providing text and chat completion."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 180,
    ) -> None:
        self.base_url = (base_url or os.getenv("WORKGUARD_OLLAMA_URL", DEFAULT_OLLAMA_URL)).rstrip("/")
        self.model = model or os.getenv("WORKGUARD_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self.timeout = timeout

    def check_health(self) -> dict[str, Any]:
        """Check connection to Ollama and verify model availability."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if resp.status_code != 200:
                return {"status": "error", "message": f"Ollama returned HTTP {resp.status_code}"}

            models = [m.get("name") for m in resp.json().get("models", [])]
            # Match model name or model prefix (e.g. 'llama3:latest' matches 'llama3')
            model_present = any(
                self.model == m or self.model.split(":")[0] == m.split(":")[0]
                for m in models
            )

            return {
                "status": "ok" if model_present else "warning",
                "base_url": self.base_url,
                "configured_model": self.model,
                "model_present": model_present,
                "available_models": models,
            }
        except Exception as e:
            return {
                "status": "unreachable",
                "base_url": self.base_url,
                "error": str(e),
            }

    def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        num_predict: int = 300,
    ) -> str:
        """Call Ollama /api/generate endpoint."""
        url = f"{self.base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except requests.RequestException as e:
            logger.error("Ollama generate request failed: %s", e)
            raise RuntimeError(f"Ollama generation failed: {e}") from e

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        num_predict: int = 300,
    ) -> str:
        """Call Ollama /api/chat endpoint."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
            },
        }


        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            msg = data.get("message", {})
            return msg.get("content", "").strip()
        except requests.RequestException as e:
            logger.error("Ollama chat request failed: %s", e)
            raise RuntimeError(f"Ollama chat failed: {e}") from e


# Global singleton instance
_ollama_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    """Get or create the global OllamaClient."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
