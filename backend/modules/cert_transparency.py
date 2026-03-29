"""
cert_transparency.py - Subdomain discovery via Certificate Transparency logs.

Scrapes crt.sh (free, no API key required) to discover subdomains for a given domain.
Certificate Transparency logs are public records of all SSL/TLS certificates issued,
making this an excellent passive reconnaissance technique.

Output format:
{
    "success": true,
    "domain": "<target>",
    "subdomains_found": 123,
    "subdomains": [
        {"subdomain": "www.example.com", "cert_id": "...", "issued": "..."},
        ...
    ],
    "wildcards": ["*.example.com", ...],
    "unique_domains": ["example.com", "www.example.com", ...],
}
"""
from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote


@dataclass
class CertificateEntry:
    """Single certificate entry from CT logs."""
    subdomain: str
    cert_id: Optional[str] = None
    issuer: Optional[str] = None
    issued_date: Optional[str] = None
    expiry_date: Optional[str] = None
    is_wildcard: bool = False


@dataclass
class CertTransparencyResult:
    """Complete result from certificate transparency search."""
    domain: str
    total_certs: int = 0
    subdomains_found: int = 0
    wildcards_found: int = 0
    certificates: list[CertificateEntry] = field(default_factory=list)
    unique_subdomains: list[str] = field(default_factory=list)
    wildcards: list[str] = field(default_factory=list)
    search_time_ms: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "success": True,
            "domain": self.domain,
            "total_certs": self.total_certs,
            "subdomains_found": self.subdomains_found,
            "wildcards_found": self.wildcards_found,
            "certificates": [
                {
                    "subdomain": c.subdomain,
                    "cert_id": c.cert_id,
                    "issuer": c.issuer,
                    "issued_date": c.issued_date,
                    "expiry_date": c.expiry_date,
                    "is_wildcard": c.is_wildcard,
                }
                for c in self.certificates
            ],
            "unique_subdomains": self.unique_subdomains,
            "wildcards": self.wildcards,
            "search_time_ms": round(self.search_time_ms, 2) if self.search_time_ms else None,
        }


# crt.sh API endpoints
CRT_SH_SEARCH_URL = "https://crt.sh/?q={domain}&output=json"
CRT_SH_WEB_URL = "https://crt.sh/?q={domain}"


def normalize_subdomain(subdomain: str, base_domain: str) -> str:
    """
    Normalize a subdomain entry.

    - Strip leading/trailing whitespace
    - Handle wildcard entries (*.example.com)
    - Ensure consistent formatting
    """
    subdomain = subdomain.strip().lower()

    # Handle wildcard certificates
    if subdomain.startswith("*."):
        return subdomain

    # Remove trailing dots
    subdomain = subdomain.rstrip(".")

    return subdomain


def extract_subdomains_from_html(html_content: str, base_domain: str) -> list[str]:
    """
    Extract subdomains from crt.sh HTML response.

    This is a fallback when JSON parsing fails. Uses regex to find
    domain patterns in the HTML table.
    """
    # Pattern to match domain names
    domain_pattern = r"[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z]{2,})+"

    matches = re.findall(domain_pattern, html_content)

    # Filter to only include subdomains of the target
    base_domain_lower = base_domain.lower()
    subdomains = set()

    for match in matches:
        match_lower = match.lower()
        if match_lower.endswith(base_domain_lower):
            subdomains.add(match_lower)

    return list(subdomains)


