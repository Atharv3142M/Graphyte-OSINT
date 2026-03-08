"""
Scoped tools for the Analyzer Agent only.
Zero-trust: Analyzer may only call these (GraySentinel semantic + threat scoring).
"""
from __future__ import annotations

from typing import Any, Callable

ANALYZER_TOOL_NAMES = {"semantic_search", "graysentinel_ingest", "score_threat"}


def semantic_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Natural-language semantic search over ingested docs. Analyzer-only."""
    try:
        from semantic_search import search
        results = search(query, limit=limit)
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


def graysentinel_ingest(urls: list[str], strategies: list[str] | None = None) -> dict[str, Any]:
    """Ingest URLs via GraySentinel pipeline. Analyzer-only."""
    from modules.graysentinel_pipeline import run_pipeline
    return run_pipeline(urls, strategies)


def score_threat(
    findings: list[dict[str, Any]],
    semantic_anomalies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score threat risk from findings and semantic anomalies. Analyzer-only."""
    score = 0.0
    reasons = []
    for f in findings or []:
        if f.get("error") or not f.get("success", True):
            continue
        data = f.get("data") or f.get("results") or f
        if isinstance(data, dict):
            if data.get("ports"):
                score += 0.2 * min(len(data.get("ports", [])), 5)
            if data.get("matches"):
                score += 0.1 * min(len(data.get("matches", [])), 10)
        if isinstance(data, list):
            score += 0.05 * min(len(data), 20)
    for a in semantic_anomalies or []:
        score += 0.15
        reasons.append(a.get("content", str(a))[:200])
    score = min(1.0, score)
    return {"success": True, "threat_score": round(score, 3), "reasons": reasons[:10]}


def get_analyzer_tools() -> dict[str, Callable[..., Any]]:
    """Return only the tools the Analyzer agent is allowed to use (zero-trust)."""
    return {
        "semantic_search": semantic_search,
        "graysentinel_ingest": graysentinel_ingest,
        "score_threat": score_threat,
    }
