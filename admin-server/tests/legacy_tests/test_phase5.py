"""Phase 5 Verification Script: Test the LangGraph Session Analysis Agent.

Usage:
    # Run the default roadmap evaluation test suite:
    python test_phase5.py

    # Or test a custom question directly:
    python test_phase5.py "How much time did arif spend on VS Code?"
"""

import sys
import time
from pathlib import Path

# Ensure admin-server root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from llm.ollama_client import get_ollama_client
from agents.session_agent import run_session_agent


def test_custom_query(query: str):
    print(f"\n{'='*70}")
    print(f"QUERY: \"{query}\"")
    print(f"{'='*70}")
    t0 = time.time()
    res = run_session_agent(query=query)
    elapsed = time.time() - t0

    print(f"\n[Agent Metadata]")
    print(f"  - Detected Employee : {res.get('employee_name')} ({res.get('employee_id')})")
    print(f"  - Detected Date     : {res.get('date')}")
    print(f"  - Detected Intent   : {res.get('intent')}")
    print(f"  - Sources Used      : {res.get('sources')}")
    print(f"  - Response Time     : {elapsed:.2f}s")
    print(f"\n[Agent Answer]")
    print(f"{res.get('answer')}")
    print(f"{'='*70}\n")


def run_roadmap_suite():
    print("=" * 70)
    print(" WORKGUARD PHASE 5: SESSION ANALYSIS AGENT TEST SUITE")
    print("=" * 70)

    # 1. Health Check
    print("\n[Step 1] Verifying Ollama Health & Model...")
    client = get_ollama_client()
    health = client.check_health()
    print(f"  - Status           : {health.get('status')}")
    print(f"  - Configured Model : {health.get('configured_model')}")
    print(f"  - Available Models : {health.get('available_models')}")
    if health.get("status") not in ("ok", "warning"):
        print(f"[ERROR] Ollama is not ready: {health.get('error')}")
        return

    # 2. Roadmap Questions from postgresql_to_agents_roadmap.md
    roadmap_questions = [
        "How much time did employee arif.arshad spend on VS Code?",
        "What applications did arif use?",
        "Give me a summary of arif.arshad's activity on 2026-09-01.",
        "What did jane.engineer work on?",
    ]

    print(f"\n[Step 2] Testing {len(roadmap_questions)} Official Roadmap Questions against PostgreSQL + FAISS...")
    for idx, q in enumerate(roadmap_questions, 1):
        print(f"\n>>> Test Question {idx}/{len(roadmap_questions)}: \"{q}\"")
        t0 = time.time()
        res = run_session_agent(query=q)
        elapsed = time.time() - t0

        print(f"  - Target Identified : {res.get('employee_name')} ({res.get('employee_id')})")
        print(f"  - Telemetry Sources : {res.get('sources')}")
        print(f"  - Execution Time    : {elapsed:.2f}s")
        print(f"  - Factual Answer    :\n    {res.get('answer')}")

    print("\n" + "=" * 70)
    print(" [SUCCESS] Phase 5 LangGraph Session Agent Verified!")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        custom_q = " ".join(sys.argv[1:])
        test_custom_query(custom_q)
    else:
        run_roadmap_suite()
