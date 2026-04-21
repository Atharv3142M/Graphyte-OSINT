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


def reverse_ip_lookup(target: str) -> dict[str, Any]:
    try:
        ip = _resolve_target(target)
    except Exception as exc:
        return {"success": False, "error": f"Unable to resolve target: {exc}", "target": target}

    try:
        resp = requests.get(f"https://api.hackertarget.com/reverseiplookup/?q={ip}", timeout=15)
        resp.raise_for_status()
        text = resp.text.strip()
    except Exception as exc:
        return {"success": False, "error": f"Reverse IP lookup failed: {exc}", "target": target, "ip": ip}

    if "error" in text.lower():
        return {"success": False, "error": text, "target": target, "ip": ip}

    domains = [line.strip() for line in text.splitlines() if line.strip()]
    return {
        "success": True,
        "target": target,
        "ip": ip,
        "domains": domains,
        "count": len(domains),
        "source": "hackertarget",
    }
