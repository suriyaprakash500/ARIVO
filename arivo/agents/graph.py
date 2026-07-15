"""LangGraph StateGraph definition and compilation.

Builds the ARIVO multi-agent pipeline as a compiled LangGraph graph
with conditional edges and a supervisor-driven routing pattern.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from arivo.agents.state import ArivoState
from arivo.agents.supervisor import supervisor_node
from arivo.agents.qms_extraction import qms_extraction_node
from arivo.agents.regulatory_assessment import regulatory_assessment_node
from arivo.agents.dossier_structuring import dossier_structuring_node
from arivo.agents.pv_e2b import pv_e2b_node
from arivo.agents.critic import critic_node


def _route_from_supervisor(state: ArivoState) -> str:
    """Conditional edge: read the supervisor's routing decision."""
    next_agent = state.get("next_agent", "END")
    if next_agent == "END":
        return END
    return next_agent


def build_graph() -> StateGraph:
    """Build and compile the ARIVO LangGraph pipeline.

    Graph structure:
        supervisor → (conditional) → qms_extraction
                                   → regulatory_assessment
                                   → dossier_structuring
                                   → pv_e2b
                                   → critic
                                   → END

        qms_extraction → supervisor
        regulatory_assessment → supervisor
        dossier_structuring → supervisor
        pv_e2b → supervisor
        critic → supervisor
    """
    graph = StateGraph(ArivoState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("qms_extraction", qms_extraction_node)
    graph.add_node("regulatory_assessment", regulatory_assessment_node)
    graph.add_node("dossier_structuring", dossier_structuring_node)
    graph.add_node("pv_e2b", pv_e2b_node)
    graph.add_node("critic", critic_node)

    # Entry point
    graph.set_entry_point("supervisor")

    # Conditional routing from supervisor
    graph.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "qms_extraction": "qms_extraction",
            "regulatory_assessment": "regulatory_assessment",
            "dossier_structuring": "dossier_structuring",
            "pv_e2b": "pv_e2b",
            "critic": "critic",
            END: END,
        },
    )

    # All agents return to supervisor after execution
    graph.add_edge("qms_extraction", "supervisor")
    graph.add_edge("regulatory_assessment", "supervisor")
    graph.add_edge("dossier_structuring", "supervisor")
    graph.add_edge("pv_e2b", "supervisor")
    graph.add_edge("critic", "supervisor")

    return graph


# Singleton compiled graph with in-memory checkpointing
_checkpointer = MemorySaver()
compiled_graph = build_graph().compile(checkpointer=_checkpointer)
