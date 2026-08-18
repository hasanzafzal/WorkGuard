"""Local WorkGuard Admin Server.

This local server authenticates, decrypts, validates, and persists employee
session packages. It deliberately does not perform AI analysis yet.
"""

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from cryptography.exceptions import InvalidTag
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from security.encryption import decrypt_session, key_from_base64


BASE_DIR = Path(__file__).resolve().parent
RECEIVED_SESSIONS_DIR = BASE_DIR / "received_sessions"
VERIFIED_SESSIONS_DIR = BASE_DIR / "verified_sessions"

app = FastAPI(title="WorkGuard Admin Server")


class EncryptionPayload(BaseModel):
    """AES-GCM fields supplied by an employee client."""

    # Preserve the encryption helper's embedded session_id along with any
    # future authenticated-encryption metadata.
    model_config = ConfigDict(extra="allow")

    algorithm: Literal["AES-256-GCM"]
    nonce: str = Field(min_length=1)
    ciphertext: str = Field(min_length=1)


class SessionTransmission(BaseModel):
    """Envelope sent by an employee client before Admin-side decryption."""

    session_id: str = Field(min_length=1)
    employee_id: str = Field(min_length=1)
    created_at: str = Field(min_length=1)
    encryption: EncryptionPayload


class ReceiveResponse(BaseModel):
    status: Literal["received"]
    session_id: str
    received_at: str


@app.get("/health")
def health() -> dict[str, str]:
    """Report whether the local Admin server is available."""

    return {
        "status": "online",
        "server": "WorkGuard Admin Server",
    }


def get_shared_key() -> bytes:
    """Load the manually provisioned Admin/employee shared key."""
    encoded_key = os.getenv("WORKGUARD_AES_KEY_BASE64")
    if not encoded_key:
        raise HTTPException(
            status_code=503,
            detail="Admin encryption key is not configured.",
        )

    try:
        return key_from_base64(encoded_key)
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail="Admin encryption key is invalid.",
        ) from error


def validate_decrypted_session(session: dict, payload: SessionTransmission) -> None:
    """Check the minimal session contract before acknowledging delivery."""
    required_fields = ("session_id", "employee_id", "metadata")
    if any(not session.get(field) for field in required_fields):
        raise HTTPException(
            status_code=422,
            detail="Decrypted session is missing required fields.",
        )

    if not isinstance(session["metadata"], dict) or not session["metadata"].get(
        "created_at"
    ):
        raise HTTPException(
            status_code=422,
            detail="Decrypted session metadata.created_at is required.",
        )

    if session["session_id"] != payload.session_id:
        raise HTTPException(
            status_code=422,
            detail="Envelope and decrypted session IDs do not match.",
        )

    if session["employee_id"] != payload.employee_id:
        raise HTTPException(
            status_code=422,
            detail="Envelope and decrypted employee IDs do not match.",
        )


def save_json(directory: Path, filename: str, data: dict) -> None:
    """Atomically persist JSON so interrupted writes are never accepted."""
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / filename

    file_descriptor, temporary_path = tempfile.mkstemp(
        dir=directory,
        prefix=".incoming_",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, destination)
    except OSError:
        try:
            os.unlink(temporary_path)
        except FileNotFoundError:
            pass
        raise


@app.post("/api/v1/sessions", response_model=ReceiveResponse, status_code=201)
def receive_session(payload: SessionTransmission) -> ReceiveResponse:
    """Verify and persist one encrypted employee session package."""

    try:
        decrypted_session = decrypt_session(
            payload.encryption.model_dump(),
            get_shared_key(),
        )
    except (InvalidTag, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail="Encrypted session could not be authenticated and decrypted.",
        ) from error

    validate_decrypted_session(decrypted_session, payload)

    received_at = datetime.now(timezone.utc).isoformat()
    saved_payload = {
        **payload.model_dump(),
        "received_at": received_at,
    }
    saved_verified_session = {
        "session_id": payload.session_id,
        "employee_id": payload.employee_id,
        "received_at": received_at,
        "session": decrypted_session,
    }
    filename = f"{uuid.uuid4().hex}.json"

    save_json(RECEIVED_SESSIONS_DIR, filename, saved_payload)
    save_json(VERIFIED_SESSIONS_DIR, filename, saved_verified_session)

    return ReceiveResponse(
        status="received",
        session_id=payload.session_id,
        received_at=received_at,
    )
