"""Verification Test Suite for Phases 6, 7, and 8.

Covers:
- Phase 6: Supervisor Agent (Routing & Orchestration)
- Phase 7: Security Intelligence Agent (Deterministic Rules + Ollama Explanation)
- Phase 8: Reporting Agent (Structured Metrics Synthesis into Executive Report)
- REST API Endpoints & Chat Integration
"""

import sys
import time
from pathlib import Path

# Ensure admin-server root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.security_agent import run_security_agent
from agents.reporting_agent import run_reporting_agent
from agents.supervisor_agent import run_supervisor_agent, classify_intent
from security.rules import evaluate_security_telemetry


def test_phase7_security_agent():
    print("\n" + "=" * 75)
    print(" [PHASE 7] TESTING SECURITY INTELLIGENCE AGENT")
    print("=" * 75)

    # 1. Deterministic rules evaluation directly
    print("\n--- 1. Deterministic Rule Evaluation in PostgreSQL ---")
    eval_arif = evaluate_security_telemetry(employee_id="SYS-B56B4DEB06F6")
    print(f"Target: {eval_arif['target'].get('employee_name')} ({eval_arif['target'].get('employee_id')})")
    print(f"Risk Score: {eval_arif['risk_score']}/100 | Risk Level: {eval_arif['risk_level']}")
    print(f"Total Findings Detected: {eval_arif['total_findings']}")
    for f in eval_arif["findings"]:
        print(f"  * [{f['severity']}] {f['rule']}: {f['description']}")
    assert eval_arif["risk_score"] > 0, "Expected non-zero risk score for after-hours/burst activity"

    # 2. End-to-end Security Agent execution
    print("\n--- 2. End-to-End Security Agent Execution (Rules + Ollama) ---")
    q = "Was arif's activity suspicious?"
    print(f"Question: \"{q}\"")
    t0 = time.time()
    res = run_security_agent(query=q)
    elapsed = time.time() - t0
    print(f"Detected Target: {res.get('employee_name')} ({res.get('employee_id')})")
    print(f"Risk Level: {res.get('risk_level')} | Risk Score: {res.get('risk_score')}")
    print(f"Findings Count: {res.get('total_findings')}")
    print(f"Execution Time: {elapsed:.2f}s")
    print(f"\nForensic Explanation:\n{res.get('answer')}")
    assert len(res.get("answer", "")) > 40, "Expected substantive security explanation"
    assert res.get("risk_score") == eval_arif["risk_score"], "Agent score must match deterministic score"
    print("\n[SUCCESS] Phase 7 Security Intelligence Agent verified!")


def test_phase8_reporting_agent():
    print("\n" + "=" * 75)
    print(" [PHASE 8] TESTING REPORTING AGENT")
    print("=" * 75)

    q = "Generate an activity report for arif.arshad."
    print(f"Request: \"{q}\"")
    t0 = time.time()
    res = run_reporting_agent(query=q)
    elapsed = time.time() - t0

    print(f"Target: {res.get('employee_name')} ({res.get('employee_id')})")
    print(f"Scope: {res.get('scope')}")
    print(f"Sources Used: {res.get('sources')}")
    print(f"Execution Time: {elapsed:.2f}s")
    print(f"\nGenerated Report Preview:\n{res.get('answer')[:500]}...\n")
    assert len(res.get("answer", "")) > 100, "Report output too short!"
    assert "arif" in res.get("answer", "").lower() or "ailab" in res.get("answer", "").lower()
    print("\n[SUCCESS] Phase 8 Reporting Agent verified!")


def test_phase6_supervisor_agent():
    print("\n" + "=" * 75)
    print(" [PHASE 6] TESTING SUPERVISOR AGENT")
    print("=" * 75)

    # 1. Official Roadmap Routing Matrix Check
    print("\n--- 1. Roadmap Routing Matrix Evaluation ---")
    roadmap_matrix = [
        ("What does our policy say?", "knowledge"),
        ("What did Alice do yesterday?", "session"),
        ("Was Alice's activity suspicious?", "security"),
        ("Generate weekly activity report", "reporting"),
    ]

    for question, expected_agent in roadmap_matrix:
        agent, reason, conf = classify_intent(question)
        print(f"Query: \"{question}\"")
        print(f"  -> Dispatched Agent : {agent} (Expected: {expected_agent}) | Confidence: {conf:.2f}")
        assert agent == expected_agent, f"Routing mismatch! Expected {expected_agent}, got {agent}"

    # 2. Live Supervisor End-to-End Routing Execution
    print("\n--- 2. Live Supervisor Execution (Routing to Security Agent) ---")
    q_sec = "Was arif's activity suspicious?"
    t0 = time.time()
    res_sup = run_supervisor_agent(query=q_sec)
    elapsed = time.time() - t0
    print(f"Query: \"{q_sec}\"")
    print(f"Routed Agent: {res_sup.get('routed_agent')}")
    print(f"Routing Reason: {res_sup.get('routing_reason')}")
    print(f"Sources: {res_sup.get('sources')}")
    print(f"Execution Time: {elapsed:.2f}s")
    print(f"Answer Preview: {res_sup.get('answer')[:250]}...")
    assert res_sup.get("routed_agent") == "security"
    assert len(res_sup.get("answer", "")) > 40

    print("\n[SUCCESS] Phase 6 Supervisor Agent verified!")


if __name__ == "__main__":
    test_phase7_security_agent()
    test_phase8_reporting_agent()
    test_phase6_supervisor_agent()
    print("\n" + "=" * 75)
    print(" [ALL PHASES 6, 7, 8 TESTS PASSED SUCCESSFULLY!]")
    print("=" * 75)
