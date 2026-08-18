"""
sqlite_buffer.py

Local persistent queue for finalized employee sessions.

Responsibilities:
    - Store finalized sessions locally.
    - Keep sessions available until successfully transmitted.
    - Retrieve pending sessions.
    - Track transmission status.
    - Prepare pending sessions for encrypted transmission.

This module does NOT perform networking.

Encryption itself is handled by:
    security/encryption.py

Future flow:

    SessionBuilder
          ↓
    SQLiteBuffer
          ↓
    get_pending_sessions()
          ↓
    prepare_session_for_transmission()
          ↓
    AES-256-GCM
          ↓
    network/client.py
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from security.encryption import encrypt_session


class SQLiteBuffer:
    """
    Local persistent queue for sessions waiting to be transmitted
    to the Admin Server.
    """

    def __init__(
        self,
        db_path: str = "employee_buffer.db"
    ):
        self.db_path = Path(db_path)

        # Make sure parent directory exists.
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self._initialize_database()

    # ------------------------------------------------------------------
    # DATABASE CONNECTION
    # ------------------------------------------------------------------

    def _connect(self):
        """
        Create a SQLite connection.
        """

        return sqlite3.connect(
            self.db_path
        )

    # ------------------------------------------------------------------
    # DATABASE INITIALIZATION
    # ------------------------------------------------------------------

    def _initialize_database(self):
        """
        Create the sessions table if it does not already exist.
        """

        with self._connect() as conn:

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    employee_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL
                )
                """
            )

            conn.commit()

    # ------------------------------------------------------------------
    # ADD SESSION
    # ------------------------------------------------------------------

    def add_session(
        self,
        session: dict
    ) -> bool:
        """
        Add a finalized session to the local transmission queue.

        The original session JSON is stored locally.

        Encryption is NOT performed here.

        This allows the local database to remain a persistent
        transmission queue and lets the encryption layer operate
        immediately before network transmission.
        """

        try:

            session_id = session["session_id"]

            employee_id = session["employee_id"]

            created_at = session["metadata"]["created_at"]

            payload = json.dumps(
                session
            )

        except (KeyError, TypeError) as e:

            print(
                f"[SQLiteBuffer] Invalid session data: {e}"
            )

            return False

        try:

            with self._connect() as conn:

                conn.execute(
                    """
                    INSERT OR IGNORE INTO sessions
                    (
                        session_id,
                        employee_id,
                        payload,
                        status,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        employee_id,
                        payload,
                        "pending",
                        created_at,
                    ),
                )

                conn.commit()

            return True

        except sqlite3.Error as e:

            print(
                f"[SQLiteBuffer] Failed to store session: {e}"
            )

            return False

    # ------------------------------------------------------------------
    # ADD SESSION FROM JSON FILE
    # ------------------------------------------------------------------

    def add_session_from_file(
        self,
        file_path: str
    ) -> bool:
        """
        Read an existing session JSON file and add it to SQLite.
        """

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as f:

                session = json.load(f)

            return self.add_session(
                session
            )

        except (
            OSError,
            json.JSONDecodeError
        ) as e:

            print(
                f"[SQLiteBuffer] "
                f"Failed to read session file: {e}"
            )

            return False

    # ------------------------------------------------------------------
    # GET PENDING SESSIONS
    # ------------------------------------------------------------------

    def get_pending_sessions(
        self,
        limit: int = 10
    ):
        """
        Return pending sessions waiting to be transmitted.

        Each returned record contains:

            id
            session_id
            employee_id
            payload
            status
            created_at
        """

        with self._connect() as conn:

            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT *
                FROM sessions
                WHERE status = 'pending'
                ORDER BY id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    # ------------------------------------------------------------------
    # PREPARE SESSION FOR TRANSMISSION
    # ------------------------------------------------------------------

    def prepare_session_for_transmission(
        self,
        session_id: str,
        key: bytes
    ) -> Optional[dict]:
        """
        Retrieve one pending session and encrypt it using AES-256-GCM.

        The encrypted payload is returned to the caller.

        IMPORTANT:
            This method does NOT mark the session as sent.

        The session should only be marked 'sent' after the Admin
        Server confirms successful receipt.

        Returns:
            dict:
                Encrypted transmission payload.

            None:
                If the session does not exist or is not pending.
        """

        # --------------------------------------------------------------
        # Retrieve pending session
        # --------------------------------------------------------------

        with self._connect() as conn:

            conn.row_factory = sqlite3.Row

            row = conn.execute(
                """
                SELECT *
                FROM sessions
                WHERE session_id = ?
                  AND status = 'pending'
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()

        if row is None:

            print(
                f"[SQLiteBuffer] "
                f"No pending session found: {session_id}"
            )

            return None

        # --------------------------------------------------------------
        # Deserialize original session
        # --------------------------------------------------------------

        try:

            session = json.loads(
                row["payload"]
            )

        except json.JSONDecodeError as e:

            print(
                f"[SQLiteBuffer] "
                f"Invalid stored payload for "
                f"{session_id}: {e}"
            )

            return None

        # --------------------------------------------------------------
        # Encrypt session
        # --------------------------------------------------------------

        try:

            encrypted_payload = encrypt_session(
                session,
                key
            )

        except (
            ValueError,
            TypeError
        ) as e:

            print(
                f"[SQLiteBuffer] "
                f"Encryption failed for "
                f"{session_id}: {e}"
            )

            return None

        # --------------------------------------------------------------
        # Add transmission metadata
        # --------------------------------------------------------------

        transmission_payload = {
            "session_id": session_id,

            "employee_id": row["employee_id"],

            "created_at": row["created_at"],

            "encryption": encrypted_payload,
        }

        return transmission_payload

    # ------------------------------------------------------------------
    # MARK SENT
    # ------------------------------------------------------------------

    def mark_sent(
        self,
        session_id: str
    ):
        """
        Mark a session as successfully transmitted.

        This should ONLY be called after the Admin Server confirms
        successful receipt and processing.
        """

        with self._connect() as conn:

            conn.execute(
                """
                UPDATE sessions
                SET status = 'sent'
                WHERE session_id = ?
                """,
                (session_id,),
            )

            conn.commit()

    # ------------------------------------------------------------------
    # MARK PENDING
    # ------------------------------------------------------------------

    def mark_pending(
        self,
        session_id: str
    ):
        """
        Put a session back into the pending queue.

        This is useful when network transmission fails.
        """

        with self._connect() as conn:

            conn.execute(
                """
                UPDATE sessions
                SET status = 'pending'
                WHERE session_id = ?
                """,
                (session_id,),
            )

            conn.commit()

    # ------------------------------------------------------------------
    # PENDING COUNT
    # ------------------------------------------------------------------

    def get_pending_count(self) -> int:
        """
        Return the number of sessions currently waiting
        for transmission.
        """

        with self._connect() as conn:

            result = conn.execute(
                """
                SELECT COUNT(*)
                FROM sessions
                WHERE status = 'pending'
                """
            ).fetchone()

        return result[0]