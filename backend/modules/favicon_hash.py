"""
Favicon hash fingerprinting (Shodan-style MurmurHash3) — keyless.
"""
from __future__ import annotations

import base64
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

try:
    import mmh3
except ImportError:
    mmh3 = None  # type: ignore[assignment]

_USER_AGENT = "Graphyte-OSINT/1.0"
_TIMEOUT = 12
_ICON_RE = re.compile(
    r'<link[^>]+rel=["\'](?:shortcut )?icon["\'][^>]*>',
    re.IGNORECASE,
)
_HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)


def _normalize_domain(target: str) -> str:
    t = target.strip()
    if t.startswith("http://") or t.startswith("https://"):
        return urlparse(t).netloc.lower().removeprefix("www.")
    return t.lower().split("/")[0].removeprefix("www.")


def _shodan_favicon_hash(data: bytes) -> int | None:
    if mmh3 is None:
        return None
    b64 = base64.encodebytes(data).decode("utf-8").strip()
    return mmh3.hash(b64)


def _discover_icon_url(html: str, base_url: str) -> str | None:
    for tag in _ICON_RE.findall(html):
        m = _HREF_RE.search(tag)
        if m:
            return urljoin(base_url, m.group(1))
    return None


def favicon_hash_lookup(domain: str) -> dict[str, Any]:
    """
    Download favicon and compute MurmurHash3 fingerprint (Shodan-compatible).
    """
    host = _normalize_domain(domain)
    if not host or "." not in host:
        return {"success": False, "error": "Invalid domain", "domain": domain}

    if mmh3 is None:
        return {
            "success": False,
            "error": "mmh3 package required (pip install mmh3)",
            "domain": host,
        }

    base = f"https://{host}"
    candidates = [
        urljoin(base + "/", "favicon.ico"),
        urljoin(base + "/", "favicon.png"),
    ]

    icon_url_used: str | None = None
    data: bytes | None = None
    status: int | None = None

    try:
        home = requests.get(
            base,
            timeout=_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
            allow_redirects=True,
        )
        if home.ok and home.text:
            discovered = _discover_icon_url(home.text, base)
            if discovered:
                candidates.insert(0, discovered)
    except requests.RequestException:
        pass

    for url in candidates:
        try:
            r = requests.get(
                url,
                timeout=_TIMEOUT,
                headers={"User-Agent": _USER_AGENT},
                allow_redirects=True,
            )
            if r.ok and r.content and len(r.content) >= 16:
                data = r.content
                icon_url_used = url
                status = r.status_code
                break
        except requests.RequestException:
            continue

    if not data:
        return {
            "success": False,
            "error": "Could not fetch favicon",
            "domain": host,
            "candidates_tried": candidates,
        }

    fav_hash = _shodan_favicon_hash(data)
    return {
        "success": True,
        "domain": host,
        "favicon_url": icon_url_used,
        "status_code": status,
        "size_bytes": len(data),
        "favicon_hash": fav_hash,
        "favicon_hash_hex": format(fav_hash & 0xFFFFFFFF, "x") if fav_hash is not None else None,
        "shodan_search_hint": f'http.favicon.hash:{fav_hash}' if fav_hash is not None else None,
    }
