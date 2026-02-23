"""
Censys reconnaissance module.
Extracted from am0nt31r0/OSINT-Search - core methodology: API requests to Censys.
Accepts arguments programmatically for FastAPI/Celery integration.
"""
from __future__ import annotations

from typing import Any

try:
    import censys.ipv4
    import validators
except ImportError:
    censys = None
    validators = None

# Dummy placeholders - replace with env/config in production
CENSYS_API_ID_PLACEHOLDER = "YOUR_CENSYS_API_ID"
CENSYS_API_SECRET_PLACEHOLDER = "YOUR_CENSYS_API_SECRET"


def censys_search(
    target: str,
    api_id: str | None = None,
    api_secret: str | None = None,
) -> dict[str, Any]:
    """
    Query Censys for IP reconnaissance (protocols, location, AS, TLS certs).

    Args:
        target: IPv4 address to look up.
        api_id: Censys API ID.
        api_secret: Censys API secret.

    Returns:
        Dict with protocols, location, autonomous_system, services (443/53), etc.
    """
    cid = api_id or CENSYS_API_ID_PLACEHOLDER
    csecret = api_secret or CENSYS_API_SECRET_PLACEHOLDER

    result: dict[str, Any] = {"target": target, "success": False, "data": None, "error": None}

    if not censys or not validators:
        result["error"] = "censys/validators packages required"
        return result

    if not validators.ip_address.ipv4(target):
        result["error"] = "Censys requires a valid IPv4 address"
        return result

    try:
        c = censys.ipv4.CensysIPv4(api_id=cid, api_secret=csecret)
        data = c.view(target)

        out: dict[str, Any] = {
            "ip": data.get("ip"),
            "protocols": data.get("protocols", []),
            "location": data.get("location", {}),
            "autonomous_system": data.get("autonomous_system", {}),
            "updated_at": data.get("updated_at"),
        }

        if "443" in data and "https" in data["443"]:
            tls_data = data["443"]["https"].get("tls", {}).get("certificate", {}).get("parsed", {})
            ext = tls_data.get("extensions", {}).get("subject_alt_name", {})
            out["https_443"] = {
                "dns_names": ext.get("dns_names", []),
                "ip_addresses": ext.get("ip_addresses", []),
                "issuer": tls_data.get("issuer"),
            }

        if "53" in data and "dns" in data["53"]:
            lookup = data["53"]["dns"].get("lookup", {})
            out["dns_53"] = {
                "open_resolver": lookup.get("open_resolver"),
                "answers": lookup.get("answers", []),
            }

        result["data"] = out
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)

    return result
