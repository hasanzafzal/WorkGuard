"""Embeddings provider and text-to-vector utilities for WorkGuard."""

from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384


class EmbeddingProvider:
    """Manages embedding model and text-to-vector conversion with L2 normalization."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv(
            "WORKGUARD_EMBEDDING_MODEL",
            DEFAULT_MODEL_NAME,
        )
        try:
            logger.info("Loading embedding model: %s", self.model_name)
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            logger.warning("Failed to load %s: %s. Falling back to %s", self.model_name, e, DEFAULT_MODEL_NAME)
            self.model = SentenceTransformer(DEFAULT_MODEL_NAME)
            self.model_name = DEFAULT_MODEL_NAME

        self.dimension = EMBEDDING_DIMENSION

    def embed_text(self, text: str) -> np.ndarray:
        """Convert a single text string into a normalized 1D float32 embedding vector."""
        vec = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        vec = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Convert multiple text strings into normalized 2D float32 embedding vectors."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        vecs = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False, batch_size=32)
        vecs = np.array(vecs, dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vecs = vecs / norms
        return vecs


# Global singleton provider instance
_embedding_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Get or instantiate the global embedding provider."""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = EmbeddingProvider()
    return _embedding_provider


def embed_text(text: str) -> np.ndarray:
    """Convenience function to embed a single text string."""
    return get_embedding_provider().embed_text(text)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Convenience function to embed a batch of text strings."""
    return get_embedding_provider().embed_texts(texts)
