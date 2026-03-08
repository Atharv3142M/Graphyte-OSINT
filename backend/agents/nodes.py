"""
Agent nodes: Searcher, Analyzer, Pentester, Orchestrator.
Each node has access only to its scoped tools (zero-trust).
"""
from __future__ import annotations

from typing import Any

from agents.state import OSINTAgentState
from agents.tools.searcher_tools import get_searcher_tools
from agents.tools.analyzer_tools import get_analyzer_tools
from agents.tools.pentester_tools import get_pentester_tools


def _ctx(state: OSINTAgentState) -> list[dict[str, Any]]:
    return state.get("investigation_context") or []


def searcher_node(state: OSINTAgentState) -> dict[str, Any]:
    """Searcher Agent: web lookups via OSINT-Search and xRecon modules only."""
    tools = get_searcher_tools()
    goal = state.get("goal") or ""
    ctx = _ctx(state)
    result: dict[str, Any] = {"calls": [], "data": None, "error": None}
    ips: list[str] = []

    # Decide what to run from goal/context (simplified: run shodan/censys if we have a target)
    target = None
    for c in reversed(ctx):
        if c.get("type") == "orchestrator_directive" and c.get("target"):
            target = c["target"]
            break
    if not target and goal:
        target = goal.split()[-1].strip(".,")  # crude fallback

    if target:
        r = tools["shodan_search"](target)
        result["calls"].append({"tool": "shodan_search", "target": target, "success": r.get("success")})
        if r.get("success") and r.get("data"):
            d = r["data"]
            if d.get("type") == "host":
                ips.append(target)
            for m in d.get("matches", []):
                ip = m.get("ip_str")
                if ip:
                    ips.append(ip)
        r2 = tools["censys_search"](target)
        result["calls"].append({"tool": "censys_search", "target": target, "success": r2.get("success")})
        if r2.get("success") and r2.get("data"):
            result.setdefault("censys", r2["data"])
    result["data"] = result.get("data") or {"discovered_ips": ips, "goal": goal}
    result["discovered_ips"] = ips

    return {
        "searcher_result": result,
        "discovered_ips": list(dict.fromkeys((state.get("discovered_ips") or []) + ips)),
        "investigation_context": ctx + [{"type": "searcher", "result_summary": str(len(ips)) + " IPs", "result": result}],
    }


def analyzer_node(state: OSINTAgentState) -> dict[str, Any]:
    """Analyzer Agent: GraySentinel semantic search and threat scoring only."""
    tools = get_analyzer_tools()
    goal = state.get("goal") or ""
    ctx = _ctx(state)
    result: dict[str, Any] = {"semantic_results": [], "threat_score": 0.0, "error": None}

    semantic = tools["semantic_search"](goal or "threat leak breach", limit=5)
    if semantic.get("success"):
        result["semantic_results"] = semantic.get("results", [])[:5]
    findings = [state.get("searcher_result"), state.get("pentester_result")]
    scored = tools["score_threat"]([f for f in findings if f], result.get("semantic_results"))
    if scored.get("success"):
        result["threat_score"] = scored.get("threat_score", 0.0)
        result["reasons"] = scored.get("reasons", [])

    return {
        "analyzer_result": result,
        "threat_score": result["threat_score"],
        "investigation_context": ctx + [{"type": "analyzer", "threat_score": result["threat_score"], "result": result}],
    }


def pentester_node(state: OSINTAgentState) -> dict[str, Any]:
    """Pentester Agent: port scan and CyberNinja passive only."""
    tools = get_pentester_tools()
    ctx = _ctx(state)
    ips = state.get("discovered_ips") or []
    result: dict[str, Any] = {"scans": [], "error": None}

    for ip in ips[:3]:  # cap at 3 IPs per round
        r = tools["port_scan"](ip)
        result["scans"].append({"host": ip, "port_scan": r})
    if not ips:
        result["message"] = "No IPs to scan; run Searcher first."

    return {
        "pentester_result": result,
        "investigation_context": ctx + [{"type": "pentester", "scans": len(result["scans"]), "result": result}],
    }


def orchestrator_node(state: OSINTAgentState) -> dict[str, Any]:
    """Orchestrator Agent: synthesize results, trigger sub-agents, STIX 2.1 compliance. No tools."""
    ctx = _ctx(state)
    goal = state.get("goal") or ""
    searcher = state.get("searcher_result") or {}
    analyzer = state.get("analyzer_result") or {}
    pentester = state.get("pentester_result") or {}
    ips = state.get("discovered_ips") or []
    threat = state.get("threat_score") or 0.0

    # Build STIX 2.1 bundle from current state
    stix_bundle = None
    try:
        from stix_pipeline import build_stix_bundle
        for name, res in [("shodan_recon", searcher), ("port_scanner", pentester)]:
            if res and res.get("data"):
                b = build_stix_bundle(name, res)
                if b:
                    stix_bundle = b
                    break
        if not stix_bundle and pentester.get("scans"):
            for scan in pentester["scans"]:
                ps = scan.get("port_scan", {})
                b = build_stix_bundle("port_scanner", ps)
                if b:
                    stix_bundle = b
                    break
    except Exception:
        pass

    summary = {
        "goal": goal,
        "discovered_ips": ips,
        "threat_score": threat,
        "searcher_calls": len(searcher.get("calls", [])),
        "analyzer_threat": analyzer.get("threat_score"),
        "pentester_scans": len(pentester.get("scans", [])),
        "stix_ready": stix_bundle is not None,
    }

    # Next agent routing: simple policy
    next_agent = "__end__"
    if not searcher.get("data") and goal:
        next_agent = "searcher"
    elif analyzer.get("threat_score") is None and ips:
        next_agent = "analyzer"
    elif ips and not pentester.get("scans"):
        next_agent = "pentester"
    elif searcher.get("data") and analyzer.get("threat_score") is None:
        next_agent = "analyzer"
    else:
        next_agent = "__end__"

    return {
        "orchestrator_summary": summary,
        "stix_bundle": stix_bundle,
        "next_agent": next_agent,
        "investigation_context": ctx + [{"type": "orchestrator_directive", "summary": summary, "next_agent": next_agent, "target": goal or (ips[0] if ips else None)}],
    }
