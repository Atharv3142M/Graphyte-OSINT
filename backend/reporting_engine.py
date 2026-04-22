"""
Reporting Engine — compiles accumulated STIX 2.1 data into human-readable and
machine-readable investigation reports.

Report types
────────────
executive-summary  → formatted Markdown string
technical-report   → formatted Markdown string
stix-bundle        → raw STIX 2.1 bundle (JSON)
raw-data           → all gathered evidence (JSON)
ioc-list           → CSV of indicators of compromise

All functions fetch data directly from:
  • Neo4j  — STIX graph (nodes + relationships)
  • Redis  — recent Celery task results (last 50 completed tasks)
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.neo4j_client import Neo4jClient


# ─────────────────────────────────────────────────────────────────────────────
# Data gathering helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_stix_graph() -> Dict[str, Any]:
    """Fetch all STIX objects + relationships from Neo4j."""
    try:
        client = Neo4jClient()
        data = client.get_graph_cytoscape()
        client.close()
        return data
    except Exception:
        return {"elements": {"nodes": [], "edges": []}}


def _get_recent_task_results(limit: int = 50) -> List[Dict[str, Any]]:
    """Load recent Celery task results from Redis."""
    results: List[Dict[str, Any]] = []
    try:
        import os
        from redis import Redis

        url = os.getenv("CELERY_BROKER_URL") or os.getenv(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        r = Redis.from_url(url, decode_responses=True)
        # Scan for completed task result keys
        for key in r.scan_iter("celery-task-meta-*", count=limit * 2):
            raw = r.get(key)
            if not raw:
                continue
            try:
                obj = json.loads(raw)
                if obj.get("status") == "SUCCESS" and obj.get("result"):
                    results.append(obj["result"])
            except Exception:
                pass
            if len(results) >= limit:
                break
    except Exception:
        pass
    return results


# ─────────────────────────────────────────────────────────────────────────────
# IOC extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_iocs(graph: Dict[str, Any]) -> Dict[str, List[str]]:
    """Pull IOCs of each type from STIX graph nodes."""
    iocs: Dict[str, List[str]] = {
        "ipv4": [],
        "ipv6": [],
        "domains": [],
        "urls": [],
        "emails": [],
        "usernames": [],
        "hashes": [],
        "cves": [],
    }
    for node in graph.get("elements", {}).get("nodes", []):
        nd = node.get("data", {})
        stype = nd.get("type", "")
        label = str(nd.get("label") or "").strip()

        if stype == "ipv4-addr" and label:
            iocs["ipv4"].append(label)
        elif stype == "ipv6-addr" and label:
            iocs["ipv6"].append(label)
        elif stype == "domain-name" and label:
            # Skip parent-domain placeholders
            if not label.lower().startswith("domain--"):
                iocs["domains"].append(label)
        elif stype == "url" and label and label.startswith(("http://", "https://")):
            iocs["urls"].append(label)
        elif stype == "user-account":
            login = nd.get("account_login") or nd.get("account_type") or ""
            if login and "@" not in login:
                iocs["usernames"].append(f"{login} ({nd.get('account_type','')})")
        elif stype == "note":
            content = nd.get("content") or {}
            if isinstance(content, dict):
                iocs["emails"].extend(content.get("emails", []))
                iocs["usernames"].extend(content.get("usernames", []))
                iocs["domains"].extend(content.get("platforms_found", []))

    # Deduplicate
    for k in iocs:
        iocs[k] = list(dict.fromkeys(iocs[k]))

    return iocs


def _threat_level(score: float) -> tuple[str, str]:
    """Return (label, color) for a threat score 0.0–1.0."""
    if score >= 0.8:
        return "CRITICAL", "🔴"
    if score >= 0.6:
        return "HIGH", "🟠"
    if score >= 0.4:
        return "MEDIUM", "🟡"
    if score >= 0.2:
        return "LOW", "🟢"
    return "NEGLIGIBLE", "⚪"


# ─────────────────────────────────────────────────────────────────────────────
# Markdown report builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_executive_summary(
    graph: Dict[str, Any],
    task_results: List[Dict[str, Any]],
) -> str:
    """Human-readable executive summary in Markdown."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    nodes = graph.get("elements", {}).get("nodes", [])
    edges = graph.get("elements", {}).get("edges", [])

    # Entity type breakdown
    type_counts: Dict[str, int] = {}
    for n in nodes:
        t = n.get("data", {}).get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    # IOC summary
    iocs = _extract_iocs(graph)
    threat_score = _derive_threat_score(nodes, task_results)
    threat_label, _ = _threat_level(threat_score)

    # Investigation targets from task results
    targets: List[str] = []
    for tr in task_results:
        for k in ("target", "domain", "host", "username", "url"):
            v = tr.get(k) or tr.get("data", {}).get(k)
            if v and v not in targets:
                targets.append(str(v))

    md = f"""# Executive Summary Report
**Generated:** {now}
**Platform:** Graphyte OSINT

---

## Investigation Overview

| Metric | Value |
|--------|-------|
| Total Entities | {len(nodes)} |
| Relationships | {len(edges)} |
| Threat Level | {threat_label} ({threat_score:.2f}) |

## Entity Breakdown

"""
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        md += f"- **{etype}**: {count}\n"

    md += f"""
## Targets Investigated

"""
    for t in targets[:20]:
        md += f"- `{t}`\n"

    md += f"""
## Indicators of Compromise (IOCs)

| Type | Count |
|------|-------|
| IPv4 Addresses | {len(iocs['ipv4'])} |
| Domains | {len(iocs['domains'])} |
| URLs | {len(iocs['urls'])} |
| Email Addresses | {len(iocs['emails'])} |
| Usernames | {len(iocs['usernames'])} |

"""
    if iocs["ipv4"]:
        md += "### IPv4 Addresses\n" + "\n".join(f"- `{ip}`" for ip in iocs["ipv4"][:30]) + "\n\n"
    if iocs["domains"]:
        md += "### Domains\n" + "\n".join(f"- `{d}`" for d in iocs["domains"][:30]) + "\n\n"
    if iocs["urls"]:
        md += "### URLs\n" + "\n".join(f"- `{u}`" for u in iocs["urls"][:30]) + "\n\n"
    if iocs["emails"]:
        md += "### Email Addresses\n" + "\n".join(f"- `{e}`" for e in iocs["emails"][:30]) + "\n\n"

    md += """---

*This report was generated automatically by Graphyte OSINT.*
*For detailed technical findings, generate a Technical Report.*
"""
    return md


