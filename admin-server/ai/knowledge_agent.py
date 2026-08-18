"""Local sentence-transformers and FAISS knowledge-index node."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ai.state import WorkGuardState


BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_STORE_DIR = BASE_DIR / "vector_store"
FAISS_INDEX_PATH = VECTOR_STORE_DIR / "sessions.faiss"
METADATA_PATH = VECTOR_STORE_DIR / "sessions_metadata.json"
EMBEDDING_MODEL = os.getenv(
    "WORKGUARD_EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",
)


def _session_to_text(session: dict, analysis: dict) -> str:
    """Create the factual text indexed for later local retrieval."""
    return json.dumps(
        {
            "session_id": session.get("session_id"),
            "employee_id": session.get("employee_id"),
            "duration_seconds": session.get("session", {}).get("duration_seconds"),
            "focus_summary": session.get("focus_summary", {}),
            "analysis": analysis,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _write_metadata(metadata: list[dict]) -> None:
    """Atomically persist FAISS vector metadata."""
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        dir=VECTOR_STORE_DIR,
        prefix=".metadata_",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(metadata, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, METADATA_PATH)
    except OSError:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise


def knowledge_agent(state: WorkGuardState) -> dict:
    """Embed a session locally and add it to the persistent FAISS index."""
    session = state.get("session")
    if not session:
        return {
            "errors": state.get("errors", [])
            + ["Knowledge Agent received no verified session."],
        }

    try:
        # Imports and model loading are lazy: receipt of sessions remains
        # available even if the optional embedding model is not installed.
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer

        embedder = SentenceTransformer(
            EMBEDDING_MODEL,
            local_files_only=True,
        )
        indexed_text = _session_to_text(
            session,
            state.get("session_analysis", {}),
        )
        vector = embedder.encode(
            [indexed_text],
            normalize_embeddings=True,
        )
        vector = np.asarray(vector, dtype="float32")

        VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        if FAISS_INDEX_PATH.exists():
            index = faiss.read_index(str(FAISS_INDEX_PATH))
            if index.d != vector.shape[1]:
                raise ValueError(
                    "Existing FAISS index uses a different embedding dimension."
                )
        else:
            index = faiss.IndexFlatIP(vector.shape[1])

        metadata = []
        if METADATA_PATH.exists():
            metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

        vector_id = index.ntotal
        index.add(vector)
        faiss.write_index(index, str(FAISS_INDEX_PATH))
        metadata.append(
            {
                "vector_id": vector_id,
                "session_id": session.get("session_id"),
                "employee_id": session.get("employee_id"),
                "embedding_model": EMBEDDING_MODEL,
                "indexed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        _write_metadata(metadata)
    except Exception as error:
        return {
            "errors": state.get("errors", [])
            + [f"Knowledge Agent failed: {error}"],
        }

    return {
        "knowledge": {
            "vector_id": vector_id,
            "embedding_model": EMBEDDING_MODEL,
            "indexed": True,
        },
        "workflow_stage": "security",
    }
