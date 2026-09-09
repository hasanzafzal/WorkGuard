"""Session Analysis Agent - determines what happened during a session."""

import json
import os
from datetime import datetime, timezone

from langchain_ollama import ChatOllama

from agents.state import WorkGuardState


MODEL_NAME = os.getenv("WORKGUARD_OLLAMA_MODEL", "llama2:latest")


def session_analysis_agent(state: WorkGuardState) -> WorkGuardState:
    """
    Analyze one verified session and return structured findings.
    
    Central question: "What happened?"
    """
    session = state.get("session")
    errors = state.get("errors", [])
    
    if not session:
        errors.append("Session Analysis Agent received no session data.")
        return {"errors": errors}
    
    try:
        prompt = f"""You are WorkGuard's Session Analysis Agent.

Analyze this verified employee activity session and return JSON only. Do not
invent facts; use only the supplied session data.

Return this exact JSON structure:
{{
  "summary": "short factual summary of what the employee did",
  "productivity_assessment": "productive, mixed, or unclear",
  "key_activities": ["list", "of", "key", "activities"],
  "focus_observations": ["list", "of", "observations"],
  "recommended_follow_up": ["list", "of", "recommendations"]
}}

Verified session:
{json.dumps(session, ensure_ascii=False, default=str)}
"""

        llm = ChatOllama(
            model=MODEL_NAME,
            temperature=0.1,
            format="json",
        )
        response = llm.invoke(prompt)
        
        try:
            analysis = json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            content = response.content.strip()
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                analysis = json.loads(content[start:end+1])
            else:
                analysis = {
                    "summary": "Unable to parse analysis",
                    "productivity_assessment": "unclear",
                    "key_activities": [],
                    "focus_observations": [],
                    "recommended_follow_up": [],
                }
        
        return {
            "session_analysis": analysis,
            "workflow_stage": "knowledge",
        }
    
    except Exception as e:
        errors.append(f"Session Analysis Agent error: {e}")
        return {
            "session_analysis": {
                "summary": "Analysis failed",
                "productivity_assessment": "unclear",
                "key_activities": [],
                "focus_observations": [],
                "recommended_follow_up": [],
            },
            "errors": errors,
            "workflow_stage": "knowledge",
        }
