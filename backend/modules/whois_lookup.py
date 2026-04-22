"""
WHOIS Domain Intelligence - Registration data, registrar info, domain age.
Zero API keys required — uses python-whois library.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    import whois as python_whois
except ImportError:
    python_whois = None  # type: ignore[assignment]


def _to_str(val: Any) -> str | None:
    """Safely convert a value to string, handling lists and None."""
    if val is None:
        return None
    if isinstance(val, list):
        return str(val[0]) if val else None
    return str(val)


def _to_date_str(val: Any) -> str | None:
    """Convert a date/datetime or list-of-dates to ISO string."""
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0] if val else None
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _calc_domain_age(creation_date: Any) -> int | None:
    """Calculate domain age in days from creation date."""
    if creation_date is None:
        return None
    if isinstance(creation_date, list):
        creation_date = creation_date[0] if creation_date else None
    if not isinstance(creation_date, datetime):
        return None
    now = datetime.now(timezone.utc)
    if creation_date.tzinfo is None:
        creation_date = creation_date.replace(tzinfo=timezone.utc)
    delta = now - creation_date
    return delta.days


def whois_lookup(domain: str) -> dict[str, Any]:
    """
    Perform WHOIS lookup for a domain.

    Args:
        domain: Target domain (e.g. 'example.com').

    Returns:
        Dict with registrar, dates, nameservers, status codes,
        domain age, and raw WHOIS text.
    """
    if python_whois is None:
        return {
            "success": False,
            "error": "python-whois is not installed. Run: pip install python-whois",
            "domain": domain,
        }

    domain = domain.strip().lower().replace("https://", "", 1).replace("http://", "", 1).split("/")[0]

    try:
        w = python_whois.whois(domain)
    except Exception as e:
        return {"success": False, "error": str(e), "domain": domain}

    # Normalize nameservers to lowercase sorted list
    nameservers = w.name_servers
    if isinstance(nameservers, list):
        nameservers = sorted(set(ns.lower() for ns in nameservers if ns))
    elif nameservers:
        nameservers = [str(nameservers).lower()]
    else:
        nameservers = []

    # Status codes
    status = w.status
    if isinstance(status, str):
        status = [status]
    elif status is None:
        status = []

    domain_age = _calc_domain_age(w.creation_date)

    result: dict[str, Any] = {
        "success": True,
        "domain": domain,
        "registrar": _to_str(w.registrar),
        "registrant_org": _to_str(getattr(w, "org", None)),
        "registrant_country": _to_str(getattr(w, "country", None)),
        "creation_date": _to_date_str(w.creation_date),
        "expiry_date": _to_date_str(w.expiration_date),
        "updated_date": _to_date_str(w.updated_date),
        "domain_age_days": domain_age,
        "nameservers": nameservers,
        "status": status,
        "dnssec": _to_str(getattr(w, "dnssec", None)),
        "emails": w.emails if isinstance(w.emails, list) else ([w.emails] if w.emails else []),
    }

    # Flag suspicious domains (very young or about to expire)
    warnings: list[str] = []
    if domain_age is not None and domain_age < 30:
        warnings.append(f"Domain is very new ({domain_age} days old) — potential phishing")
    if domain_age is not None and domain_age < 365:
        warnings.append(f"Domain is less than 1 year old ({domain_age} days)")

    exp = w.expiration_date
    if isinstance(exp, list):
        exp = exp[0] if exp else None
    if isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days_left = (exp - datetime.now(timezone.utc)).days
        if days_left < 0:
            warnings.append("Domain has EXPIRED")
        elif days_left < 30:
            warnings.append(f"Domain expires in {days_left} days")

    result["warnings"] = warnings
    return result
