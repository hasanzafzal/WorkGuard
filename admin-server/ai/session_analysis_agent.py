"""LangGraph node for factual, structured employee-session analysis."""

import json
import os

from langchain_ollama import ChatOllama

from ai.state import WorkGuardState


MODEL_NAME = os.getenv("WORKGUARD_OLLAMA_MODEL", "llama3:latest")


def session_analysis_agent(state: WorkGuardState) -> dict:
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
        llm = ChatOllama(
            model=MODEL_NAME,
            temperature=0,
            format="json",
        )
        response = llm.invoke(prompt)
        analysis = json.loads(response.content)
    except Exception as error:
        return {
            "errors": state.get("errors", [])
            + [f"Session Analysis Agent failed: {error}"],
        }

    return {"session_analysis": analysis}
