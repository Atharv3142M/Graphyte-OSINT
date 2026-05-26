"""Run all OSINT modules via subprocess and validate JSON + normalized envelope."""
from __future__ import annotations

import json
import subprocess
import sys

from backend.normalize import normalize_result

MODULES: list[tuple[str, dict]] = [
    ("shodan_recon", {"target": "8.8.8.8"}),
    ("censys_recon", {"target": "8.8.8.8"}),
    ("scraper", {"urls": ["https://example.com"]}),
    ("port_scanner", {"host": "example.com", "ports": [80, 443]}),
    ("cyberninja_passive", {"usernames": ["admin"]}),
    ("xrecon", {"query": "example.com", "query_type": "auto"}),
    ("dns_intel", {"domain": "example.com", "brute_subdomains": False}),
    ("whois_lookup", {"domain": "example.com"}),
    ("ssl_analyzer", {"host": "example.com", "port": 443}),
    ("http_security", {"url": "https://example.com"}),
    ("tech_stack", {"url": "https://example.com"}),
    ("social_hunter", {"username": "torvalds", "max_concurrent": 5}),
    ("cert_transparency", {"domain": "example.com"}),
    ("deep_scraper", {"url": "https://example.com", "max_depth": 1, "max_pages": 2}),
    ("ip_geolocation", {"target": "8.8.8.8"}),
    ("reverse_ip_lookup", {"target": "8.8.8.8"}),
    ("bgp_asn_lookup", {"target": "AS15169"}),
    ("wayback_machine", {"target": "example.com", "limit": 5}),
    ("email_header_analyzer", {"raw_headers": "From: a@example.com\r\nTo: b@example.com\r\n"}),
    ("sherlock_hunt", {"username": "torvalds", "timeout": 5, "max_connections": 3}),
    ("robots_sitemap", {"domain": "github.com", "max_sitemap_urls": 10}),
    ("favicon_hash", {"domain": "github.com"}),
    ("username_permutator", {"seed": "john.doe", "max_results": 20}),
    ("github_osint", {"target": "torvalds", "lookup_type": "username"}),
    ("phone_intel", {"number": "+14155552671", "default_region": "US"}),
    ("email_reputation", {"email": "user@example.com"}),
]

TIMEOUTS: dict[str, int] = {
    "sherlock_hunt": 120,
    "social_hunter": 90,
    "deep_scraper": 90,
    "dns_intel": 90,
    "cyberninja_passive": 60,
    "github_osint": 30,
    "robots_sitemap": 45,
}


def _parse_stdout(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def main() -> int:
    ok_count = 0
    fail_count = 0

    for mod, pload in MODULES:
        print(f"Testing {mod}...", flush=True)
        timeout = TIMEOUTS.get(mod, 45)
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "backend.run_module", mod],
                input=json.dumps(pload).encode("utf-8"),
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT {mod}")
            fail_count += 1
            continue

        if proc.returncode != 0:
            print(f"  EXIT {proc.returncode} {mod}: {proc.stderr.decode('utf-8', errors='replace')[:300]}")
            fail_count += 1
            continue

        raw = _parse_stdout(proc.stdout.decode("utf-8", errors="replace"))
        if raw is None:
            preview = proc.stdout.decode("utf-8", errors="replace")[:200]
            print(f"  JSON PARSE FAILED {mod}: stdout preview={preview!r}")
            fail_count += 1
            continue

        envelope = normalize_result(mod, raw)
        if not envelope.get("ok"):
            err = (envelope.get("errors") or [{}])[0]
            msg = err.get("message") if isinstance(err, dict) else envelope
            print(f"  ENVELOPE FAIL {mod}: {msg}")
            fail_count += 1
            continue

        arts = envelope.get("artifacts") or {}
        total = sum(len(v) for v in arts.values() if isinstance(v, list))
        print(f"  OK {mod} (artifacts={total})")
        ok_count += 1

    print(f"\nSummary: {ok_count} ok, {fail_count} failed (of {len(MODULES)})")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
