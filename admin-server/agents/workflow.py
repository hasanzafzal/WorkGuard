"""LangGraph orchestration for the WorkGuard AI pipeline."""

from datetime import datetime, timezone
from langgraph.graph import END, START, StateGraph

from agents.knowledge_agent import knowledge_agent
from agents.reporting_agent import reporting_agent
from agents.security_agent import security_agent
from agents.session_analysis_agent import session_analysis_agent
from agents.state import WorkGuardState
from agents.supervisor_agent import supervisor_agent
from database.repository import persist_report, mark_session_processed


def _route_after_supervisor(state: WorkGuardState) -> str:
    """Route to analysis or reporting based on session validity."""
    return "session_analysis" if state.get("session") else "reporting"


def build_workflow():
    """Build the LangGraph workflow for session analysis."""
    workflow = StateGraph(WorkGuardState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("session_analysis", session_analysis_agent)
    workflow.add_node("knowledge", knowledge_agent)
    workflow.add_node("security", security_agent)
    workflow.add_node("reporting", reporting_agent)
    
    # Add edges
    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "session_analysis": "session_analysis",
            "reporting": "reporting",
        },
    )
    workflow.add_edge("session_analysis", "knowledge")
    workflow.add_edge("knowledge", "security")
    workflow.add_edge("security", "reporting")
    workflow.add_edge("reporting", END)
    
    return workflow.compile()


def run_workflow(session: dict) -> dict:
    """
    Run the complete agent pipeline for one verified session.
    
    Returns the final report from all agents.
    """
    graph = build_workflow()
    
    result = graph.invoke(
        {
            "session_id": session.get("session_id", ""),
            "session": session,
            "errors": [],
        }
    )
    
    # Persist report to database
    try:
        if result.get("report"):
            persist_report(result["report"])
            mark_session_processed(session.get("session_id", ""))
    except Exception as e:
        print(f"Failed to persist report: {e}")
    
    return result
