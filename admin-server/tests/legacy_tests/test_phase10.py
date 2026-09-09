"""Verification Test Suite for Phase 10: Dashboard Integration.

Verifies all backend endpoints consumed by the Phase 10 Admin Dashboard:
1. GET /api/v1/chat/status (Dashboard & SystemStatus: Agent status, Ollama, PostgreSQL)
2. GET /api/v1/processing/status (SystemStatus: Pipeline stats & recent jobs)
3. GET /api/v1/vectors/stats (SystemStatus: FAISS vectors & indexed sessions)
4. GET /api/v1/llm/health (SystemStatus: LLM connectivity & models)
5. POST /api/v1/agents/session-analysis (EmployeeDetails: On-demand session agent)
6. POST /api/v1/agents/security (Security & EmployeeDetails: On-demand security agent)
7. POST /api/v1/agents/reporting (Reports: On-demand report generation agent)
8. POST /api/v1/agents/supervisor (Quick Chat / Supervisor orchestration)
"""

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

    max_wait = 15
    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            resp = requests.get(f"{base_url}/health", timeout=1)
            if resp.status_code == 200:
                print(f"[INFO] Server successfully started and healthy at {base_url}.")
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)

    raise RuntimeError(f"Server failed to become healthy within {max_wait} seconds.")


def test_system_observability():
    print("\n--- 1. Testing Observability Endpoints (SystemStatus & Dashboard) ---")
    
    # 1. Chat Status
    r = requests.get(f"{BASE_URL}/api/v1/chat/status", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    print(f"[PASS] GET /api/v1/chat/status: status={data.get('status')}, agents={list(data.get('agents', {}).keys())}")
    
    # 2. Processing Status
    r = requests.get(f"{BASE_URL}/api/v1/processing/status", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    p_data = r.json()
    stats = p_data.get("stats", {})
    print(f"[PASS] GET /api/v1/processing/status: completed={stats.get('completed')}, pending={stats.get('pending')}")
    
    # 3. Vectors Stats
    r = requests.get(f"{BASE_URL}/api/v1/vectors/stats", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    v_data = r.json()
    print(f"[PASS] GET /api/v1/vectors/stats: faiss_total_vectors={v_data.get('faiss_total_vectors')}, indexed_sessions={v_data.get('indexed_sessions_count')}")

    # 4. LLM Health
    r = requests.get(f"{BASE_URL}/api/v1/llm/health", timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    l_data = r.json()
    print(f"[PASS] GET /api/v1/llm/health: status={l_data.get('status')}, configured_model={l_data.get('configured_model')}")


def test_agent_endpoints():
    print("\n--- 2. Testing Direct Agent Endpoints (Security, EmployeeDetails, Reports) ---")
    
    # 1. Session Agent
    payload = {"query": "What did employee emp-001 do?", "employee_id": "emp-001"}
    r = requests.post(f"{BASE_URL}/api/v1/agents/session-analysis", json=payload, timeout=60)
    assert r.status_code == 200, f"Session agent failed: {r.status_code} {r.text}"
    resp = r.json()
    assert "answer" in resp, "Missing answer in response"
    print(f"[PASS] POST /api/v1/agents/session-analysis: answer snippet='{resp['answer'][:80]}...'")

    # 2. Security Agent
    payload = {"query": "Check security risks for emp-001", "employee_id": "emp-001"}
    r = requests.post(f"{BASE_URL}/api/v1/agents/security", json=payload, timeout=60)
    assert r.status_code == 200, f"Security agent failed: {r.status_code} {r.text}"
    resp = r.json()
    assert "answer" in resp, "Missing answer in response"
    print(f"[PASS] POST /api/v1/agents/security: risk_level={resp.get('risk_level')}, score={resp.get('risk_score')}")

    # 3. Reporting Agent
    payload = {"query": "Generate summary report", "employee_id": "emp-001"}
    r = requests.post(f"{BASE_URL}/api/v1/agents/reporting", json=payload, timeout=60)
    assert r.status_code == 200, f"Reporting agent failed: {r.status_code} {r.text}"
    resp = r.json()
    assert "answer" in resp, "Missing answer in response"
    print(f"[PASS] POST /api/v1/agents/reporting: scope={resp.get('scope')}, answer snippet='{resp['answer'][:80]}...'")

    # 4. Supervisor Agent
    payload = {"query": "Give me an overview of all workforce activity"}
    r = requests.post(f"{BASE_URL}/api/v1/agents/supervisor", json=payload, timeout=60)
    assert r.status_code == 200, f"Supervisor agent failed: {r.status_code} {r.text}"
    resp = r.json()
    assert "answer" in resp, "Missing answer in response"
    print(f"[PASS] POST /api/v1/agents/supervisor: routed_agent={resp.get('routed_agent')}")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 10: Backend API Verification for Dashboard Integration")
    print("=" * 60)

    ensure_server_running()
    test_system_observability()
    test_agent_endpoints()

    print("\n" + "=" * 60)
    print("ALL PHASE 10 BACKEND INTEGRATION APIS VERIFIED SUCCESSFULLY!")
    print("=" * 60)
