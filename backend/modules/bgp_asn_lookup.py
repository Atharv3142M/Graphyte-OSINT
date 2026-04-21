from __future__ import annotations

import socket
from typing import Any

import requests


def _resolve_target(target: str) -> str:
    try:
        socket.inet_aton(target)
        return target
    except OSError:
        return socket.gethostbyname(target)


def bgp_asn_lookup(target: str) -> dict[str, Any]:
    asn_target = target.strip().upper()
    if asn_target.startswith("AS") and asn_target[2:].isdigit():
        asn = asn_target[2:]
        url = f"https://api.bgpview.io/asn/{asn}"
        mode = "asn"
    else:
        try:
            ip = _resolve_target(target)
        except Exception as exc:
            return {"success": False, "error": f"Unable to resolve target: {exc}", "target": target}
        url = f"https://api.bgpview.io/ip/{ip}"
        mode = "ip"

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"success": False, "error": f"BGP lookup failed: {exc}", "target": target}

    if data.get("status") != "ok":
        return {"success": False, "error": "BGPView returned non-ok status", "target": target}

    return {
        "success": True,
        "target": target,
        "mode": mode,
        "data": data.get("data", {}),
        "source": "bgpview.io",
    }
