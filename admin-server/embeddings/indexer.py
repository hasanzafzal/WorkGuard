"""Indexing service connecting PostgreSQL analysis documents to FAISS."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from database.connection import get_connection
from database.schema import ensure_processing_tables
from embeddings import embed_text, embed_texts, get_embedding_provider
from tools.faiss_tools import get_faiss_store

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def index_documents(documents: list[dict[str, Any]]) -> list[int]:
    """Generate embeddings and index a list of analysis document dictionaries.

    Parameters
    ----------
    documents : list of dict
        Each dict must contain: id, session_id, employee_id, doc_type, title, content.
        Optionally metadata.

    Returns
    -------
    list of int
        The assigned FAISS vector IDs.
    """
    if not documents:
        return []

    provider = get_embedding_provider()
    store = get_faiss_store()

    texts = [doc["content"] for doc in documents]
    vectors = provider.embed_texts(texts)

    metadata_list = [
        {
            "document_id": doc["id"],
            "session_id": doc["session_id"],
            "employee_id": doc["employee_id"],
            "doc_type": doc["doc_type"],
            "title": doc["title"],
            "content": doc["content"],
            "metadata": doc.get("metadata", {}),
        }
        for doc in documents
    ]

    vector_ids = store.add_vectors(vectors, metadata_list)

    # Synchronize into PostgreSQL vector_metadata table
    connection = get_connection()
    try:
        ensure_processing_tables(connection)
        with connection.cursor() as cur:
            for vid, doc in zip(vector_ids, documents):
                cur.execute(
                    """
                    INSERT INTO vector_metadata (
                        vector_id, document_id, session_id, employee_id,
                        doc_type, embedding_model, indexed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (vector_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        session_id = EXCLUDED.session_id,
                        employee_id = EXCLUDED.employee_id,
                        doc_type = EXCLUDED.doc_type,
                        embedding_model = EXCLUDED.embedding_model,
                        indexed_at = EXCLUDED.indexed_at;
                    """,
                    (
                        vid,
                        doc["id"],
                        doc["session_id"],
                        doc["employee_id"],
                        doc["doc_type"],
                        provider.model_name,
                        _now_utc(),
                    ),
                )
        connection.commit()
    finally:
        connection.close()

    logger.info("Indexed %d documents into FAISS (vector IDs: %s)", len(vector_ids), vector_ids)
    return vector_ids


def index_session(session_id: str, force: bool = False) -> int:
    """Index all analysis documents for a specific session into FAISS.

    Parameters
    ----------
    session_id : str
        The session ID whose documents to index.
    force : bool, default False
        If True, removes any existing vectors for this session before re-indexing.

    Returns
    -------
    int
        Count of documents indexed.
    """
    store = get_faiss_store()
    connection = get_connection()
    try:
        ensure_processing_tables(connection)
        with connection.cursor() as cur:
            # Check existing vectors in PostgreSQL
            cur.execute(
                "SELECT vector_id FROM vector_metadata WHERE session_id = %s;",
                (session_id,),
            )
            existing_vids = [r[0] for r in cur.fetchall()]

            if existing_vids and not force:
                logger.info("Session %s already indexed (%d vectors) — skipping", session_id, len(existing_vids))
                return len(existing_vids)

            # If forcing re-index, purge existing vectors from FAISS and PostgreSQL
            if existing_vids and force:
                store.remove_vectors(existing_vids)
                cur.execute(
                    "DELETE FROM vector_metadata WHERE session_id = %s;",
                    (session_id,),
                )
                connection.commit()

            # Fetch analysis documents for this session
            cur.execute(
                """
                SELECT id, session_id, employee_id, doc_type, title, content, metadata
                FROM analysis_documents
                WHERE session_id = %s
                ORDER BY id ASC;
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            if not rows:
                logger.warning("No analysis documents found for session %s to index", session_id)
                return 0

            cols = [d[0] for d in cur.description]
            documents = [dict(zip(cols, r)) for r in rows]

        # Index the documents
        vector_ids = index_documents(documents)
        return len(vector_ids)
    finally:
        connection.close()


def index_all_unindexed(limit: int = 100) -> dict[str, Any]:
    """Find and index all analysis documents that are not yet in vector_metadata."""
    connection = get_connection()
    try:
        ensure_processing_tables(connection)
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT ad.id, ad.session_id, ad.employee_id, ad.doc_type, ad.title, ad.content, ad.metadata
                FROM analysis_documents ad
                LEFT JOIN vector_metadata vm ON ad.id = vm.document_id
                WHERE vm.document_id IS NULL
                ORDER BY ad.id ASC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            pending_docs = [dict(zip(cols, r)) for r in rows]

        if not pending_docs:
            return {"indexed_count": 0, "pending_remaining": 0}

        vector_ids = index_documents(pending_docs)
        return {
            "indexed_count": len(vector_ids),
            "vector_ids": vector_ids,
        }
    finally:
        connection.close()


def search_documents(
    query: str,
    k: int = 5,
    doc_type: str | None = None,
    employee_id: str | None = None,
) -> list[dict[str, Any]]:
    """Perform semantic vector similarity search against the FAISS index."""
    query_vector = embed_text(query)
    store = get_faiss_store()
    return store.search(
        query_vector=query_vector,
        k=k,
        doc_type=doc_type,
        employee_id=employee_id,
    )
