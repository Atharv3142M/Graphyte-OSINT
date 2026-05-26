from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests


API_BASE = os.getenv("OSINT_SMOKE_API_BASE", "http://127.0.0.1:8000")
TENANT_ID = os.getenv("OSINT_SMOKE_TENANT_ID", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
TIMEOUT_S = float(os.getenv("OSINT_SMOKE_TIMEOUT_S", "20"))
POLL_INTERVAL_S = float(os.getenv("OSINT_SMOKE_POLL_INTERVAL_S", "1.5"))
POLL_MAX_S = float(os.getenv("OSINT_SMOKE_POLL_MAX_S", "45"))
STARTUP_WAIT_S = float(os.getenv("OSINT_SMOKE_STARTUP_WAIT_S", "60"))


def _headers() -> dict[str, str]:
    return {"Content-Type": "application/json", "X-Tenant-ID": TENANT_ID}


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    r = requests.post(f"{API_BASE}{path}", headers=_headers(), json=body, timeout=TIMEOUT_S)
    try:
        payload = r.json()
    except Exception:
        payload = {"_raw": r.text}
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code} {path}: {payload}")
    return payload


def _wait_for_health() -> None:
    deadline = time.time() + STARTUP_WAIT_S
    last_err: str | None = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{API_BASE}/health", timeout=min(TIMEOUT_S, 5))
            if r.ok:
                return
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(1.0)
    raise RuntimeError(f"Backend not healthy at {API_BASE}/health after {STARTUP_WAIT_S}s. Last error: {last_err}")


def _poll_task(task_id: str, poll_max_s: float | None = None) -> dict[str, Any]:
    deadline = time.time() + (poll_max_s if poll_max_s is not None else POLL_MAX_S)
    last: dict[str, Any] = {}
    while time.time() < deadline:
        r = requests.get(f"{API_BASE}/api/tasks/{task_id}", headers=_headers(), timeout=TIMEOUT_S)
        last = r.json() if r.ok else {"status": f"HTTP_{r.status_code}", "result": None}
        status = str(last.get("status", "")).lower()
        if status in {"success", "failure"}:
            return last
        time.sleep(POLL_INTERVAL_S)
    return {"task_id": task_id, "status": "timeout", "result": last.get("result")}


@dataclass(frozen=True)
class Case:
    id: str
    endpoint: str
    body: dict[str, Any]
    classify: Callable[[dict[str, Any], dict[str, Any]], str]
    poll_max_s: float | None = None


def _error_message_from_result(result: dict[str, Any]) -> str:
    """Extract a human message from normalized envelope or legacy raw dict."""
    errors = result.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0]
        if isinstance(first, dict) and first.get("message"):
            return str(first["message"])
    raw = result.get("raw")
    if isinstance(raw, dict) and raw.get("error"):
        return str(raw["error"])
    if result.get("error"):
        return str(result["error"])
    return ""


def _classify_default(dispatch: dict[str, Any], final: dict[str, Any]) -> str:
    status = str(final.get("status", "")).lower()
    result = final.get("result") or {}
    if status == "timeout":
        return "timeout"
    if status == "failure":
        return "fail"
    if not isinstance(result, dict):
        return "ok"

    # Normalized UI envelope from Celery (ok + errors[])
    if "ok" in result:
        if result.get("ok") is False:
            err = _error_message_from_result(result).lower()
            if "api key" in err or "unauthorized" in err or "forbidden" in err or "invalid api" in err:
                return "needs_key"
            if "packages required" in err or "not available" in err or "not installed" in err:
                return "needs_deps"
            if "ssrf" in err or "blocked" in err:
                return "blocked"
            if "timeout" in err or "timed out" in err:
                return "timeout"
            return "soft_fail"
        return "ok"

    # Legacy raw module dict (pre-normalize)
    if result.get("error") or result.get("success") is False:
        err = _error_message_from_result(result).lower()
        if "api key" in err or "unauthorized" in err or "forbidden" in err:
            return "needs_key"
        if "ssrf" in err or "blocked" in err:
            return "blocked"
        if "timeout" in err or "timed out" in err:
            return "timeout"
        return "soft_fail"
    return "ok"


