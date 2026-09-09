"""LLM integration package for WorkGuard."""

from llm.ollama_client import (
    OllamaClient,
    get_ollama_client,
)

__all__ = [
    "OllamaClient",
    "get_ollama_client",
]
