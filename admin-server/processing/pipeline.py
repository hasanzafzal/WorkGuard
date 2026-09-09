"""PostgreSQL-to-Processing Pipeline engine.

Reads sessions from PostgreSQL, normalizes and enriches the data,
generates structured analysis documents, and persists them into PostgreSQL.
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from psycopg.types.json import Json

from database.connection import get_connection
from database.schema import ensure_processing_tables
from processing.document_generator import generate_all_documents
from processing.normalizer import (
    calculate_and_update_productive_seconds,
    fetch_normalized_session,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_pending_sessions(limit: int = 50) -> list[str]:
    """Retrieve session IDs that have not been successfully processed yet."""
    connection = get_connection()
    try:
        ensure_processing_tables(connection)
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT s.session_id
                FROM sessions s
                LEFT JOIN session_processing_status sps ON s.session_id = sps.session_id
                WHERE sps.session_id IS NULL OR sps.status IN ('pending', 'failed')
                ORDER BY s.start_time ASC
                LIMIT %s;
                """,
                (limit,),
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        connection.close()


def process_session(session_id: str, force: bool = False) -> dict[str, Any]:
    """Process a single session from PostgreSQL.

    1. Checks if already completed (unless force=True).
    2. Marks session as 'processing'.
    3. Fetches normalized session data and calculates productive time.
    4. Generates analysis documents.
    5. Persists documents into `analysis_documents`.
    6. Marks status as 'completed'.

    Parameters
    ----------
    session_id : str
        The unique ID of the session to process.
    force : bool, default False
        If True, re-processes even if already completed.

    Returns
    -------
    dict
        Summary of the processing outcome.
    """
    connection = get_connection()
    try:
        ensure_processing_tables(connection)

        # Check existing status
        with connection.cursor() as cur:
            cur.execute(
                "SELECT status FROM session_processing_status WHERE session_id = %s;",
                (session_id,),
            )
            row = cur.fetchone()
            if row and row[0] == "completed" and not force:
                logger.info("Session %s already completed — skipping", session_id)
                return {
                    "session_id": session_id,
                    "status": "already_completed",
                    "documents_count": 0,
                }

            # Upsert into session_processing_status as 'processing'
            cur.execute(
                """
                INSERT INTO session_processing_status (session_id, status, updated_at)
                VALUES (%s, 'processing', %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    status = 'processing',
                    error_message = NULL,
                    updated_at = EXCLUDED.updated_at;
                """,
                (session_id, _now_utc()),
            )
        connection.commit()
    finally:
        connection.close()

    try:
        # Step 1: Normalize session data from PostgreSQL
        ns = fetch_normalized_session(session_id)
        if not ns:
            raise ValueError(f"Session {session_id} not found in database")

        # Step 2: Calculate and update productive seconds
        productive_seconds = calculate_and_update_productive_seconds(
            session_id=session_id,
            app_focus_items=ns.app_focus_items,
        )
        ns.productive_seconds = productive_seconds

        # Step 3: Generate structured analysis documents
        documents = generate_all_documents(ns)

        # Step 4: Persist documents and update processing status atomically
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # If re-processing, remove older documents for this session
                cur.execute(
                    "DELETE FROM analysis_documents WHERE session_id = %s;",
                    (session_id,),
                )

                # Insert newly generated analysis documents
                for doc in documents:
                    cur.execute(
                        """
                        INSERT INTO analysis_documents (
                            session_id, employee_id, doc_type, title, content, metadata, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s);
                        """,
                        (
                            doc.session_id,
                            doc.employee_id,
                            doc.doc_type,
                            doc.title,
                            doc.content,
                            Json(doc.metadata),
                            _now_utc(),
                        ),
                    )

                # Mark status as completed
                cur.execute(
                    """
                    UPDATE session_processing_status
                    SET status = 'completed',
                        documents_count = %s,
                        processed_at = %s,
                        error_message = NULL,
                        updated_at = %s
                    WHERE session_id = %s;
                    """,
                    (len(documents), _now_utc(), _now_utc(), session_id),
                )
            conn.commit()
        finally:
            conn.close()

        logger.info(
            "Session %s successfully processed into %d analysis documents",
            session_id,
            len(documents),
        )

        # Step 5: Index analysis documents into FAISS and sync vector_metadata
        indexed_count = 0
        try:
            from embeddings.indexer import index_session
            indexed_count = index_session(session_id, force=force)
            logger.info("Session %s: %d documents indexed into FAISS", session_id, indexed_count)
        except Exception as idx_err:
            logger.warning("Session %s FAISS indexing encountered an issue: %s", session_id, idx_err)

        return {
            "session_id": session_id,
            "status": "completed",
            "employee_id": ns.employee_id,
            "documents_count": len(documents),
            "vectors_indexed": indexed_count,
            "productive_seconds": productive_seconds,
            "duration_seconds": ns.duration_seconds,
        }


    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        logger.error("Failed to process session %s: %s", session_id, exc)

        # Record failure in database
        conn_fail = get_connection()
        try:
            with conn_fail.cursor() as cur:
                cur.execute(
                    """
                    UPDATE session_processing_status
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = %s
                    WHERE session_id = %s;
                    """,
                    (err_msg, _now_utc(), session_id),
                )
            conn_fail.commit()
        finally:
            conn_fail.close()

        raise


def process_all_pending(limit: int = 50, force: bool = False) -> dict[str, Any]:
    """Find and process all pending sessions up to limit."""
    pending = get_pending_sessions(limit=limit)
    logger.info("Found %d pending sessions to process", len(pending))

    results = []
    failed = []

    for s_id in pending:
        try:
            res = process_session(s_id, force=force)
            results.append(res)
        except Exception as err:
            failed.append({"session_id": s_id, "error": str(err)})

    return {
        "total_pending": len(pending),
        "processed_count": len(results),
        "failed_count": len(failed),
        "results": results,
        "failures": failed,
    }
