"""
Playbook router — maps detected input types to the relevant OSINT modules.

This module defines the routing matrix used by POST /api/investigate to fan out
an investigation to all applicable modules simultaneously.
"""

from __future__ import annotations

from typing import Final

# ── Routing map ────────────────────────────────────────────────────────────────
#
# Each input type maps to a list of Celery task names.
# Task names MUST match those registered via @celery_app.task(name="tasks.xxx").
#
# intensity tiers:
#   low       — passive, keyless modules only (fast, no API keys)
#   standard  — fast modules (default, < 10s expected per module)
#   aggressive — all modules including slow ones (deep scraper, social hunter)

ROUTING_MAP: Final[dict[str, list[str]]] = {
    # ── IPv4 ──────────────────────────────────────────────────────────────────
    "ipv4": [
        "tasks.dns_intel",
        "tasks.whois_lookup",
        "tasks.port_scan",
        "tasks.cyberninja_passive",
        "tasks.xrecon",
        "tasks.shodan_recon",
        "tasks.censys_recon",
        "tasks.ip_geolocation",
        "tasks.reverse_ip_lookup",
        "tasks.bgp_asn_lookup",
    ],

    # ── IPv6 ──────────────────────────────────────────────────────────────────
    "ipv6": [
        "tasks.whois_lookup",
        "tasks.cyberninja_passive",
        "tasks.xrecon",
    ],

    # ── CIDR ──────────────────────────────────────────────────────────────────
    "cidr": [
        "tasks.dns_intel",
        "tasks.whois_lookup",
        "tasks.port_scan",
        "tasks.cyberninja_passive",
    ],

    # ── Domain ────────────────────────────────────────────────────────────────
    "domain": [
        "tasks.dns_intel",
        "tasks.whois_lookup",
        "tasks.ssl_analyze",
        "tasks.http_security",
        "tasks.tech_stack",
        "tasks.cert_transparency",
        "tasks.robots_sitemap",
        "tasks.favicon_hash",
        "tasks.cyberninja_passive",
        "tasks.xrecon",
        "tasks.wayback_machine",
        "tasks.ip_geolocation",
        "tasks.reverse_ip_lookup",
    ],

    # ── URL ───────────────────────────────────────────────────────────────────
    "url": [
        "tasks.dns_intel",
        "tasks.ssl_analyze",
        "tasks.http_security",
        "tasks.tech_stack",
        "tasks.robots_sitemap",
        "tasks.favicon_hash",
        "tasks.deep_scraper",
        "tasks.graysentinel_ingest",
        "tasks.xrecon",
        "tasks.wayback_machine",
    ],

    # ── Email ──────────────────────────────────────────────────────────────────
    "email": [
        "tasks.email_reputation",
        "tasks.username_permutator",
        "tasks.social_hunter",
        "tasks.cert_transparency",
        "tasks.xrecon",
    ],

    # ── Username ───────────────────────────────────────────────────────────────
    "username": [
        "tasks.username_permutator",
        "tasks.github_osint",
        "tasks.social_hunter",
        "tasks.sherlock_hunt",
        "tasks.xrecon",
        "tasks.cyberninja_passive",
    ],

    # ── Hashes ─────────────────────────────────────────────────────────────────
    "hash_md5": [
        "tasks.xrecon",
    ],
    "hash_sha1": [
        "tasks.xrecon",
    ],
    "hash_sha256": [
        "tasks.xrecon",
    ],

    # ── Phone ───────────────────────────────────────────────────────────────────
    "phone": [
        "tasks.phone_intel",
        "tasks.xrecon",
        "tasks.cyberninja_passive",
    ],

    # ── ASN ────────────────────────────────────────────────────────────────────
    "asn": [
        "tasks.whois_lookup",
        "tasks.cyberninja_passive",
        "tasks.bgp_asn_lookup",
    ],

    # ── Company (low confidence — manual confirm) ─────────────────────────────────
    "company": [
        "tasks.dns_intel",
        "tasks.whois_lookup",
        "tasks.cyberninja_passive",
        "tasks.xrecon",
    ],
}

# ── Module-friendly display names (for UI) ────────────────────────────────────

MODULE_NAMES: Final[dict[str, str]] = {
    "tasks.dns_intel": "DNS Intel",
    "tasks.whois_lookup": "WHOIS",
    "tasks.ssl_analyze": "SSL Analysis",
    "tasks.http_security": "HTTP Security",
    "tasks.tech_stack": "Tech Stack",
    "tasks.cert_transparency": "Cert Transparency",
    "tasks.port_scan": "Port Scan",
    "tasks.social_hunter": "Social Hunter",
    "tasks.deep_scraper": "Deep Scraper",
    "tasks.cyberninja_passive": "CyberNinja",
    "tasks.xrecon": "xRecon",
    "tasks.shodan_recon": "Shodan Recon",
    "tasks.censys_recon": "Censys Recon",
    "tasks.graysentinel_ingest": "GraySentinel",
    "tasks.metadata_extract": "Metadata Extract",
    "tasks.ip_geolocation": "IP Geolocation",
    "tasks.reverse_ip_lookup": "Reverse IP",
    "tasks.bgp_asn_lookup": "BGP / ASN",
    "tasks.wayback_machine": "Wayback Machine",
    "tasks.email_header_analyzer": "Email Header",
    "tasks.sherlock_hunt": "Sherlock",
    "tasks.robots_sitemap": "Robots & Sitemap",
    "tasks.favicon_hash": "Favicon Hash",
    "tasks.username_permutator": "Username Permutator",
    "tasks.github_osint": "GitHub OSINT",
    "tasks.phone_intel": "Phone Intel",
    "tasks.email_reputation": "Email Reputation",
}

# ── Intensity tiers ────────────────────────────────────────────────────────────

INTENSITY_EXCLUSIONS: Final[dict[str, set[str]]] = {
    "low": {
        "tasks.port_scan",
        "tasks.deep_scraper",
        "tasks.shodan_recon",
        "tasks.censys_recon",
        "tasks.graysentinel_ingest",
        "tasks.social_hunter",
        "tasks.sherlock_hunt",
    },
    "standard": set(),
    "aggressive": set(),
}


def get_modules_for_types(types: list[str], intensity: str = "standard") -> list[str]:
    """
    Resolve the full list of modules for the given input types and intensity.

    Returns a deduplicated list of task names in execution order.
    """
    excluded = INTENSITY_EXCLUSIONS.get(intensity, set())
    seen: set[str] = set()
    modules: list[str] = []

    for input_type in types:
        for task in ROUTING_MAP.get(input_type, []):
            if task not in seen and task not in excluded:
                seen.add(task)
                modules.append(task)

    return modules


def get_module_display_names(modules: list[str]) -> list[str]:
    """Map task names to friendly display names for the UI."""
    return [MODULE_NAMES.get(t, t.split(".")[-1].replace("_", " ").title()) for t in modules]