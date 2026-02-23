"""
Shodan reconnaissance module.
Extracted from am0nt31r0/OSINT-Search - core methodology: API requests to Shodan.
Accepts arguments programmatically for FastAPI/Celery integration.
"""
from __future__ import annotations

from typing import Any

try:
    import shodan
    import validators
except ImportError:
    shodan = None
    validators = None

SHODAN_API_KEY_PLACEHOLDER = "YOUR_SHODAN_API_KEY"


def shodan_search(target: str, api_key: str | None = None) -> dict[str, Any]:
    """
    Query Shodan for host/domain reconnaissance.

    Args:
        target: IP address or domain to search.
        api_key: Shodan API key. Uses placeholder if not provided.

    Returns:
        Dict with host info, ports, hostnames, location; or error details.
    """
    key = api_key or SHODAN_API_KEY_PLACEHOLDER
    if not shodan or not validators:
        return {"error": "shodan/validators packages required", "success": False}

    result: dict[str, Any] = {"target": target, "success": False, "data": None, "error": None}

    try:
        api = shodan.Shodan(key)

        if validators.ip_address.ipv4(target):
            host = api.host(target)
            result["data"] = {
                "type": "host",
                "city": host.get("city"),
                "country_name": host.get("country_name"),
                "postal_code": host.get("postal_code"),
                "longitude": host.get("longitude"),
                "latitude": host.get("latitude"),
                "os": host.get("os"),
                "org": host.get("org"),
                "isp": host.get("isp"),
                "ports": host.get("ports", []),
                "hostnames": host.get("hostnames", []),
            }
        elif validators.domain(target):
            search_result = api.search(target)
            matches = []
            for service in search_result.get("matches", []):
                matches.append({
                    "ip_str": service.get("ip_str"),
                    "city": service.get("location", {}).get("city"),
                    "country_name": service.get("location", {}).get("country_name"),
                    "postal_code": service.get("location", {}).get("postal_code"),
                    "longitude": service.get("location", {}).get("longitude"),
                    "latitude": service.get("location", {}).get("latitude"),
                    "os": service.get("os"),
                    "org": service.get("org"),
                    "isp": service.get("isp"),
                    "port": service.get("port"),
                    "hostnames": service.get("hostnames", []),
                })
            result["data"] = {"type": "domain", "matches": matches}
        else:
            result["error"] = "Invalid target: must be IPv4 or domain"
            return result

        result["success"] = True
    except shodan.APIError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)

    return result
