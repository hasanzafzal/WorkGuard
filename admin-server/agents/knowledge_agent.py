"""Knowledge Agent - retrieves and answers factual questions using stored data."""

import json
from agents.state import WorkGuardState
from tools.postgres_tools import list_employees, search_sessions_by_employee


def knowledge_agent(state: WorkGuardState) -> WorkGuardState:
    """
    Retrieve factual information from PostgreSQL and FAISS.
    
    Central question: "What does the system know about this?"
    
    The Knowledge Agent is retrieval-oriented and uses:
    - PostgreSQL for structured queries
    - FAISS for semantic similarity search
    """
    session = state.get("session", {})
    errors = state.get("errors", [])
    
    if not session:
        errors.append("Knowledge Agent received no session data.")
        return {
            "knowledge": {},
            "errors": errors,
            "workflow_stage": "security",
        }
    
    try:
        knowledge = {}
        
        employee_id = session.get("employee_id")
        session_id = session.get("session_id")
        
        # Retrieve employee context
        if employee_id:
            try:
                employee_sessions = search_sessions_by_employee(employee_id, limit=10)
                knowledge["employee_context"] = {
                    "employee_id": employee_id,
                    "total_sessions": len(employee_sessions),
                    "recent_sessions": [
                        {
                            "session_id": s.get("session_id"),
                            "start_time": str(s.get("start_time")),
                            "duration_seconds": s.get("duration_seconds"),
                        }
                        for s in employee_sessions[:3]
                    ],
                }
            except Exception as e:
                knowledge["employee_context"] = {
                    "error": f"Failed to retrieve employee context: {e}",
                }
        
        # Retrieve session-specific context
        knowledge["session_context"] = {
            "session_id": session_id,
            "employee_id": employee_id,
            "duration_seconds": session.get("session", {}).get("duration_seconds"),
            "focus_summary": session.get("focus_summary", {}),
        }
        
        # Add session metadata if available
        if session.get("metadata"):
            knowledge["session_metadata"] = session.get("metadata")
        
        return {
            "knowledge": knowledge,
            "workflow_stage": "security",
            "errors": errors,
        }
    
    except Exception as e:
        errors.append(f"Knowledge Agent error: {e}")
        return {
            "knowledge": {},
            "errors": errors,
            "workflow_stage": "security",
        }
