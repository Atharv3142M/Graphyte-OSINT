"""
CyberNinja passive sandbox wrapper.

Self-contained passive username enumeration. No external repos or symlinks.
Checks well-known sites via HTTP(S) only (no Tor, no browser).
"""
from __future__ import annotations

from typing import Any, Dict, List

# Minimal site definitions: url_format with {}, expected status for "claimed"
_MINIMAL_SITES = [
    {"name": "GitHub", "url": "https://github.com/{}", "claimed_status": 200},
    {"name": "GitLab", "url": "https://gitlab.com/{}", "claimed_status": 200},
    {"name": "Reddit", "url": "https://www.reddit.com/user/{}", "claimed_status": 200},
]


def _check_username_site(username: str, site: dict, timeout: float | None) -> dict[str, Any]:
    """Check if username exists on a single site. Returns site name and status."""
    try:
        import requests
        url = site["url"].format(username)
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OSINT-Bot/1.0)"},
            timeout=timeout or 10,
            allow_redirects=True,
        )
        exists = resp.status_code == site.get("claimed_status", 200)
        return {"site": site["name"], "url": url, "status_code": resp.status_code, "exists": exists}
    except Exception as e:
        return {"site": site["name"], "error": str(e), "exists": False}


def cyberninja_passive(
    usernames: List[str],
    timeout: float | None = None,
    site_list: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Run passive username enumeration. Self-contained; no repos dependency.

    Args:
        usernames: List of usernames to investigate.
        timeout: Optional request timeout in seconds.
        site_list: Optional subset of site names to limit (e.g. ["GitHub", "GitLab"]).

    Returns:
        Dictionary keyed by username with per-site results.
    """
    if not usernames:
        return {"error": "At least one username is required", "success": False}

    sites = _MINIMAL_SITES
    if site_list:
        sites = [s for s in _MINIMAL_SITES if s["name"] in site_list]
    if not sites:
        sites = _MINIMAL_SITES

    results: Dict[str, Any] = {}
    for username in usernames:
        checks = [_check_username_site(username, s, timeout) for s in sites]
        results[username] = {"checks": checks, "summary": {c["site"]: c.get("exists") for c in checks}}

    return {"success": True, "data": results}
