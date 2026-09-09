"""LangGraph node for factual, structured employee-session analysis."""

import json
import os

from ai.state import WorkGuardState

MODEL_NAME = os.getenv("WORKGUARD_OLLAMA_MODEL", "llama3:latest")


def _fallback_analysis(session: dict) -> dict:
    """Generate objective structured analysis when ChatOllama is unreachable."""
    duration = session.get("session", {}).get("duration_seconds", 0)
    events = session.get("events", [])
    apps = list({e.get("app_name") for e in events if isinstance(e, dict) and e.get("app_name")})
    focus = session.get("focus_summary", {})
    
    productivity = "productive"
    if duration < 60 and len(events) < 5:
        productivity = "unclear"
    elif any("game" in str(a).lower() or "video" in str(a).lower() for a in apps):
        productivity = "mixed"

    return {
        "summary": f"Session duration {duration}s across {len(events)} events with {len(apps)} distinct applications.",
        "productivity_assessment": productivity,
        "key_activities": [f"Active in: {', '.join(apps[:4])}"] if apps else ["Standard workstation tasks"],
        "focus_observations": [f"Focus score recorded: {focus.get('score', 'normal')}"] if focus else ["Consistent focus pattern observed"],
        "recommended_follow_up": ["Routine review" if productivity == "productive" else "Verify activity window breakdown"]
    }


def session_analysis_agent(state: WorkGuardState) -> WorkGuardState:
    """Analyze one verified session and return a LangGraph state update."""
    session = state.get("session")

    if not session:
        return {
            "errors": state.get("errors", [])
            + ["Session Analysis Agent received no session data."],
        }

    prompt = f"""
You are WorkGuard's Session Analysis Agent.

Analyze this verified employee activity session and return JSON only. Do not
invent facts; use only the supplied session data.

Return this exact JSON structure:
{{
  "summary": "short factual summary",
  "productivity_assessment": "productive, mixed, or unclear",
  "key_activities": ["activity"],
  "focus_observations": ["observation"],
  "recommended_follow_up": ["recommendation"]
}}

Verified session:
{json.dumps(session, ensure_ascii=False)}
"""

    try:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=MODEL_NAME,
            temperature=0,
            format="json",
        )
        response = llm.invoke(prompt)
        analysis = json.loads(response.content)
    except Exception as error:
        # Gracefully degrade to rule-based factual analysis so workflow completes
        analysis = _fallback_analysis(session)
        return {
            "session_analysis": analysis,
            "errors": state.get("errors", [])
            + [f"Session Analysis Agent used fallback (LLM note: {error})"],
        }

    return {"session_analysis": analysis}

