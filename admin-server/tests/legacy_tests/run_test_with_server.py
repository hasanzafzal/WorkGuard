#!/usr/bin/env python3
"""Run the admin server and test encrypted session ingestion end-to-end."""

import os
import sys
import json
import base64
import time
from pathlib import Path
from threading import Thread

# Add admin-server to path
sys.path.insert(0, str(Path(__file__).parent))

# Start uvicorn in background thread
def start_server():
    import uvicorn
    from main import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="critical")

print("Starting admin server in background...")
server_thread = Thread(target=start_server, daemon=True)
server_thread.start()

# Wait for server to boot
time.sleep(4)

print("Server started. Running test...\n")

# Now run the test
from dotenv import load_dotenv
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

load_dotenv(Path(__file__).resolve().parent / ".env")
key = base64.b64decode(os.environ["WORKGUARD_AES_KEY_BASE64"])

session = {
  "session_id": "sess_test_001",
  "employee_id": "emp_001",
  "employee_name": "Alice Johnson",
  "session": {
    "start_time": "2026-08-20T20:44:27.109838+00:00",
    "end_time": "2026-08-20T20:46:36.814551+00:00",
    "duration_seconds": 129
  },
  "events": [],
  "focus_summary": {
    "Code.exe": 31.0,
  },
  "metadata": {
    "schema_version": "1.0",
    "created_at": "2026-08-20T20:46:41.838820+00:00"
  }
}

nonce = os.urandom(12)
ciphertext = AESGCM(key).encrypt(
    nonce,
    json.dumps(session, separators=(",", ":")).encode("utf-8"),
    session["session_id"].encode("utf-8"),
)

payload = {
    "session_id": "sess_test_001",
    "employee_id": "emp_001",
    "created_at": "2026-08-31T09:00:00Z",
    "encryption": {
        "algorithm": "AES-256-GCM",
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
    }
}

try:
    print(f"Sending encrypted session to http://localhost:8000/api/v1/sessions")
    resp = requests.post("http://localhost:8000/api/v1/sessions", json=payload, timeout=30)
    print(f"HTTP Status: {resp.status_code}")
    print(f"Response body:\n{resp.text}\n")
    
    if resp.status_code in [200, 201]:
        print("✅ SUCCESS: Session accepted!")
        print(json.dumps(resp.json(), indent=2))
    else:
        print(f"❌ FAILED: Expected 201, got {resp.status_code}")
        
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
