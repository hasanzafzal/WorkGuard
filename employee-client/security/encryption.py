"""
encryption.py

AES-256-GCM encryption utilities for WorkGuard.

Purpose:
    Encrypt finalized employee session payloads before they are
    transmitted over the LAN to the Admin PC.

Security:
    - AES-256
    - GCM (Galois/Counter Mode)
    - 256-bit secret key
    - Random 96-bit nonce for every encryption operation
    - Authentication/integrity protection provided by GCM

Important:
    This module does NOT handle networking.
    It only performs encryption and decryption.

Future flow:

    Session
        ↓
    SQLite
        ↓
    encryption.py
        ↓
    AES-256-GCM
        ↓
    Encrypted payload
        ↓
    network/client.py
"""

import base64
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

KEY_SIZE_BYTES = 32       # 32 bytes = 256 bits
NONCE_SIZE_BYTES = 12     # Recommended GCM nonce size


# ---------------------------------------------------------------------------
# KEY MANAGEMENT
# ---------------------------------------------------------------------------

def generate_key() -> bytes:
    """
    Generate a cryptographically secure 256-bit AES key.

    Returns:
        bytes: 32-byte AES-256 key.
    """

    return AESGCM.generate_key(
        bit_length=256
    )


def key_to_base64(key: bytes) -> str:
    """
    Convert a binary AES key into a Base64 string.

    Useful for storing the key in an environment variable or
    local secret configuration.
    """

    if len(key) != KEY_SIZE_BYTES:
        raise ValueError(
            "AES-256 key must be exactly 32 bytes."
        )

    return base64.b64encode(key).decode("utf-8")


def key_from_base64(key_string: str) -> bytes:
    """
    Convert a Base64-encoded AES key back into bytes.
    """

    try:

        key = base64.b64decode(
            key_string,
            validate=True
        )

    except Exception as e:

        raise ValueError(
            "Invalid Base64 AES key."
        ) from e

    if len(key) != KEY_SIZE_BYTES:
        raise ValueError(
            "AES-256 key must decode to exactly 32 bytes."
        )

    return key


# ---------------------------------------------------------------------------
# ENCRYPTION
# ---------------------------------------------------------------------------

def encrypt_data(
    plaintext: bytes,
    key: bytes,
    associated_data: bytes | None = None
) -> dict:
    """
    Encrypt arbitrary bytes using AES-256-GCM.

    Args:
        plaintext:
            Data to encrypt.

        key:
            32-byte AES-256 key.

        associated_data:
            Optional authenticated but unencrypted metadata.

    Returns:
        dict containing:
            nonce
            ciphertext

        Both are Base64 encoded so they can safely be transmitted
        as JSON.

    Notes:
        AES-GCM internally generates an authentication tag as part
        of the encrypted output returned by the cryptography library.
    """

    if len(key) != KEY_SIZE_BYTES:
        raise ValueError(
            "AES-256 key must be exactly 32 bytes."
        )

    # Generate a fresh random nonce for EVERY encryption.
    nonce = os.urandom(
        NONCE_SIZE_BYTES
    )

    aesgcm = AESGCM(key)

    ciphertext = aesgcm.encrypt(
        nonce,
        plaintext,
        associated_data
    )

    return {
        "algorithm": "AES-256-GCM",
        "nonce": base64.b64encode(
            nonce
        ).decode("utf-8"),

        "ciphertext": base64.b64encode(
            ciphertext
        ).decode("utf-8")
    }


# ---------------------------------------------------------------------------
# DECRYPTION
# ---------------------------------------------------------------------------

def decrypt_data(
    encrypted_payload: dict,
    key: bytes,
    associated_data: bytes | None = None
) -> bytes:
    """
    Decrypt an AES-256-GCM encrypted payload.

    Raises:
        ValueError:
            If the payload is malformed or the key is invalid.

        InvalidTag:
            If the ciphertext has been modified or the wrong key
            is supplied.
    """

    if len(key) != KEY_SIZE_BYTES:
        raise ValueError(
            "AES-256 key must be exactly 32 bytes."
        )

    if encrypted_payload.get("algorithm") != "AES-256-GCM":
        raise ValueError(
            "Unsupported encryption algorithm."
        )

    try:

        nonce = base64.b64decode(
            encrypted_payload["nonce"],
            validate=True
        )

        ciphertext = base64.b64decode(
            encrypted_payload["ciphertext"],
            validate=True
        )

    except (KeyError, ValueError) as e:

        raise ValueError(
            "Malformed encrypted payload."
        ) from e

    if len(nonce) != NONCE_SIZE_BYTES:
        raise ValueError(
            "Invalid AES-GCM nonce size."
        )

    aesgcm = AESGCM(key)

    try:

        plaintext = aesgcm.decrypt(
            nonce,
            ciphertext,
            associated_data
        )

    except InvalidTag as e:

        raise InvalidTag(
            "AES-GCM authentication failed. "
            "The data may have been modified or "
            "the encryption key is incorrect."
        ) from e

    return plaintext


# ---------------------------------------------------------------------------
# JSON SESSION HELPERS
# ---------------------------------------------------------------------------

def encrypt_session(
    session: dict,
    key: bytes
) -> dict:
    """
    Encrypt a WorkGuard session dictionary.

    The session is serialized to UTF-8 JSON before encryption.
    """

    session_json = json.dumps(
        session,
        separators=(",", ":"),
        ensure_ascii=False
    )

    plaintext = session_json.encode(
        "utf-8"
    )

    # Session ID can be authenticated as associated data.
    #
    # It is NOT encrypted here because it will eventually be useful
    # to identify the encrypted package before decryption.
    session_id = session.get(
        "session_id",
        ""
    )

    associated_data = session_id.encode(
        "utf-8"
    )

    encrypted = encrypt_data(
        plaintext,
        key,
        associated_data=associated_data
    )

    encrypted["session_id"] = session_id

    return encrypted


def decrypt_session(
    encrypted_payload: dict,
    key: bytes
) -> dict:
    """
    Decrypt an encrypted WorkGuard session and return the
    original Python dictionary.
    """

    session_id = encrypted_payload.get(
        "session_id",
        ""
    )

    associated_data = session_id.encode(
        "utf-8"
    )

    plaintext = decrypt_data(
        encrypted_payload,
        key,
        associated_data=associated_data
    )

    try:

        session = json.loads(
            plaintext.decode("utf-8")
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError
    ) as e:

        raise ValueError(
            "Decrypted data is not valid JSON."
        ) from e

    return session