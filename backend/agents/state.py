"""
Shared state and memory schema for the OSINT multi-agent graph.
State is checkpointed so agents maintain context across multi-step investigation chains.
"""
from __future__ import annotations

from typing import Any, TypedDict


class OSINTAgentState(TypedDict, total=False):
    """State passed through the LangGraph. All keys optional for incremental updates."""

    # Goal and control
    goal: str
    next_agent: str | None

    # Per-agent results (scoped; only that agent writes its key)
    searcher_result: dict[str, Any]
    analyzer_result: dict[str, Any]
    pentester_result: dict[str, Any]
    orchestrator_summary: dict[str, Any]

    # Accumulated findings for STIX and reporting
    discovered_ips: list[str]
    threat_score: float
    stix_bundle: dict[str, Any] | None

    # Memory: messages and investigation context (nodes append by returning updated list)
    messages: list[dict[str, Any]]
    investigation_context: list[dict[str, Any]]