async def fetch_crt_sh_json(domain: str) -> Optional[list[dict]]:
    """
    Fetch certificate data from crt.sh JSON API.

    Args:
        domain: Domain to search for

    Returns:
        List of certificate entries or None if failed
    """
    import aiohttp

    url = CRT_SH_SEARCH_URL.format(domain=quote(domain))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json,text/html,*/*",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return await response.json()
                    else:
                        # Try to parse as JSON anyway
                        text = await response.text()
                        try:
                            import json
                            return json.loads(text)
                        except:
                            return None
                else:
                    return None
    except Exception:
        return None


async def fetch_crt_sh_html(domain: str) -> Optional[str]:
    """
    Fetch certificate data from crt.sh HTML (fallback).

    Args:
        domain: Domain to search for

    Returns:
        HTML content or None if failed
    """
    import aiohttp

    url = CRT_SH_WEB_URL.format(domain=quote(domain))

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
    except Exception:
        pass

    return None


def parse_cert_entry(entry: dict, base_domain: str) -> Optional[CertificateEntry]:
    """
    Parse a single certificate entry from crt.sh response.

    Args:
        entry: Raw certificate entry from crt.sh
        base_domain: Base domain for normalization

    Returns:
        CertificateEntry or None if invalid
    """
    # crt.sh returns entries with 'name_value' containing the domain(s)
    name_value = entry.get("name_value", "")

    if not name_value or not isinstance(name_value, str):
        return None

    # Split on newlines - a single cert can cover multiple domains
    names = name_value.split("\n")

    # Process the first valid name
    for name in names:
        normalized = normalize_subdomain(name, base_domain)
        if normalized and base_domain.lower() in normalized.lower():
            return CertificateEntry(
                subdomain=normalized,
                cert_id=str(entry.get("id", "")),
                issuer=entry.get("issuer_name", ""),
                issued_date=entry.get("not_before", ""),
                expiry_date=entry.get("not_after", ""),
                is_wildcard=normalized.startswith("*."),
            )

    return None


async def search_certificates(
    domain: str,
    use_html_fallback: bool = True,
) -> CertTransparencyResult:
    """
    Search certificate transparency logs for subdomains.

    Args:
        domain: Domain to search for
        use_html_fallback: Whether to try HTML scraping if JSON fails

    Returns:
        CertTransparencyResult with all findings
    """
    start_time = time.perf_counter()

    # Validate domain
    if not domain or len(domain) < 3:
        return CertTransparencyResult(
            domain=domain,
            certificates=[
                CertificateEntry(
                    subdomain="",
                    is_wildcard=False,
                )
            ],
            search_time_ms=(time.perf_counter() - start_time) * 1000,
        )

    # Clean domain
    domain = domain.lower().strip()
    domain = domain.rstrip(".")

    # Try JSON API first
    json_data = await fetch_crt_sh_json(domain)

    certificates = []
    seen_subdomains = set()

    if json_data and isinstance(json_data, list):
        for entry in json_data:
            cert = parse_cert_entry(entry, domain)
            if cert and cert.subdomain not in seen_subdomains:
                certificates.append(cert)
                seen_subdomains.add(cert.subdomain)

    # Fallback to HTML scraping if JSON failed or returned empty
    elif use_html_fallback and (not json_data or not isinstance(json_data, list)):
        html_content = await fetch_crt_sh_html(domain)
        if html_content:
            html_subdomains = extract_subdomains_from_html(html_content, domain)
            for subdomain in html_subdomains:
                if subdomain not in seen_subdomains:
                    certificates.append(
                        CertificateEntry(
                            subdomain=subdomain,
                            is_wildcard=subdomain.startswith("*."),
                        )
                    )
                    seen_subdomains.add(subdomain)

    # Separate wildcards and regular subdomains
    wildcards = [c.subdomain for c in certificates if c.is_wildcard]
    regular_subdomains = [c.subdomain for c in certificates if not c.is_wildcard]

    end_time = time.perf_counter()

    return CertTransparencyResult(
        domain=domain,
        total_certs=len(certificates),
        subdomains_found=len(regular_subdomains),
        wildcards_found=len(wildcards),
        certificates=certificates,
        unique_subdomains=sorted(regular_subdomains),
        wildcards=sorted(wildcards),
        search_time_ms=(end_time - start_time) * 1000,
    )


def cert_transparency(
    domain: str,
    use_html_fallback: bool = True,
) -> dict:
    """
    Main entry point - search certificate transparency logs for subdomains.

    Args:
        domain: Domain to search for
        use_html_fallback: Whether to try HTML scraping if JSON fails

    Returns:
        Dict with findings (compatible with STIX pipeline)
    """
    import asyncio

    result = asyncio.run(search_certificates(domain, use_html_fallback))
    return result.to_dict()


if __name__ == "__main__":
    # CLI entry point for subprocess execution
    import json

    payload = json.loads(sys.stdin.read())
    domain = payload.get("domain", "")
    use_html_fallback = payload.get("use_html_fallback", True)

    result = cert_transparency(domain, use_html_fallback)
    print(json.dumps(result))
