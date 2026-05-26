"""
Robots.txt and sitemap.xml ingester — keyless HTTP reconnaissance.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

_USER_AGENT = "Graphyte-OSINT/1.0"
_TIMEOUT = 12
_SITEMAP_LOC_RE = re.compile(r"(?i)^Sitemap:\s*(\S+)")
_ROBOTS_LINE_RE = re.compile(r"(?i)^(User-agent|Disallow|Allow|Crawl-delay):\s*(.*)$")


def _normalize_domain(target: str) -> str:
    t = target.strip()
    if t.startswith("http://") or t.startswith("https://"):
        parsed = urlparse(t)
        host = parsed.netloc or parsed.path.split("/")[0]
    else:
        host = t.split("/")[0]
    return host.lower().removeprefix("www.")


def _base_url(domain: str) -> str:
    return f"https://{domain}"


def _fetch_text(url: str) -> tuple[str | None, int | None, str | None]:
    try:
        r = requests.get(
            url,
            timeout=_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
            allow_redirects=True,
        )
        if r.status_code >= 400:
            return None, r.status_code, f"HTTP {r.status_code}"
        return r.text, r.status_code, None
    except requests.RequestException as e:
        return None, None, str(e)


def _parse_robots(body: str) -> dict[str, Any]:
    sitemaps: list[str] = []
    rules: list[dict[str, str]] = []
    current_agent = "*"

    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sm = _SITEMAP_LOC_RE.match(line)
        if sm:
            sitemaps.append(sm.group(1).strip())
            continue
        m = _ROBOTS_LINE_RE.match(line)
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        if key == "user-agent":
            current_agent = val or "*"
        else:
            rules.append({"user_agent": current_agent, "directive": key, "path": val})

    return {"sitemaps": sitemaps, "rules": rules}


def _parse_sitemap_xml(body: str, max_urls: int = 500) -> list[dict[str, Any]]:
    urls: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return urls

    tag = lambda el: el.tag.split("}")[-1] if "}" in el.tag else el.tag

    for elem in root.iter():
        if tag(elem) != "url":
            continue
        loc = lastmod = None
        for child in elem:
            t = tag(child)
            if t == "loc" and child.text:
                loc = child.text.strip()
            elif t == "lastmod" and child.text:
                lastmod = child.text.strip()
        if loc:
            urls.append({"loc": loc, "lastmod": lastmod})
        if len(urls) >= max_urls:
            break

    # sitemap index → nested sitemap locs
    if not urls:
        for elem in root.iter():
            if tag(elem) == "sitemap":
                for child in elem:
                    if tag(child) == "loc" and child.text:
                        urls.append({"loc": child.text.strip(), "type": "sitemap_index"})
            if len(urls) >= max_urls:
                break
    return urls


def robots_sitemap_ingest(domain: str, max_sitemap_urls: int = 200) -> dict[str, Any]:
    """
    Fetch robots.txt, discover sitemaps, and extract URLs.
    """
    host = _normalize_domain(domain)
    if not host or "." not in host:
        return {"success": False, "error": "Invalid domain", "domain": domain}

    base = _base_url(host)
    robots_url = urljoin(base + "/", "robots.txt")

    result: dict[str, Any] = {
        "success": False,
        "domain": host,
        "robots_url": robots_url,
        "robots": None,
        "sitemaps_fetched": [],
        "sitemap_urls": [],
        "url_count": 0,
        "error": None,
    }

    body, status, err = _fetch_text(robots_url)
    parsed = _parse_robots(body) if body else {"sitemaps": [], "rules": []}
    result["robots"] = {
        "status_code": status,
        "sitemap_directives": parsed["sitemaps"],
        "rules": parsed["rules"][:200],
        "rule_count": len(parsed["rules"]),
        "note": err if body is None else None,
    }

    sitemap_candidates = list(parsed["sitemaps"])
    if not sitemap_candidates:
        sitemap_candidates = [
            urljoin(base + "/", "sitemap.xml"),
            urljoin(base + "/", "sitemap_index.xml"),
        ]

    all_urls: list[dict[str, Any]] = []
    fetched: list[dict[str, Any]] = []

    for sm_url in sitemap_candidates[:5]:
        sm_body, sm_status, sm_err = _fetch_text(sm_url)
        entry: dict[str, Any] = {"url": sm_url, "status_code": sm_status, "error": sm_err}
        if sm_body:
            urls = _parse_sitemap_xml(sm_body, max_urls=max_sitemap_urls)
            entry["url_count"] = len(urls)
            all_urls.extend(urls)
            # If index, fetch first child sitemap
            for u in urls:
                if u.get("type") == "sitemap_index" and len(all_urls) < max_sitemap_urls:
                    child_body, _, _ = _fetch_text(u["loc"])
                    if child_body:
                        all_urls.extend(_parse_sitemap_xml(child_body, max_urls=max_sitemap_urls - len(all_urls)))
        fetched.append(entry)
        if len(all_urls) >= max_sitemap_urls:
            break

    result["sitemaps_fetched"] = fetched
    result["sitemap_urls"] = all_urls[:max_sitemap_urls]
    result["url_count"] = len(result["sitemap_urls"])
    # Success when we parsed robots and/or discovered sitemap URLs
    result["success"] = bool(body) or result["url_count"] > 0 or status == 404
    if not result["success"]:
        result["error"] = err or "robots.txt not reachable and no sitemap URLs found"
    return result
