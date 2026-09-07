"""Verification Test Suite for Phase 9: Admin Chat API.

Verifies:
1. GET /api/v1/chat/status (Agent status, Ollama health, PostgreSQL connectivity)
2. GET /api/v1/chat/suggestions (Dynamic starter prompts based on registered workforce)
3. POST /api/v1/chat (Single-turn inquiry routing via Supervisor Agent)
4. POST /api/v1/chat (Multi-turn conversational context inheritance across turns)
5. Structured response envelope (answer, citations, routed_agent, routing_reason, suggested_followups)
"""

import os
import sys
import time
from pathlib import Path
from threading import Thread
import requests

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure admin-server root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

BASE_URL = "http://localhost:8000"


def ensure_server_running(base_url: str = BASE_URL) -> None:
    """Ensure the admin server is running. If not, auto-start uvicorn in a daemon thread."""
    try:
        resp = requests.get(f"{base_url}/health", timeout=1)
        if resp.status_code == 200:
            print(f"[INFO] Detected running server at {base_url}.")
            return
    except requests.RequestException:
        pass

    print(f"[INFO] Server not running at {base_url}. Starting in background thread...")
    import uvicorn
    from main import app

    def _start():
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

    server_thread = Thread(target=_start, daemon=True)
    server_thread.start()

    # Poll until ready
    max_wait = 15
    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            resp = requests.get(f"{base_url}/health", timeout=1)
            if resp.status_code == 200:
                print(f"[INFO] Server ready at {base_url}!")
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)

    print("[WARN] Server did not report healthy within timeout; continuing tests anyway...")


def test_phase9_chat_api():
    ensure_server_running(BASE_URL)

    print("\n" + "=" * 75)
    print(" [PHASE 9] TESTING ADMIN CHAT API")
    print("=" * 75)

    # 1. Test Chat Status Endpoint
    print("\n--- 1. Testing GET /api/v1/chat/status ---")
    resp_status = requests.get(f"{BASE_URL}/api/v1/chat/status", timeout=10)
    assert resp_status.status_code == 200, f"Status error: {resp_status.status_code}"
    status_data = resp_status.json()
    print("System Status:", status_data.get("status"))
    print("Supervisor:", status_data.get("supervisor"))
    print("Agents:", status_data.get("agents"))
    print("Database:", status_data.get("database"))
    assert status_data.get("status") in ("ready", "ok"), "Chat system should be ready"
    assert status_data.get("database", {}).get("status") == "connected"
    print("[PASS] Chat system status verified!")

    # 2. Test Chat Suggestions Endpoint
    print("\n--- 2. Testing GET /api/v1/chat/suggestions ---")
    resp_sugg = requests.get(f"{BASE_URL}/api/v1/chat/suggestions", timeout=10)
    assert resp_sugg.status_code == 200, f"Suggestions error: {resp_sugg.status_code}"
    sugg_data = resp_sugg.json()
    suggestions = sugg_data.get("suggestions", [])
    registered = sugg_data.get("registered_employees", [])
    print(f"Registered Employees: {registered}")
    print("Sample Suggestions:")
    for s in suggestions[:4]:
        print(f"  * {s}")
    assert len(suggestions) >= 4, "Expected at least 4 suggestions"
    assert len(registered) > 0, "Expected registered employees in suggestions"
    print("[PASS] Chat suggestions verified!")

    # 3. Test Single-Turn Session Query
    print("\n--- 3. Testing POST /api/v1/chat (Session Query) ---")
    q1 = "How much time did arif spend on VS Code?"
    print(f"Prompt: \"{q1}\"")
    t0 = time.time()
    resp_chat1 = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={"message": q1, "conversation_history": []},
        timeout=180,
    )
    assert resp_chat1.status_code == 200, f"Chat error: {resp_chat1.status_code}"
    data1 = resp_chat1.json()
    elapsed1 = time.time() - t0
    print(f"Routed Agent: {data1.get('routed_agent')} (Reason: {data1.get('routing_reason')})")
    print(f"Employee ID: {data1.get('employee_id')}")
    print(f"Citations: {data1.get('citations')}")
    print(f"Suggested Follow-ups: {data1.get('suggested_followups')}")
    print(f"Response Time: {elapsed1:.2f}s")
    print(f"Answer Preview:\n{data1.get('answer')[:300]}...")
    assert data1.get("routed_agent") == "session", "Expected session agent routing"
    assert len(data1.get("suggested_followups", [])) >= 2, "Expected follow-up suggestions"
    print("[PASS] Single-turn session inquiry verified!")

    # 4. Test Multi-Turn Conversational Context Inheritance
    print("\n--- 4. Testing POST /api/v1/chat (Multi-turn Context Inheritance) ---")
    # In turn 2, the user does NOT say "arif". They say "Was that activity suspicious?"
    q2 = "Was that activity suspicious?"
    print(f"Turn 2 Prompt: \"{q2}\" (no employee name explicitly mentioned)")
    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": data1.get("answer", "")},
    ]
    t0 = time.time()
    resp_chat2 = requests.post(
        f"{BASE_URL}/api/v1/chat",
        json={"message": q2, "conversation_history": history},
        timeout=180,
    )
    assert resp_chat2.status_code == 200, f"Chat follow-up error: {resp_chat2.status_code}"
    data2 = resp_chat2.json()
    elapsed2 = time.time() - t0
    print(f"Routed Agent: {data2.get('routed_agent')}")
    print(f"Inherited Employee Target: {data2.get('employee_name')} ({data2.get('employee_id')})")
    print(f"Citations: {data2.get('citations')}")
    print(f"Suggested Follow-ups: {data2.get('suggested_followups')}")
    print(f"Response Time: {elapsed2:.2f}s")
    print(f"Answer Preview:\n{data2.get('answer')[:300]}...")
    assert data2.get("routed_agent") == "security", "Expected security agent routing for suspicion inquiry"
    assert "arif" in (data2.get("employee_name", "").lower() or data2.get("answer", "").lower()), (
        "Expected context inheritance to resolve arif as target"
    )
    print("[PASS] Multi-turn conversational context inheritance verified!")

    print("\n" + "=" * 75)
    print(" [PHASE 9 ADMIN CHAT API TEST SUITE PASSED SUCCESSFULLY!]")
    print("=" * 75)


if __name__ == "__main__":
    test_phase9_chat_api()
