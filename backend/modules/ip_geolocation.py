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


def ip_geolocation(target: str) -> dict[str, Any]:
    try:
        ip = _resolve_target(target)
    except Exception as exc:
        return {"success": False, "error": f"Unable to resolve target: {exc}", "target": target}

    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {"success": False, "error": f"Geolocation lookup failed: {exc}", "target": target, "ip": ip}

    if data.get("status") != "success":
        return {"success": False, "error": data.get("message", "Unknown error"), "target": target, "ip": ip}

    return {
        "success": True,
        "target": target,
        "ip": ip,
        "country": data.get("country"),
        "region": data.get("regionName"),
        "city": data.get("city"),
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "isp": data.get("isp"),
        "org": data.get("org"),
        "asn": data.get("as"),
        "timezone": data.get("timezone"),
        "mobile": data.get("mobile"),
        "proxy": data.get("proxy"),
        "hosting": data.get("hosting"),
        "source": "ip-api.com",
    }