def _build_technical_report(
    graph: Dict[str, Any],
    task_results: List[Dict[str, Any]],
) -> str:
    """Detailed technical report with full evidence chain."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    nodes = graph.get("elements", {}).get("nodes", [])
    edges = graph.get("elements", {}).get("edges", [])
    iocs = _extract_iocs(graph)
    threat_score = _derive_threat_score(nodes, task_results)
    threat_label, _ = _threat_level(threat_score)

    type_counts: Dict[str, int] = {}
    for n in nodes:
        t = n.get("data", {}).get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    md = f"""# Technical Investigation Report
**Generated:** {now}
**Platform:** Graphyte OSINT

---

## Threat Assessment

| Indicator | Value |
|-----------|-------|
| Threat Score | {threat_score:.3f} / 1.0 |
| Threat Level | {threat_label} |
| Total Entities | {len(nodes)} |
| Total Relationships | {len(edges)} |

"""

    # Entity inventory
    md += "## Entity Inventory\n\n"
    for etype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        md += f"- **{etype}**: {count} {'node' if count == 1 else 'nodes'}\n"

    # Module findings
    md += "\n## Module Findings\n\n"
    if task_results:
        for tr in task_results:
            module = tr.get("module", tr.get("source", "unknown"))
            success = tr.get("success", True)
            error = tr.get("error")
            data_keys = [k for k in (tr.get("data") or {}).keys() if k not in ("success", "error")] if isinstance(tr.get("data"), dict) else []

            status_icon = "✅" if success else "❌"
            md += f"### {status_icon} {module}\n"
            if error:
                md += f"- **Error:** {error}\n"
            if data_keys:
                md += f"- **Fields:** {', '.join(data_keys)}\n"
                # Include notable IOCs from this result
                d = tr.get("data", {})
                for ip in d.get("ips", d.get("found_ips", []))[:5]:
                    md += f"  - IPv4: `{ip}`\n"
                for dom in d.get("domains", d.get("subdomains", []))[:5]:
                    md += f"  - Domain: `{dom}`\n"
                for email in d.get("emails", d.get("found_emails", []))[:5]:
                    md += f"  - Email: `{email}`\n"
                for url in d.get("urls", d.get("found_urls", []))[:5]:
                    md += f"  - URL: `{url}`\n"
            md += "\n"
    else:
        md += "No module results available.\n\n"

    # Full IOC dump
    md += "## Complete IOC List\n\n"
    md += f"| Type | Indicator |\n|------|-----------|\n"
    for ip in iocs["ipv4"]:
        md += f"| ipv4 | `{ip}` |\n"
    for d in iocs["domains"]:
        md += f"| domain | `{d}` |\n"
    for u in iocs["urls"]:
        md += f"| url | `{u}` |\n"
    for e in iocs["emails"]:
        md += f"| email | `{e}` |\n"
    for u in iocs["usernames"]:
        md += f"| username | `{u}` |\n"

    md += "\n## Relationship Map\n\n"
    if edges:
        for e in edges[:50]:
            ed = e.get("data", {})
            src = ed.get("source", "?")[:20]
            tgt = ed.get("target", "?")[:20]
            md += f"- `{src}` → `{tgt}`\n"
    else:
        md += "No relationships recorded.\n"

    md += "\n---"
    md += "\n*Generated by Graphyte OSINT — for authorized security research only.*\n"
    return md


def _derive_threat_score(nodes: List[Dict[str, Any]], task_results: List[Dict[str, Any]]) -> float:
    """Heuristic threat score 0.0–1.0 based on entity types and findings."""
    score = 0.0
    node_types = {n.get("data", {}).get("type", "") for n in nodes}

    if "malware" in node_types or "attack-pattern" in node_types:
        score += 0.5
    if "ipv4-addr" in node_types or "ipv6-addr" in node_types:
        score += 0.1
    if "domain-name" in node_types:
        score += 0.1
    if "user-account" in node_types:
        score += 0.15

    # Scan results: open ports add risk
    for tr in task_results:
        ports = tr.get("open_ports", tr.get("data", {}).get("open_ports", []))
        if ports:
            score = min(1.0, score + 0.1)

        # Honeypot/compromised signals
        if tr.get("is_honeypot") or tr.get("data", {}).get("is_honeypot"):
            score = min(1.0, score + 0.3)
        if tr.get("is_compromised") or tr.get("data", {}).get("is_compromised"):
            score = min(1.0, score + 0.3)

    # Penalize excessive unknowns
    if not nodes and not task_results:
        score = 0.05

    return round(score, 3)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_executive_summary() -> str:
    graph = _get_stix_graph()
    tasks = _get_recent_task_results()
    return _build_executive_summary(graph, tasks)


def generate_technical_report() -> str:
    graph = _get_stix_graph()
    tasks = _get_recent_task_results()
    return _build_technical_report(graph, tasks)


def generate_stix_bundle() -> Dict[str, Any]:
    """Return the full STIX 2.1 bundle as JSON-serializable dict."""
    graph = _get_stix_graph()
    nodes = graph.get("elements", {}).get("nodes", [])
    edges = graph.get("elements", {}).get("edges", [])

    objects: List[Dict[str, Any]] = []
    id_map: Dict[str, Dict[str, Any]] = {}

    for n in nodes:
        nd = n.get("data", {})
        obj: Dict[str, Any] = {
            "type": nd.get("type", "unknown"),
            "id": nd.get("id", f"unknown--{len(objects)}"),
            "spec_version": "2.1",
        }
        label = nd.get("label") or ""
        if nd.get("type") == "ipv4-addr":
            obj["value"] = label
        elif nd.get("type") == "domain-name":
            obj["value"] = label
        elif nd.get("type") == "url":
            obj["value"] = label
        elif nd.get("type") == "user-account":
            obj["account_type"] = nd.get("account_type", label)
            obj["account_login"] = nd.get("account_login", label)
        elif nd.get("type") == "note":
            obj["abstract"] = label
            if nd.get("content"):
                try:
                    obj["content"] = json.loads(nd["content"]) if isinstance(nd["content"], str) else nd["content"]
                except Exception:
                    obj["content"] = nd["content"]
        objects.append(obj)
        id_map[obj["id"]] = obj

    now = datetime.utcnow().isoformat() + "Z"
    for e in edges:
        ed = e.get("data", {})
        src, tgt = ed.get("source"), ed.get("target")
        if src and tgt:
            objects.append({
                "type": "relationship",
                "id": ed.get("id", f"relationship--{len(objects)}"),
                "relationship_type": ed.get("type", "related-to"),
                "source_ref": src,
                "target_ref": tgt,
                "created": now,
                "modified": now,
                "spec_version": "2.1",
            })

    import uuid
    return {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid4()}",
        "spec_version": "2.1",
        "objects": objects,
    }


def generate_raw_data() -> Dict[str, Any]:
    """Return all gathered evidence as JSON."""
    graph = _get_stix_graph()
    tasks = _get_recent_task_results()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph": graph,
        "task_results": tasks,
        "iocs": _extract_iocs(graph),
    }


def generate_ioc_csv() -> str:
    """Return IOCs as RFC-4180 CSV."""
    graph = _get_stix_graph()
    iocs = _extract_iocs(graph)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["type", "indicator", "context"])
    for ip in iocs["ipv4"]:
        writer.writerow(["ipv4", ip, "discovered"])
    for d in iocs["domains"]:
        writer.writerow(["domain", d, "discovered"])
    for u in iocs["urls"]:
        writer.writerow(["url", u, "discovered"])
    for e in iocs["emails"]:
        writer.writerow(["email", e, "discovered"])
    for un in iocs["usernames"]:
        writer.writerow(["username", un, "discovered"])
    return output.getvalue()
