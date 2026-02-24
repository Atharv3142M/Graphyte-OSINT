"""
STIX 2.1 standardization helpers for OSINT module outputs.

This is intentionally minimal: it produces simple bundles with ipv4-addr,
domain-name, and note objects that can be ingested into Neo4j.
"""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, List


def _bundle_id() -> str:
    return f"bundle--{uuid.uuid4()}"


def _obj_id(prefix: str) -> str:
    return f"{prefix}--{uuid.uuid4()}"


def build_stix_bundle(module_name: str, result: Dict[str, Any]) -> Dict[str, Any] | None:
    """
    Convert a module result into a STIX 2.1 bundle (very small subset).
    Returns None if no meaningful mapping exists.
    """
    if not result or not result.get("success", True) or result.get("error"):
        return None

    objects: List[Dict[str, Any]] = []
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    if module_name == "shodan_recon":
        data = result.get("data") or {}
        if data.get("type") == "host":
            ipv4 = result.get("target")
            if ipv4:
                objects.append(
                    {
                        "type": "ipv4-addr",
                        "id": _obj_id("ipv4-addr"),
                        "value": ipv4,
                        "x_shodan_ports": data.get("ports", []),
                        "x_shodan_city": data.get("city"),
                        "x_shodan_country": data.get("country_name"),
                        "x_shodan_org": data.get("org"),
                        "x_shodan_isp": data.get("isp"),
                    }
                )
        elif data.get("type") == "domain":
            for match in data.get("matches", []):
                ip = match.get("ip_str")
                if ip:
                    objects.append(
                        {
                            "type": "ipv4-addr",
                            "id": _obj_id("ipv4-addr"),
                            "value": ip,
                            "x_shodan_port": match.get("port"),
                            "x_shodan_city": match.get("city"),
                            "x_shodan_country": match.get("country_name"),
                        }
                    )

    elif module_name == "port_scanner":
        host = result.get("host")
        for p in result.get("open_ports", []):
            port = p.get("port")
            if host and port is not None:
                objects.append(
                    {
                        "type": "network-traffic",
                        "id": _obj_id("network-traffic"),
                        "dst_ref": _obj_id("ipv4-addr"),
                        "dst_port": port,
                        "protocols": ["tcp"],
                        "x_open": True,
                        "x_host": host,
                    }
                )

    elif module_name == "scraper":
        # Represent emails and phone numbers as notes for now.
        emails = result.get("found_emails", [])
        phones = result.get("found_numbers", [])
        if emails or phones:
            objects.append(
                {
                    "type": "note",
                    "id": _obj_id("note"),
                    "created": now,
                    "modified": now,
                    "abstract": "Contact information discovered by scraper",
                    "content": {
                        "emails": emails,
                        "phone_numbers": phones,
                    },
                }
            )

    if not objects:
        return None

    return {
        "type": "bundle",
        "id": _bundle_id(),
        "spec_version": "2.1",
        "objects": objects,
    }

