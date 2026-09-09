"""FAISS vector store integration for semantic retrieval using IndexIDMap2."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import faiss
import numpy as np

logger = logging.getLogger(__name__)

VECTOR_STORE_DIR = Path(__file__).resolve().parent.parent / "vector_store"
DEFAULT_INDEX_PATH = str(VECTOR_STORE_DIR / "session_index.faiss")
DEFAULT_METADATA_PATH = str(VECTOR_STORE_DIR / "metadata.json")
DIMENSION = 384


class FAISSStore:
    """Manages persistent FAISS IndexIDMap2 index for cosine similarity search."""

    def __init__(
        self,
        index_path: str | None = None,
        metadata_path: str | None = None,
    ) -> None:
        self.index_path = index_path or DEFAULT_INDEX_PATH
        self.metadata_path = metadata_path or DEFAULT_METADATA_PATH
        self.dimension = DIMENSION

        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)

        self.index: faiss.IndexIDMap2 | None = None
        self.metadata: dict[str, dict[str, Any]] = {}
        self._load_or_create_index()

    def _create_fresh_index(self) -> faiss.IndexIDMap2:
        """Create a new IndexIDMap2 wrapping IndexFlatIP for cosine similarity."""
        base_index = faiss.IndexFlatIP(self.dimension)
        return faiss.IndexIDMap2(base_index)

    def _load_or_create_index(self) -> None:
        """Load existing FAISS index or initialize a fresh IndexIDMap2."""
        if os.path.exists(self.index_path):
            try:
                loaded = faiss.read_index(self.index_path)
                if isinstance(loaded, faiss.IndexIDMap2):
                    self.index = loaded
                else:
                    # Upgrade legacy flat index to IndexIDMap2
                    logger.info("Upgrading legacy flat FAISS index to IndexIDMap2")
                    map_index = faiss.IndexIDMap2(loaded)
                    self.index = map_index
                logger.info("Loaded FAISS index with %d vectors from %s", self.index.ntotal, self.index_path)
            except Exception as e:
                logger.warning("Failed to load FAISS index from %s: %s. Creating new index.", self.index_path, e)
                self.index = self._create_fresh_index()
        else:
            self.index = self._create_fresh_index()

        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.warning("Failed to load FAISS metadata from %s: %s", self.metadata_path, e)
                self.metadata = {}
        else:
            self.metadata = {}

    def _get_next_vector_id(self) -> int:
        """Find the next available integer vector ID."""
        if not self.metadata:
            return 1
        existing_ids = [int(k) for k in self.metadata.keys() if k.isdigit()]
        return (max(existing_ids) + 1) if existing_ids else 1

    def add_vectors(
        self,
        vectors: np.ndarray,
        metadata_list: list[dict[str, Any]],
        vector_ids: list[int] | None = None,
    ) -> list[int]:
        """Add vectors with explicit integer IDs to the IndexIDMap2 index.

        Parameters
        ----------
        vectors : np.ndarray
            Shape (N, 384), float32 normalized vectors.
        metadata_list : list of dict
            Metadata dict for each vector.
        vector_ids : list of int, optional
            Explicit IDs. If omitted, sequential IDs are generated.

        Returns
        -------
        list of int
            The assigned vector IDs.
        """
        n = len(vectors)
        if n != len(metadata_list):
            raise ValueError(f"Vectors count ({n}) must match metadata count ({len(metadata_list)})")
        if n == 0:
            return []

        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension must be {self.dimension}, got {vectors.shape[1]}")

        # Ensure float32 normalized
        vectors_f32 = np.ascontiguousarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(vectors_f32, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vectors_f32 = vectors_f32 / norms

        if vector_ids is None:
            start_id = self._get_next_vector_id()
            assigned_ids = list(range(start_id, start_id + n))
        else:
            if len(vector_ids) != n:
                raise ValueError(f"vector_ids length ({len(vector_ids)}) must match vectors count ({n})")
            assigned_ids = vector_ids

        ids_array = np.array(assigned_ids, dtype=np.int64)

        # If any of these IDs already exist in the index, remove them first
        existing_ids = [vid for vid in assigned_ids if str(vid) in self.metadata]
        if existing_ids:
            self.remove_vectors(existing_ids)

        self.index.add_with_ids(vectors_f32, ids_array)

        for vid, meta in zip(assigned_ids, metadata_list):
            self.metadata[str(vid)] = meta

        self._save_index()
        return assigned_ids

    def remove_vectors(self, vector_ids: list[int]) -> int:
        """Remove vectors from FAISS and metadata by explicit IDs."""
        if not vector_ids or self.index.ntotal == 0:
            return 0

        ids_to_remove = [int(v) for v in vector_ids if str(v) in self.metadata]
        if not ids_to_remove:
            return 0

        ids_array = np.array(ids_to_remove, dtype=np.int64)
        removed_count = self.index.remove_ids(ids_array)

        for vid in ids_to_remove:
            self.metadata.pop(str(vid), None)

        self._save_index()
        logger.info("Removed %d vectors from FAISS index", removed_count)
        return removed_count

    def search(
        self,
        query_vector: np.ndarray,
        k: int = 5,
        doc_type: str | None = None,
        employee_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search the FAISS index by cosine similarity with optional metadata filtering."""
        if self.index.ntotal == 0:
            return []

        # Prepare normalized query vector
        query_f32 = np.ascontiguousarray(query_vector.reshape(1, -1), dtype=np.float32)
        norm = np.linalg.norm(query_f32)
        if norm > 0:
            query_f32 = query_f32 / norm

        # Retrieve a broader candidate set if filtering is applied
        fetch_k = min(self.index.ntotal, k * 5 if (doc_type or employee_id) else k)
        distances, indices = self.index.search(query_f32, fetch_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            vid = int(idx)
            meta = self.metadata.get(str(vid), {})

            # Apply filters
            if doc_type and meta.get("doc_type") != doc_type:
                continue
            if employee_id and meta.get("employee_id") != employee_id:
                continue

            results.append({
                "vector_id": vid,
                "score": round(float(dist), 4),  # Cosine similarity in [-1, 1]
                "document_id": meta.get("document_id"),
                "session_id": meta.get("session_id"),
                "employee_id": meta.get("employee_id"),
                "doc_type": meta.get("doc_type"),
                "title": meta.get("title"),
                "content": meta.get("content"),
                "metadata": meta.get("metadata", {}),
            })

            if len(results) >= k:
                break

        return results

    def _save_index(self) -> None:
        """Persist index and metadata atomically to disk."""
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, default=str)

    def get_size(self) -> int:
        """Return total number of vectors in the FAISS index."""
        return self.index.ntotal

    def clear(self) -> None:
        """Clear all vectors from the index and metadata."""
        self.index = self._create_fresh_index()
        self.metadata = {}
        self._save_index()


# Global FAISSStore singleton
_global_faiss_store: FAISSStore | None = None


def get_faiss_store() -> FAISSStore:
    """Get or create the global FAISSStore instance."""
    global _global_faiss_store
    if _global_faiss_store is None:
        _global_faiss_store = FAISSStore()
    return _global_faiss_store
