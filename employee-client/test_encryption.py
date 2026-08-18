"""
test_encryption.py

Standalone test for WorkGuard AES-256-GCM encryption.

This test:
    1. Loads an existing session JSON.
    2. Generates an AES-256 key.
    3. Encrypts the session.
    4. Decrypts the session.
    5. Verifies that the decrypted session exactly matches
       the original.
    6. Tests that tampering is detected.
"""

import json
import os

from cryptography.exceptions import InvalidTag

from security.encryption import (
    generate_key,
    key_to_base64,
    encrypt_session,
    decrypt_session,
)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

SESSIONS_DIR = os.path.join(
    BASE_DIR,
    "sessions"
)


def find_session_file():
    """
    Find the first session JSON file in the sessions directory.
    """

    files = [
        file
        for file in os.listdir(SESSIONS_DIR)
        if file.endswith(".json")
    ]

    if not files:
        raise FileNotFoundError(
            "No session JSON files found in the sessions directory."
        )

    return os.path.join(
        SESSIONS_DIR,
        files[0]
    )


def main():

    # ------------------------------------------------------------------
    # Find an existing session
    # ------------------------------------------------------------------

    session_path = find_session_file()

    print(
        f"[TEST] Loading session:\n"
        f"       {session_path}"
    )

    with open(
        session_path,
        "r",
        encoding="utf-8"
    ) as f:

        original_session = json.load(f)

    print(
        f"[TEST] Session ID: "
        f"{original_session['session_id']}"
    )

    # ------------------------------------------------------------------
    # Generate AES-256 key
    # ------------------------------------------------------------------

    key = generate_key()

    print(
        "[TEST] Generated AES-256 key."
    )

    print(
        "[TEST] Base64 key:"
    )

    print(
        key_to_base64(key)
    )

    # ------------------------------------------------------------------
    # Encrypt
    # ------------------------------------------------------------------

    encrypted = encrypt_session(
        original_session,
        key
    )

    print(
        "\n[TEST] Encryption successful."
    )

    print(
        f"[TEST] Algorithm: "
        f"{encrypted['algorithm']}"
    )

    print(
        f"[TEST] Session ID: "
        f"{encrypted['session_id']}"
    )

    print(
        f"[TEST] Nonce: "
        f"{encrypted['nonce']}"
    )

    print(
        f"[TEST] Ciphertext length: "
        f"{len(encrypted['ciphertext'])} characters"
    )

    # ------------------------------------------------------------------
    # Decrypt
    # ------------------------------------------------------------------

    decrypted_session = decrypt_session(
        encrypted,
        key
    )

    print(
        "\n[TEST] Decryption successful."
    )

    # ------------------------------------------------------------------
    # Verify original == decrypted
    # ------------------------------------------------------------------

    if decrypted_session == original_session:

        print(
            "[TEST] PASS: "
            "Decrypted session exactly matches "
            "the original session."
        )

    else:

        print(
            "[TEST] FAIL: "
            "Decrypted session does not match "
            "the original session."
        )

        raise SystemExit(1)

    # ------------------------------------------------------------------
    # Test tamper detection
    # ------------------------------------------------------------------

    print(
        "\n[TEST] Testing tamper detection..."
    )

    tampered = encrypted.copy()

    ciphertext = tampered["ciphertext"]

    # Change one Base64 character.
    #
    # This should cause AES-GCM authentication to fail.

    replacement = (
        "A"
        if ciphertext[0] != "A"
        else "B"
    )

    tampered["ciphertext"] = (
        replacement + ciphertext[1:]
    )

    try:

        decrypt_session(
            tampered,
            key
        )

        print(
            "[TEST] FAIL: "
            "Tampered ciphertext was accepted!"
        )

        raise SystemExit(1)

    except InvalidTag:

        print(
            "[TEST] PASS: "
            "Tampered ciphertext was rejected."
        )

    # ------------------------------------------------------------------
    # Final result
    # ------------------------------------------------------------------

    print(
        "\n======================================"
    )

    print(
        " AES-256-GCM TEST PASSED"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":

    main()