"""
xRecon-style keyless reconnaissance (username, domain, email).
Uses passive HTTP/DNS checks only — no API keys required.
"""
from __future__ import annotations

import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import quote

import requests

_USER_AGENT = "Graphyte-OSINT/1.0"
_TIMEOUT = 8

_USERNAME_SITES: list[tuple[str, str]] = [
    ("GitHub", "https://github.com/{q}"),
    ("GitLab", "https://gitlab.com/{q}"),
    ("Reddit", "https://www.reddit.com/user/{q}"),
    ("Hacker News", "https://news.ycombinator.com/user?id={q}"),
    ("Dev.to", "https://dev.to/{q}"),
    ("Medium", "https://medium.com/@{q}"),
    ("Pinterest", "https://www.pinterest.com/{q}/"),
    ("Twitch", "https://www.twitch.tv/{q}"),
    ("Steam", "https://steamcommunity.com/id/{q}"),
    ("Keybase", "https://keybase.io/{q}"),
    ("Docker Hub", "https://hub.docker.com/u/{q}"),
    ("npm", "https://www.npmjs.com/~{q}"),
    ("PyPI", "https://pypi.org/user/{q}/"),
    ("Instagram", "https://www.instagram.com/{q}/"),
    ("TikTok", "https://www.tiktok.com/@{q}"),
]

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)
_IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
)


def _detect_query_type(query: str, query_type: str) -> str:
    qt = (query_type or "auto").strip().lower()
    if qt not in ("", "auto"):
        return qt
    q = query.strip()
    if "@" in q:
        return "email"
    if _IPV4_RE.match(q):
        return "ip"
    if _DOMAIN_RE.match(q):
        return "domain"
    return "username"


def _http_probe(url: str) -> dict[str, Any]:
    out: dict[str, Any] = {"url": url, "found": False, "status": None, "error": None}
    try:
        r = requests.head(
            url,
            allow_redirects=True,
            timeout=_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        )
        out["status"] = r.status_code
        # 200/301/302/308 often mean profile exists; 404 = not found
        out["found"] = r.status_code in (200, 301, 302, 308)
    except requests.RequestException as e:
        out["error"] = str(e)
    return out


def _domain_dns(domain: str) -> dict[str, Any]:
    info: dict[str, Any] = {"domain": domain, "addresses": [], "aliases": []}
    try:
        hostname, aliases, addresses = socket.gethostbyname_ex(domain)
        info["hostname"] = hostname
        info["aliases"] = list(aliases)
        info["addresses"] = list(addresses)
    except OSError as e:
        info["error"] = str(e)
    return info


def _username_recon(username: str) -> list[dict[str, Any]]:
    safe = quote(username.strip(), safe="")
    sources: list[dict[str, Any]] = []

    def check(site: tuple[str, str]) -> dict[str, Any]:
        name, template = site
        url = template.format(q=safe)
        probe = _http_probe(url)
        return {
            "name": name,
            "url": url,
            "found": probe["found"],
            "status": probe["status"],
            "error": probe.get("error"),
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(check, site) for site in _USERNAME_SITES]
        for fut in as_completed(futures):
            try:
                sources.append(fut.result())
            except Exception as e:
                sources.append({"name": "unknown", "url": "", "found": False, "error": str(e)})

    sources.sort(key=lambda s: (not s.get("found"), s.get("name", "")))
    return sources


def _domain_recon(domain: str) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    dns_info = _domain_dns(domain)
    for addr in dns_info.get("addresses") or []:
        sources.append(
            {
                "name": "DNS A",
                "url": addr,
                "found": True,
                "status": None,
                "kind": "ip",
            }
        )
    if dns_info.get("error"):
        sources.append(
            {
                "name": "DNS",
                "url": domain,
                "found": False,
                "error": dns_info["error"],
            }
        )

    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}/"
        probe = _http_probe(url)
        sources.append(
            {
                "name": f"Web ({scheme.upper()})",
                "url": url,
                "found": probe["found"],
                "status": probe["status"],
                "error": probe.get("error"),
            }
        )
    return sources


def _email_recon(email: str) -> tuple[str, list[dict[str, Any]]]:
    local, _, domain = email.strip().partition("@")
    if not domain:
        return "email", [{"name": "parse", "url": email, "found": False, "error": "Invalid email"}]
    sources = _username_recon(local)
    sources.extend(_domain_recon(domain))
    return "email", sources


def xrecon_search(query: str, query_type: str = "username") -> dict[str, Any]:
    """
    Run keyless xRecon-style lookup for username, domain, email, or IP.
    """
    q = (query or "").strip()
    if not q:
        return {"success": False, "error": "Query is required", "query": q, "query_type": query_type}

    resolved = _detect_query_type(q, query_type)
    sources: list[dict[str, Any]] = []

    if resolved == "domain":
        sources = _domain_recon(q)
    elif resolved == "email":
        resolved, sources = _email_recon(q)
    elif resolved == "ip":
        sources = [
            {
                "name": "IP target",
                "url": q,
                "found": True,
                "status": None,
                "kind": "ip",
            }
        ]
    else:
        resolved = "username"
        sources = _username_recon(q)

    found = [s for s in sources if s.get("found")]
    profile_urls = [s["url"] for s in found if isinstance(s.get("url"), str) and s["url"].startswith("http")]

    return {
        "success": True,
        "query": q,
        "query_type": resolved,
        "found_count": len(found),
        "sources": sources,
        "profile_urls": profile_urls,
        "data": {
            "query": q,
            "query_type": resolved,
            "found_count": len(found),
            "sources": sources,
        },
    }
