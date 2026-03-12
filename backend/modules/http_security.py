"""
HTTP Security Header Auditor - Checks 10 key security headers, grades A–F.
Uses only the requests library (already in the project).
"""
from __future__ import annotations

from typing import Any

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]

# Header definitions: name, description, severity weight, and what to look for
_SECURITY_HEADERS: list[dict[str, Any]] = [
    {
        "name": "Strict-Transport-Security",
        "description": "Enforces HTTPS connections, prevents SSL stripping attacks",
        "weight": 15,
        "recommendation": "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
    },
    {
        "name": "Content-Security-Policy",
        "description": "Prevents XSS, clickjacking, and code injection attacks",
        "weight": 15,
        "recommendation": "Add: Content-Security-Policy: default-src 'self'; script-src 'self'",
    },
    {
        "name": "X-Frame-Options",
        "description": "Prevents clickjacking by controlling iframe embedding",
        "weight": 10,
        "recommendation": "Add: X-Frame-Options: DENY (or SAMEORIGIN if iframes are needed)",
    },
    {
        "name": "X-Content-Type-Options",
        "description": "Prevents MIME type sniffing attacks",
        "weight": 10,
        "recommendation": "Add: X-Content-Type-Options: nosniff",
    },
    {
        "name": "Referrer-Policy",
        "description": "Controls how much referrer information is leaked to other sites",
        "weight": 10,
        "recommendation": "Add: Referrer-Policy: strict-origin-when-cross-origin",
    },
    {
        "name": "Permissions-Policy",
        "description": "Controls which browser features can be used (camera, mic, geolocation)",
        "weight": 10,
        "recommendation": "Add: Permissions-Policy: camera=(), microphone=(), geolocation=()",
    },
    {
        "name": "X-XSS-Protection",
        "description": "Legacy reflected XSS filter (superseded by CSP but still useful)",
        "weight": 5,
        "recommendation": "Add: X-XSS-Protection: 0 (rely on CSP instead, or 1; mode=block for legacy)",
    },
    {
        "name": "Cross-Origin-Opener-Policy",
        "description": "Isolates browsing context to prevent side-channel attacks (Spectre)",
        "weight": 10,
        "recommendation": "Add: Cross-Origin-Opener-Policy: same-origin",
    },
    {
        "name": "Cross-Origin-Resource-Policy",
        "description": "Prevents resources from being loaded by other origins (Spectre mitigation)",
        "weight": 10,
        "recommendation": "Add: Cross-Origin-Resource-Policy: same-origin",
    },
    {
        "name": "Cross-Origin-Embedder-Policy",
        "description": "Required for SharedArrayBuffer; prevents loading non-CORS resources",
        "weight": 5,
        "recommendation": "Add: Cross-Origin-Embedder-Policy: require-corp",
    },
]

# Bonus headers to note (not scored)
_INFO_HEADERS = [
    "Server", "X-Powered-By", "X-AspNet-Version", "X-Generator",
]


def http_security_audit(
    url: str,
    timeout: float = 10.0,
    follow_redirects: bool = True,
) -> dict[str, Any]:
    """
    Audit HTTP security headers of a URL and produce a letter grade.

    Args:
        url: Target URL (e.g. 'https://example.com'). HTTP scheme added if missing.
        timeout: Request timeout in seconds.
        follow_redirects: Whether to follow HTTP redirects.

    Returns:
        Dict with headers found/missing, per-header analysis, grade,
        score (0-100), and actionable recommendations.
    """
    if _requests is None:
        return {
            "success": False,
            "error": "requests library is not installed. Run: pip install requests",
            "url": url,
        }

    # Ensure URL has a scheme
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        resp = _requests.get(
            url,
            timeout=timeout,
            allow_redirects=follow_redirects,
            headers={"User-Agent": "OSINT-SecurityAuditor/1.0"},
        )
    except Exception as e:
        return {"success": False, "error": f"Request failed: {e}", "url": url}

    headers = resp.headers
    total_weight = sum(h["weight"] for h in _SECURITY_HEADERS)
    earned_weight = 0

    headers_analysis: list[dict[str, Any]] = []
    missing: list[dict[str, str]] = []
    found: dict[str, str] = {}

    for hdef in _SECURITY_HEADERS:
        name = hdef["name"]
        value = headers.get(name)
        if value:
            earned_weight += hdef["weight"]
            found[name] = value
            headers_analysis.append({
                "header": name,
                "status": "present",
                "value": value,
                "description": hdef["description"],
            })
        else:
            missing.append({
                "header": name,
                "description": hdef["description"],
                "recommendation": hdef["recommendation"],
            })
            headers_analysis.append({
                "header": name,
                "status": "missing",
                "description": hdef["description"],
                "recommendation": hdef["recommendation"],
            })

    # Score as percentage of weights achieved
    score = int((earned_weight / total_weight) * 100) if total_weight > 0 else 0

    # Letter grade
    if score >= 90:
        grade = "A"
    elif score >= 75:
        grade = "B"
    elif score >= 55:
        grade = "C"
    elif score >= 35:
        grade = "D"
    else:
        grade = "F"

    # Information headers that leak server details
    info_leaks: list[dict[str, str]] = []
    for ih in _INFO_HEADERS:
        val = headers.get(ih)
        if val:
            info_leaks.append({
                "header": ih,
                "value": val,
                "risk": "Server information disclosure — remove in production",
            })

    return {
        "success": True,
        "url": url,
        "final_url": resp.url,
        "status_code": resp.status_code,
        "grade": grade,
        "score": score,
        "headers_present": len(found),
        "headers_missing": len(missing),
        "headers_total": len(_SECURITY_HEADERS),
        "analysis": headers_analysis,
        "missing_headers": missing,
        "found_headers": found,
        "information_disclosure": info_leaks,
        "uses_https": resp.url.startswith("https://"),
    }
