"""
LangGraph stateful graph for multi-agent OSINT orchestration.
Orchestrator -> Searcher | Analyzer | Pentester -> back to Orchestrator; checkpoint memory.
"""
from __future__ import annotations

from typing import Literal

from langgraph.graph import END, START, StateGraph
try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    from langgraph.checkpoint.memory import InMemorySaver as MemorySaver

from backend.agents.state import OSINTAgentState
from backend.agents.nodes import orchestrator_node, searcher_node, analyzer_node, pentester_node


def _route_orchestrator(state: OSINTAgentState) -> Literal["searcher", "analyzer", "pentester", "__end__"]:
    """Route from Orchestrator to next agent or end."""
    next_agent = state.get("next_agent") or "__end__"
    if next_agent in ("searcher", "analyzer", "pentester"):
        return next_agent
    return "__end__"


def build_osint_graph(use_memory: bool = True):
    """
    Build and compile the OSINT multi-agent graph with optional checkpoint memory.
    use_memory=True enables persistent state across multi-step investigation chains.
    """
    builder = StateGraph(OSINTAgentState)

    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("searcher", searcher_node)
    builder.add_node("analyzer", analyzer_node)
    builder.add_node("pentester", pentester_node)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        _route_orchestrator,
        {
            "searcher": "searcher",
            "analyzer": "analyzer",
            "pentester": "pentester",
            "__end__": END,
        },
    )
    builder.add_edge("searcher", "orchestrator")
    builder.add_edge("analyzer", "orchestrator")
    builder.add_edge("pentester", "orchestrator")

    checkpointer = MemorySaver() if use_memory else None
    return builder.compile(checkpointer=checkpointer)
