from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Tuple


_IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]{1,253}\.[a-zA-Z]{2,63}\b")
_URL_RE = re.compile(r"\bhttps?://[^\s\"'<>]+", re.IGNORECASE)
_ASN_RE = re.compile(r"\bAS\d{1,10}\b", re.IGNORECASE)


def _to_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return str(v)


def _flatten_strings(obj: Any) -> Iterable[str]:
    if obj is None:
        return
    if isinstance(obj, str):
        yield obj
        return
    if isinstance(obj, (int, float, bool)):
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                yield k
            yield from _flatten_strings(v)
        return
    if isinstance(obj, list):
        for item in obj:
            yield from _flatten_strings(item)
        return
    # fallback
    yield str(obj)


def _dedupe(seq: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for s in seq:
        s2 = (s or "").strip()
        if not s2:
            continue
        if s2 in seen:
            continue
        seen.add(s2)
        out.append(s2)
    return out


def _extract_artifacts(raw: Dict[str, Any]) -> Dict[str, List[str]]:
    texts = list(_flatten_strings(raw))
    ips = _dedupe(m.group(0) for t in texts for m in _IPV4_RE.finditer(t))
    emails = _dedupe(m.group(0) for t in texts for m in _EMAIL_RE.finditer(t))
    urls = _dedupe(m.group(0) for t in texts for m in _URL_RE.finditer(t))
    asns = _dedupe(m.group(0).upper() for t in texts for m in _ASN_RE.finditer(t))

    domains: List[str] = []
    for key in ("domain", "target", "host"):
        v = raw.get(key)
        if isinstance(v, str) and v and "." in v and "://" not in v:
            domains.append(v.strip())
    domains = _dedupe(domains)

    usernames: List[str] = []
    if isinstance(raw.get("username"), str):
        usernames.append(raw["username"])
    if isinstance(raw.get("usernames"), list):
        for u in raw["usernames"]:
            if isinstance(u, str):
                usernames.append(u)
    usernames = _dedupe(usernames)

    return {
        "ips": ips,
        "domains": domains,
        "urls": urls,
        "emails": emails,
        "usernames": usernames,
        "asns": asns,
    }


def _maybe_table(name: str, value: Any) -> Dict[str, Any] | None:
    # list[dict] → table
    if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
        columns: List[str] = []
        for row in value[:50]:
            for k in row.keys():
                if k not in columns:
                    columns.append(str(k))
            if len(columns) >= 16:
                break
        rows: List[List[Any]] = []
        for row in value[:200]:
            rows.append([row.get(c) for c in columns])
        return {"name": name, "columns": columns, "rows": rows}
    return None


def _stats_from_raw(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    stats: List[Dict[str, Any]] = []
    for k in ("status_code", "grade", "score", "count", "pages_crawled", "tech_count", "san_count"):
        if k in raw and raw.get(k) is not None:
            stats.append({"label": k.replace("_", " ").title(), "value": raw.get(k)})
    return stats


def _title_for_module(module_name: str, raw: Dict[str, Any]) -> str:
    base = module_name.replace("_", " ").title()
    # common nicer titles
    overrides = {
        "dns_intel": "DNS Intel",
        "whois_lookup": "WHOIS",
        "ssl_analyzer": "SSL/TLS Analysis",
        "http_security": "HTTP Security Headers",
        "tech_stack": "Tech Stack",
        "deep_scraper": "Deep Scraper",
        "reverse_ip_lookup": "Reverse IP",
        "ip_geolocation": "IP Geolocation",
        "bgp_asn_lookup": "BGP / ASN",
        "wayback_machine": "Wayback Machine",
        "email_header_analyzer": "Email Header Analyzer",
        "social_hunter": "Social Hunter",
        "sherlock_hunt": "Sherlock",
        "cyberninja_passive": "CyberNinja (Passive)",
        "port_scanner": "Port Scan",
        "scraper": "Scrape URLs",
        "graysentinel_pipeline": "GraySentinel Ingest",
        "shodan_recon": "Shodan Recon",
        "censys_recon": "Censys Recon",
        "xrecon": "xRecon",
        "metadata_extractor": "Metadata Extractor",
    }
    title = overrides.get(module_name, base)
    target = raw.get("target") or raw.get("domain") or raw.get("host") or raw.get("url") or raw.get("username")
    if isinstance(target, str) and target:
        return f"{title}: {target}"
    return title


def normalize_result(module_name: str, raw_result: Any) -> Dict[str, Any]:
    # Defensive: accept anything and coerce to a dict shape we can normalize.
    if raw_result is None:
        raw = {"error": "Module returned no result", "success": False}
    elif isinstance(raw_result, dict) and "data" in raw_result and isinstance(raw_result["data"], dict):
        # Unwrap {"success": True, "data": {...}}
        unwrapped = dict(raw_result["data"])
        unwrapped["success"] = raw_result.get("success", True)
        if "error" in raw_result:
            unwrapped["error"] = raw_result["error"]
        raw = unwrapped
    elif isinstance(raw_result, dict):
        raw = raw_result
    else:
        raw = {"error": "Invalid result type", "raw": _to_str(raw_result), "success": False}

    ok = bool(raw.get("success", True)) and not bool(raw.get("error"))
    errors: List[Dict[str, Any]] = []
    if not ok:
        msg = str(raw.get("error") or "Module failed")
        code = "module_error"
        hint = None
        lower = msg.lower()
        if "api key" in lower or "unauthorized" in lower or "forbidden" in lower:
            code = "missing_api_key"
            hint = "Set the required API key(s) in Settings or environment variables."
        elif "ssrf" in lower or "blocked" in lower:
            code = "ssrf_blocked"
            hint = "Target blocked by SSRF policy. Use a public target URL/domain/IP."
        elif "timed out" in lower or "timeout" in lower:
            code = "timeout"
            hint = "This module timed out. Try again or lower intensity / scope."
        errors.append({"code": code, "message": msg, "hint": hint, "retryable": code in {"timeout"}})

    artifacts = _extract_artifacts(raw)

    tables: List[Dict[str, Any]] = []
    for k, v in list(raw.items()):
        t = _maybe_table(k, v)
        if t:
            tables.append(t)

    # Common structured tables
    if isinstance(raw.get("analysis"), list):
        t = _maybe_table("analysis", raw.get("analysis"))
        if t:
            tables.append(t)
    if isinstance(raw.get("snapshots"), list):
        t = _maybe_table("snapshots", raw.get("snapshots"))
        if t:
            tables.append(t)
    if isinstance(raw.get("technologies"), list):
        t = _maybe_table("technologies", raw.get("technologies"))
        if t:
            tables.append(t)

    envelope = {
        "ok": ok,
        "module": module_name,
        "summary": {
            "title": _title_for_module(module_name, raw),
            "stats": _stats_from_raw(raw),
            "badges": [],
        },
        "artifacts": artifacts,
        "tables": tables[:12],
        "raw": raw,
        "errors": errors,
    }
    return envelope

