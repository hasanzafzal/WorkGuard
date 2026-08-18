"""HTTP transmission for encrypted WorkGuard employee sessions."""

from typing import Optional

import requests

from storage.sqlite_buffer import SQLiteBuffer


class NetworkClient:
    """Send pending SQLite sessions to the WorkGuard Admin Server."""

    def __init__(
        self,
        sqlite_buffer: SQLiteBuffer,
        encryption_key: bytes,
        server_url: str = "http://127.0.0.1:8000",
        timeout_seconds: float = 5.0,
    ):
        self.sqlite_buffer = sqlite_buffer
        self.encryption_key = encryption_key
        self.sessions_url = f"{server_url.rstrip('/')}/api/v1/sessions"
        self.timeout_seconds = timeout_seconds

    def transmit_pending_sessions(self, limit: int = 10) -> int:
        """
        Encrypt and transmit up to ``limit`` pending sessions.

        A session is marked sent only when the Admin Server returns a matching
        ``received`` acknowledgement. Network and server failures leave the
        session pending for a later retry.
        """

        sent_count = 0
        pending_sessions = self.sqlite_buffer.get_pending_sessions(limit=limit)

        for record in pending_sessions:
            session_id = record["session_id"]
            payload = self.sqlite_buffer.prepare_session_for_transmission(
                session_id,
                self.encryption_key,
            )

            if payload is None:
                continue

            try:
                response = requests.post(
                    self.sessions_url,
                    json=payload,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                acknowledgement = response.json()
            except (requests.RequestException, ValueError) as error:
                print(
                    "[NetworkClient] Transmission failed for "
                    f"{session_id}; it remains pending: {error}"
                )
                continue

            if (
                acknowledgement.get("status") != "received"
                or acknowledgement.get("session_id") != session_id
            ):
                print(
                    "[NetworkClient] Invalid acknowledgement for "
                    f"{session_id}; it remains pending."
                )
                continue

            self.sqlite_buffer.mark_sent(session_id)
            sent_count += 1
            print(f"[NetworkClient] Session sent: {session_id}")

        return sent_count