def cases() -> list[Case]:
    email_headers = "From: a@example.com\r\nTo: b@example.com\r\nSubject: test\r\nDate: Tue, 21 Apr 2026 00:00:00 +0000\r\nMessage-ID: <test@example.com>\r\nReceived: from mail.example.com (mail.example.com [93.184.216.34]) by mx.example.net with ESMTP id 123;\r\n\tTue, 21 Apr 2026 00:00:00 +0000\r\n"
    # Keep this suite fast: avoid long-running / noisy jobs by default.
    return [
        Case("dns-intel", "/api/dns-intel", {"domain": "example.com", "brute_subdomains": False}, _classify_default, poll_max_s=90),
        Case("whois", "/api/whois", {"domain": "example.com"}, _classify_default, poll_max_s=90),
        Case("ssl-analyze", "/api/ssl-analyze", {"host": "example.com", "port": 443, "timeout": 10}, _classify_default, poll_max_s=60),
        Case("http-security", "/api/http-security", {"url": "https://example.com", "timeout": 10}, _classify_default),
        Case("tech-stack", "/api/tech-stack", {"url": "https://example.com", "timeout": 10}, _classify_default),
        Case("cert-transparency", "/api/cert-transparency", {"domain": "example.com", "use_html_fallback": True}, _classify_default),
        Case("deep-scraper", "/api/deep-scraper", {"url": "https://example.com", "max_depth": 1, "max_pages": 3, "max_concurrent": 3}, _classify_default, poll_max_s=90),
        Case("reverse-ip", "/api/reverse-ip", {"target": "example.com"}, _classify_default),
        Case("ip-geolocation", "/api/ip-geolocation", {"target": "8.8.8.8"}, _classify_default),
        Case("bgp-asn", "/api/bgp-asn", {"target": "AS15169"}, _classify_default),
        Case("wayback", "/api/wayback", {"target": "example.com", "limit": 10}, _classify_default),
        Case("email-header", "/api/email-header", {"raw_headers": email_headers}, _classify_default),
        Case("sherlock", "/api/sherlock", {"username": "torvalds", "timeout": 10, "max_connections": 3}, _classify_default, poll_max_s=120),
        Case("social-hunter", "/api/social-hunter", {"username": "torvalds", "max_concurrent": 10}, _classify_default),
        Case("cyberninja", "/api/cyberninja", {"usernames": ["torvalds"], "timeout": 5, "site_list": None}, _classify_default),
        Case("xrecon", "/api/xrecon", {"query": "example.com", "query_type": "auto"}, _classify_default),
        Case("port-scan", "/api/port-scan", {"host": "example.com", "ports": [80, 443], "max_workers": 30, "timeout": 1.0}, _classify_default, poll_max_s=120),
        Case("scrape", "/api/scrape", {"urls": ["https://example.com"], "max_workers": 5}, _classify_default),
        # ingest can be slow / depends on Weaviate; keep out of default smoke.
        Case("shodan", "/api/shodan", {"target": "example.com", "api_key": None}, _classify_default),
        Case("censys", "/api/censys", {"target": "example.com", "api_id": None, "api_secret": None}, _classify_default),
        Case("robots-sitemap", "/api/robots-sitemap", {"domain": "example.com", "max_sitemap_urls": 20}, _classify_default),
        Case("favicon-hash", "/api/favicon-hash", {"domain": "example.com"}, _classify_default),
        Case("username-permutator", "/api/username-permutator", {"seed": "john.doe", "max_results": 20}, _classify_default),
        Case("github-osint", "/api/github-osint", {"target": "torvalds", "lookup_type": "username"}, _classify_default),
        Case("phone-intel", "/api/phone-intel", {"number": "+14155552671", "default_region": "US"}, _classify_default),
        Case("email-reputation", "/api/email-reputation", {"email": "test@example.com"}, _classify_default),
        # metadata-extract intentionally omitted from default suite (needs a real file path)
    ]


def main() -> int:
    _wait_for_health()
    out: dict[str, Any] = {"api_base": API_BASE, "cases": [], "summary": {}}
    counts: dict[str, int] = {}
    for c in cases():
        entry: dict[str, Any] = {"id": c.id, "endpoint": c.endpoint, "status": None, "task_id": None}
        try:
            dispatch = _post(c.endpoint, c.body)
            task_id = dispatch.get("task_id")
            entry["task_id"] = task_id
            if not task_id:
                entry["status"] = "fail"
                entry["error"] = f"missing task_id in response: {dispatch}"
            else:
                final = _poll_task(str(task_id), poll_max_s=c.poll_max_s)
                entry["final_status"] = final.get("status")
                entry["classification"] = c.classify(dispatch, final)
                entry["result"] = final.get("result")
                entry["status"] = "ok" if entry["classification"] == "ok" else entry["classification"]
        except Exception as e:
            entry["status"] = "fail"
            entry["error"] = str(e)

        out["cases"].append(entry)
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1

    out["summary"] = counts
    print(json.dumps(out, indent=2)[:2_000_000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

