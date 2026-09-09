"""LangGraph orchestration for the WorkGuard Week 2 AI pipeline."""

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:
    END = START = StateGraph = None

from ai.knowledge_agent import knowledge_agent
from ai.reporting_agent import reporting_agent
from ai.security_agent import security_agent
from ai.session_analysis_agent import session_analysis_agent
from ai.state import WorkGuardState
from ai.supervisor_agent import supervisor_agent


def _route_after_supervisor(state: WorkGuardState) -> str:
    """Skip analysis nodes when the supervisor has no valid session."""
    return "session_analysis" if state.get("session") else "reporting"


def build_workflow():
    """Build the fixed, supervised local agent workflow."""
    if StateGraph is None:
        raise ImportError("langgraph package is not available in current environment")
    workflow = StateGraph(WorkGuardState)

    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("session_analysis", session_analysis_agent)
    workflow.add_node("knowledge", knowledge_agent)
    workflow.add_node("security", security_agent)
    workflow.add_node("reporting", reporting_agent)

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
    """Run the supervised agent pipeline for one verified session."""
    try:
        graph = build_workflow()
        return graph.invoke(
            {
                "session_id": session.get("session_id", ""),
                "session": session,
                "errors": [],
            }
        )
    except Exception as error:
        # Deterministic sequential fallback when LangGraph engine is unavailable
        initial_state = {
            "session_id": session.get("session_id", ""),
            "session": session,
            "errors": [f"LangGraph fallback activated: {error}"],
        }
        state = {**initial_state, **supervisor_agent(initial_state)}
        if state.get("session"):
            state = {**state, **session_analysis_agent(state)}
            state = {**state, **knowledge_agent(state)}
            state = {**state, **security_agent(state)}
        state = {**state, **reporting_agent(state)}
        return state

