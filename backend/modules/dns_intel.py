"""
DNS Intelligence Engine - Comprehensive DNS reconnaissance.
Collects all record types, parses SPF/DMARC, discovers subdomains via brute-force.
Zero API keys required — uses dnspython for all lookups.
"""
from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

try:
    import dns.resolver
    import dns.reversename
    import dns.exception
except ImportError:
    dns = None  # type: ignore[assignment]

# Common subdomains for brute-force discovery
_SUBDOMAIN_WORDLIST = [
    "www", "mail", "ftp", "webmail", "smtp", "pop", "imap", "blog", "shop",
    "store", "api", "dev", "staging", "test", "beta", "demo", "admin", "portal",
    "app", "m", "mobile", "cdn", "media", "static", "assets", "img", "images",
    "ns1", "ns2", "ns3", "dns", "dns1", "dns2", "mx", "mx1", "mx2",
    "vpn", "remote", "gateway", "proxy", "firewall", "ssh", "git", "gitlab",
    "jenkins", "ci", "cd", "docker", "k8s", "kubernetes", "registry",
    "db", "database", "mysql", "postgres", "redis", "mongo", "elastic",
    "search", "analytics", "monitor", "grafana", "prometheus", "kibana",
    "auth", "login", "sso", "oauth", "id", "identity", "accounts",
    "docs", "wiki", "help", "support", "status", "health",
    "cloud", "aws", "azure", "gcp", "s3", "storage",
    "intranet", "internal", "corp", "office", "exchange",
    "old", "new", "v2", "v3", "legacy", "backup", "bak",
    "cpanel", "whm", "plesk", "panel", "dashboard",
    "calendar", "chat", "meet", "video", "conference",
    "crm", "erp", "hr", "finance", "billing", "pay", "payment",
]


def _resolve_records(domain: str, rdtype: str) -> list[str]:
    """Resolve DNS records of a given type. Returns list of string values."""
    if dns is None:
        return []
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 10
        answers = resolver.resolve(domain, rdtype)
        return [str(rdata) for rdata in answers]
    except Exception:
        return []


def _parse_spf(txt_records: list[str]) -> dict[str, Any] | None:
    """Find and parse SPF record from TXT records."""
    for rec in txt_records:
        cleaned = rec.strip('"').strip("'")
        if cleaned.lower().startswith("v=spf1"):
            mechanisms = cleaned.split()
            return {
                "raw": cleaned,
                "mechanisms": mechanisms[1:],  # skip v=spf1
                "has_all_fail": "-all" in mechanisms,
                "has_all_softfail": "~all" in mechanisms,
                "has_all_pass": "+all" in mechanisms,
                "assessment": (
                    "strong" if "-all" in mechanisms
                    else "moderate" if "~all" in mechanisms
                    else "weak" if "+all" in mechanisms
                    else "neutral"
                ),
            }
    return None


def _parse_dmarc(domain: str) -> dict[str, Any] | None:
    """Resolve and parse DMARC record."""
    dmarc_domain = f"_dmarc.{domain}"
    records = _resolve_records(dmarc_domain, "TXT")
    for rec in records:
        cleaned = rec.strip('"').strip("'")
        if cleaned.lower().startswith("v=dmarc1"):
            tags: dict[str, str] = {}
            for part in cleaned.split(";"):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    tags[k.strip().lower()] = v.strip()
            policy = tags.get("p", "none")
            return {
                "raw": cleaned,
                "policy": policy,
                "subdomain_policy": tags.get("sp", policy),
                "percentage": int(tags.get("pct", "100")),
                "rua": tags.get("rua", ""),
                "ruf": tags.get("ruf", ""),
                "assessment": (
                    "strong" if policy == "reject"
                    else "moderate" if policy == "quarantine"
                    else "weak"
                ),
            }
    return None


def _reverse_dns(ip: str) -> str | None:
    """Perform reverse DNS lookup for an IP address."""
    if dns is None:
        return None
    try:
        rev_name = dns.reversename.from_address(ip)
        answers = dns.resolver.resolve(rev_name, "PTR")
        return str(list(answers)[0])
    except Exception:
        return None


def _check_subdomain(subdomain: str, domain: str) -> dict[str, Any] | None:
    """Check if a subdomain resolves. Returns info dict if found."""
    fqdn = f"{subdomain}.{domain}"
    ips = _resolve_records(fqdn, "A")
    if ips:
        return {"subdomain": subdomain, "fqdn": fqdn, "ips": ips}
    return None


def dns_recon(
    domain: str,
    discover_subdomains: bool = True,
    subdomain_wordlist: list[str] | None = None,
    max_workers: int = 15,
) -> dict[str, Any]:
    """
    Full DNS intelligence gathering for a domain.

    Args:
        domain: Target domain (e.g. 'example.com').
        discover_subdomains: Whether to brute-force common subdomains.
        subdomain_wordlist: Custom wordlist; uses built-in ~100 entries if None.
        max_workers: Thread pool size for subdomain discovery.

    Returns:
        Dict with all DNS records, parsed SPF/DMARC, discovered subdomains,
        reverse DNS, and an overall security assessment.
    """
    if dns is None:
        return {
            "success": False,
            "error": "dnspython is not installed. Run: pip install dnspython",
            "domain": domain,
        }

    domain = domain.strip().lower().lstrip("http://").lstrip("https://").split("/")[0]

    result: dict[str, Any] = {
        "success": True,
        "domain": domain,
        "records": {},
        "spf": None,
        "dmarc": None,
        "subdomains_found": [],
        "reverse_dns": {},
        "security_assessment": {},
    }

    # Collect all standard record types
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]
    for rtype in record_types:
        records = _resolve_records(domain, rtype)
        if records:
            result["records"][rtype] = records

    # Parse email security from TXT records
    txt_records = result["records"].get("TXT", [])
    result["spf"] = _parse_spf(txt_records)
    result["dmarc"] = _parse_dmarc(domain)

    # Reverse DNS for all A records
    a_records = result["records"].get("A", [])
    for ip in a_records:
        ptr = _reverse_dns(ip)
        if ptr:
            result["reverse_dns"][ip] = ptr

    # Subdomain discovery
    if discover_subdomains:
        wordlist = subdomain_wordlist or _SUBDOMAIN_WORDLIST
        found: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_check_subdomain, sub, domain): sub
                for sub in wordlist
            }
            for future in as_completed(futures):
                try:
                    sub_result = future.result()
                    if sub_result:
                        found.append(sub_result)
                except Exception:
                    pass
        found.sort(key=lambda x: x["subdomain"])
        result["subdomains_found"] = found

    # Security assessment
    issues: list[str] = []
    if not result["spf"]:
        issues.append("No SPF record found — email spoofing is possible")
    elif result["spf"].get("assessment") == "weak":
        issues.append("SPF uses +all — allows any server to send as this domain")
    if not result["dmarc"]:
        issues.append("No DMARC record found — no email authentication enforcement")
    elif result["dmarc"].get("assessment") == "weak":
        issues.append("DMARC policy is 'none' — monitoring only, no enforcement")

    mx_records = result["records"].get("MX", [])
    if not mx_records:
        issues.append("No MX records — domain may not receive email")

    score = max(0, 100 - (len(issues) * 25))
    result["security_assessment"] = {
        "score": score,
        "grade": "A" if score >= 90 else "B" if score >= 70 else "C" if score >= 50 else "F",
        "issues": issues,
    }

    return result
