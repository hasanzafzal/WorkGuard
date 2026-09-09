"""AES-256-GCM encryption/decryption for WorkGuard sessions."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


KEY_SIZE_BYTES = 32
NONCE_SIZE_BYTES = 12
ALGORITHM = "AES-256-GCM"


def key_from_base64(key_string: str) -> bytes:
    """Decode and validate a Base64-encoded AES-256 key."""

    if not isinstance(key_string, str):
        raise ValueError("AES key must be a string.")

    key_string = key_string.strip()

    if not key_string:
        raise ValueError("AES key is empty.")

    try:
        key = base64.b64decode(key_string, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("Invalid Base64 AES key.") from error

    if len(key) != KEY_SIZE_BYTES:
        raise ValueError(
            f"AES-256 key must decode to exactly "
            f"{KEY_SIZE_BYTES} bytes; got {len(key)} bytes."
        )

    return key


def decrypt_session(
    encrypted_payload: dict[str, Any],
    key: bytes,
) -> dict[str, Any]:
    """Authenticate and decrypt an encrypted WorkGuard session."""

    if not isinstance(key, bytes):
        raise ValueError("AES key must be bytes.")

    if len(key) != KEY_SIZE_BYTES:
        raise ValueError(
            f"AES-256 key must be exactly {KEY_SIZE_BYTES} bytes."
        )

    algorithm = encrypted_payload.get("algorithm")

    if algorithm != ALGORITHM:
        raise ValueError(
            f"Unsupported encryption algorithm: {algorithm!r}"
        )

    session_id = encrypted_payload.get("session_id")

    if not isinstance(session_id, str) or not session_id:
        raise ValueError("Missing session_id in encrypted payload.")

    nonce_b64 = encrypted_payload.get("nonce")
    ciphertext_b64 = encrypted_payload.get("ciphertext")

    if not isinstance(nonce_b64, str) or not nonce_b64:
        raise ValueError("Missing encrypted payload nonce.")

    if not isinstance(ciphertext_b64, str) or not ciphertext_b64:
        raise ValueError("Missing encrypted payload ciphertext.")

    try:
        nonce = base64.b64decode(nonce_b64, validate=True)
        ciphertext = base64.b64decode(
            ciphertext_b64,
            validate=True,
        )
    except (ValueError, binascii.Error) as error:
        raise ValueError(
            "Nonce or ciphertext is not valid Base64."
        ) from error

    if len(nonce) != NONCE_SIZE_BYTES:
        raise ValueError(
            f"AES-GCM nonce must be exactly "
            f"{NONCE_SIZE_BYTES} bytes; got {len(nonce)} bytes."
        )

    if len(ciphertext) < 16:
        raise ValueError(
            "AES-GCM ciphertext is too short."
        )

    aad = session_id.encode("utf-8")

    try:
        plaintext = AESGCM(key).decrypt(
            nonce,
            ciphertext,
            aad,
        )
    except InvalidTag as error:
        raise InvalidTag(
            "AES-GCM authentication failed. "
            "The AES key, session_id/AAD, nonce, or ciphertext "
            "does not match the values used during encryption."
        ) from error

    try:
        decoded = plaintext.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Decrypted payload is not valid UTF-8."
        ) from error

    try:
        session = json.loads(decoded)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Decrypted payload is not valid JSON."
        ) from error

    if not isinstance(session, dict):
        raise ValueError(
            "Decrypted session must be a JSON object."
        )

    return session
