"""Semantic retrieval layer querying FAISS vector store and analysis documents."""

from __future__ import annotations

import logging
from typing import Any

from embeddings.indexer import search_documents

logger = logging.getLogger(__name__)


def search_employee_activity(
    query: str,
    employee_id: str | None = None,
    k: int = 5,
    doc_type: str | None = None,
) -> list[dict[str, Any]]:
    """Search for relevant activities of a specific employee using natural language."""
    return search_documents(
        query=query,
        k=k,
        doc_type=doc_type,
        employee_id=employee_id,
    )


def search_knowledge(
    query: str,
    k: int = 5,
    doc_type: str | None = None,
) -> list[dict[str, Any]]:
    """Perform broad semantic search across all indexed organizational analysis documents."""
    return search_documents(
        query=query,
        k=k,
        doc_type=doc_type,
        employee_id=None,
    )
