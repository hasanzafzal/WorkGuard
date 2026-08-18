import os

from storage.sqlite_buffer import SQLiteBuffer
from security.encryption import (
    generate_key,
    decrypt_session,
)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DB_PATH = os.path.join(
    BASE_DIR,
    "storage",
    "employee_buffer.db"
)


def main():

    # --------------------------------------------------------------
    # Initialize buffer
    # --------------------------------------------------------------

    buffer = SQLiteBuffer(
        db_path=DB_PATH
    )

    # --------------------------------------------------------------
    # Find pending sessions
    # --------------------------------------------------------------

    pending = buffer.get_pending_sessions(
        limit=1
    )

    if not pending:

        print(
            "[TEST] No pending sessions found."
        )

        print(
            "[TEST] Run main.py and generate a session first."
        )

        return

    record = pending[0]

    session_id = record["session_id"]

    print(
        f"[TEST] Found pending session: "
        f"{session_id}"
    )

    # --------------------------------------------------------------
    # Generate test AES key
    # --------------------------------------------------------------

    key = generate_key()

    print(
        "[TEST] Generated AES-256 key."
    )

    # --------------------------------------------------------------
    # Prepare encrypted transmission payload
    # --------------------------------------------------------------

    encrypted_payload = (
        buffer.prepare_session_for_transmission(
            session_id,
            key
        )
    )

    if encrypted_payload is None:

        print(
            "[TEST] FAIL: "
            "Could not prepare encrypted payload."
        )

        return

    print(
        "[TEST] Encryption successful."
    )

    print(
        "[TEST] Transmission payload:"
    )

    print(
        encrypted_payload
    )

    # --------------------------------------------------------------
    # Decrypt again to verify
    # --------------------------------------------------------------

    decrypted_session = decrypt_session(
        encrypted_payload["encryption"],
        key
    )

    # --------------------------------------------------------------
    # Compare with SQLite original
    # --------------------------------------------------------------

    import json

    original_session = json.loads(
        record["payload"]
    )

    if decrypted_session == original_session:

        print(
            "\n[TEST] PASS:"
        )

        print(
            "SQLite -> AES-256-GCM -> "
            "Decryption produced the original session."
        )

    else:

        print(
            "\n[TEST] FAIL:"
        )

        print(
            "Decrypted session does not match "
            "SQLite session."
        )

        return

    # --------------------------------------------------------------
    # Important status check
    # --------------------------------------------------------------

    pending_after = (
        buffer.get_pending_sessions(
            limit=10
        )
    )

    still_pending = any(
        item["session_id"] == session_id
        for item in pending_after
    )

    if still_pending:

        print(
            "[TEST] PASS: "
            "Session remains pending."
        )

    else:

        print(
            "[TEST] FAIL: "
            "Session was unexpectedly removed "
            "from the pending queue."
        )

        return

    print(
        "\n======================================"
    )

    print(
        " SQLITE + AES-256-GCM TEST PASSED"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":
    main()
