"""AES-256-GCM decryption for encrypted WorkGuard session packages."""

import base64
import json

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


KEY_SIZE_BYTES = 32
NONCE_SIZE_BYTES = 12


def key_from_base64(key_string: str) -> bytes:
    """Decode and validate a Base64-encoded AES-256 key."""
    try:
        key = base64.b64decode(key_string, validate=True)
    except Exception as error:
        raise ValueError("Invalid Base64 AES key.") from error

    if len(key) != KEY_SIZE_BYTES:
        raise ValueError("AES-256 key must decode to exactly 32 bytes.")

    return key


def decrypt_session(encrypted_payload: dict, key: bytes) -> dict:
    """Authenticate and decrypt a session encrypted by the employee client."""
    if len(key) != KEY_SIZE_BYTES:
        raise ValueError("AES-256 key must be exactly 32 bytes.")
    if encrypted_payload.get("algorithm") != "AES-256-GCM":
        raise ValueError("Unsupported encryption algorithm.")

    try:
        nonce = base64.b64decode(encrypted_payload["nonce"], validate=True)
        ciphertext = base64.b64decode(
            encrypted_payload["ciphertext"],
            validate=True,
        )
    except (KeyError, ValueError) as error:
        raise ValueError("Malformed encrypted payload.") from error

    if len(nonce) != NONCE_SIZE_BYTES:
        raise ValueError("Invalid AES-GCM nonce size.")

    session_id = encrypted_payload.get("session_id", "")
    try:
        plaintext = AESGCM(key).decrypt(
            nonce,
            ciphertext,
            session_id.encode("utf-8"),
        )
    except InvalidTag as error:
        raise InvalidTag(
            "AES-GCM authentication failed. The data may have been modified "
            "or the encryption key is incorrect."
        ) from error

    try:
        return json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Decrypted data is not valid JSON.") from error
