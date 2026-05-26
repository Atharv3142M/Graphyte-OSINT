"""
Email reputation — disposable domain detection and DNS/MX validation (keyless).
Optional breach check is not performed (requires HIBP API key).
"""
from __future__ import annotations

import re
from typing import Any

try:
    import dns.resolver
except ImportError:
    dns = None  # type: ignore[assignment]

# High-signal disposable / throwaway domains (extendable)
_DISPOSABLE_DOMAINS: frozenset[str] = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "guerrillamail.net",
        "10minutemail.com",
        "tempmail.com",
        "temp-mail.org",
        "throwaway.email",
        "yopmail.com",
        "trashmail.com",
        "getnada.com",
        "sharklasers.com",
        "dispostable.com",
        "maildrop.cc",
        "fakeinbox.com",
        "mintemail.com",
        "emailondeck.com",
        "spamgourmet.com",
        "mytemp.email",
        "tempail.com",
        "burnermail.io",
    }
)

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]{1,64}@([a-zA-Z0-9.-]{1,253}\.[a-zA-Z]{2,})$")


def _mx_records(domain: str) -> tuple[list[str], str | None]:
    if dns is None:
        return [], "dnspython not installed"
    try:
        answers = dns.resolver.resolve(domain, "MX")
        hosts = sorted(str(r.exchange).rstrip(".") for r in answers)
        return hosts, None
    except Exception as e:
        return [], str(e)


def email_reputation_check(email: str) -> dict[str, Any]:
    """
    Assess email format, disposable provider, and MX presence.
    """
    raw = (email or "").strip().lower()
    if not raw:
        return {"success": False, "error": "Email is required", "email": raw}

    m = _EMAIL_RE.match(raw)
    if not m:
        return {"success": False, "error": "Invalid email format", "email": raw}

    local, domain = raw.split("@", 1)
    disposable = domain in _DISPOSABLE_DOMAINS or any(
        domain.endswith(f".{d}") for d in _DISPOSABLE_DOMAINS
    )

    mx_hosts, mx_error = _mx_records(domain)
    has_mx = len(mx_hosts) > 0

    risk = "low"
    flags: list[str] = []
    if disposable:
        risk = "high"
        flags.append("disposable_domain")
    if not has_mx:
        risk = "high" if risk != "high" else risk
        flags.append("no_mx_records")
    if len(local) <= 2:
        flags.append("short_local_part")

    return {
        "success": True,
        "email": raw,
        "local_part": local,
        "domain": domain,
        "disposable": disposable,
        "has_mx": has_mx,
        "mx_hosts": mx_hosts[:10],
        "mx_error": mx_error,
        "risk": risk,
        "flags": flags,
        "breach_check": {
            "available": False,
            "message": "Breach lookup requires HIBP API key (not configured)",
        },
    }
