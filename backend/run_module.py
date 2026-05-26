"""
CLI entry point for subprocess execution of OSINT modules.
Invoked as: python -m backend.run_module <module_name>
Reads JSON payload from stdin, calls the module function, writes a SINGLE JSON
result line to stdout.  All progress/log/print output from the module (and its
transitive imports) is force-redirected to stderr to guarantee a clean stdout
JSON contract.

Contract:
  - stdout: exactly one line, valid JSON
  - stderr: free-form (logs, tracebacks, third-party prints, warnings)
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from typing import Any, Dict, Iterator


@contextmanager
def _redirect_stdout_to_stderr() -> Iterator[None]:
    """Force every write to sys.stdout (incl. third-party prints) onto stderr.

    This protects the JSON-on-stdout contract: any module that calls print(),
    or any imported library that emits a deprecation/progress message, would
    otherwise corrupt the output stream. We restore stdout *only* for the
    final json.dumps line written by main().
    """
    saved = sys.stdout
    try:
        sys.stdout = sys.stderr
        yield
    finally:
        sys.stdout = saved


def _load_service_config() -> Dict[str, Any]:
    """
    Optionally load a JSON config file pointed to by OSINT_CONFIG_FILE.
    Used for injecting sensitive credentials without hardcoding them.
    """
    path = os.getenv("OSINT_CONFIG_FILE")
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Module name required", "success": False}))
        sys.exit(1)
    module_name = sys.argv[1]
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON stdin: {e}", "success": False}))
        sys.exit(1)

    service_config = _load_service_config()
    result: Dict[str, Any] = {}

    # Everything below runs with stdout silently redirected to stderr.
    # We only print the final JSON to the real stdout in the cleanup block.
    try:
        with _redirect_stdout_to_stderr():
            if module_name == "shodan_recon":
                from backend.modules.shodan_recon import shodan_search

                api_key = service_config.get("api_key") or payload.get("api_key")
                result = shodan_search(
                    payload.get("target", ""),
                    api_key,
                )
            elif module_name == "censys_recon":
                from backend.modules.censys_recon import censys_search

                api_id = service_config.get("api_id") or payload.get("api_id")
                api_secret = service_config.get("api_secret") or payload.get("api_secret")
                result = censys_search(
                    payload.get("target", ""),
                    api_id,
                    api_secret,
                )
            elif module_name == "scraper":
                from backend.modules.scraper import scrape_urls

                result = scrape_urls(
                    payload.get("urls", []),
                    payload.get("max_workers", 5),
                )
            elif module_name == "port_scanner":
                from backend.modules.port_scanner import scan_ports

                result = scan_ports(
                    payload.get("host", ""),
                    payload.get("ports"),
                    payload.get("max_workers", 20),
                    payload.get("timeout", 2.0),
                )
            elif module_name in ("graysentinel_ingest", "graysentinel_pipeline"):
                from backend.modules.graysentinel_pipeline import run_pipeline

                result = run_pipeline(
                    payload.get("urls", []),
                    payload.get("strategies"),
                )
            elif module_name == "cyberninja_passive":
                try:
                    from backend.modules.cyberninja_passive import cyberninja_passive
                except ImportError:
                    result = {"error": "CyberNinja passive module not available", "success": False}
                else:
                    result = cyberninja_passive(
                        payload.get("usernames", []),
                        timeout=payload.get("timeout"),
                        site_list=payload.get("site_list"),
                    )
            elif module_name == "xrecon":
                from backend.modules.xrecon import xrecon_search

                result = xrecon_search(
                    payload.get("query", ""),
                    payload.get("query_type", "username"),
                )
            elif module_name == "dns_intel":
                from backend.modules.dns_intel import dns_recon

                result = dns_recon(
                    payload.get("domain", ""),
                    discover_subdomains=payload.get("brute_subdomains", False),
                    subdomain_wordlist=payload.get("wordlist"),
                )
            elif module_name == "whois_lookup":
                from backend.modules.whois_lookup import whois_lookup

                result = whois_lookup(payload.get("domain", ""))
            elif module_name == "ssl_analyzer":
                from backend.modules.ssl_analyzer import ssl_analyze

                result = ssl_analyze(
                    payload.get("host", ""),
                    port=payload.get("port", 443),
                    timeout=payload.get("timeout", 10),
                )
            elif module_name == "http_security":
                from backend.modules.http_security import http_security_audit

                result = http_security_audit(
                    payload.get("url", ""),
                    timeout=payload.get("timeout", 10),
                )
            elif module_name == "tech_stack":
                from backend.modules.tech_stack import detect_tech_stack

                result = detect_tech_stack(
                    payload.get("url", ""),
                    timeout=payload.get("timeout", 10),
                )
            elif module_name == "metadata_extractor":
                from backend.modules.metadata_extractor import extract_metadata

                result = extract_metadata(payload.get("file_path", ""))
            elif module_name == "social_hunter":
                from backend.modules.social_hunter import social_hunter

                result = social_hunter(
                    payload.get("username", ""),
                    max_concurrent=payload.get("max_concurrent", 20),
                )
            elif module_name == "cert_transparency":
                from backend.modules.cert_transparency import cert_transparency

                result = cert_transparency(
                    payload.get("domain", ""),
                    use_html_fallback=payload.get("use_html_fallback", True),
                )
            elif module_name == "deep_scraper":
                from backend.modules.deep_scraper import deep_scraper

                result = deep_scraper(
                    payload.get("url", ""),
                    max_depth=payload.get("max_depth", 2),
                    max_pages=payload.get("max_pages", 50),
                    max_concurrent=payload.get("max_concurrent", 10),
                )
            elif module_name == "ip_geolocation":
                from backend.modules.ip_geolocation import ip_geolocation

                result = ip_geolocation(payload.get("target", ""))
            elif module_name == "reverse_ip_lookup":
                from backend.modules.reverse_ip_lookup import reverse_ip_lookup

                result = reverse_ip_lookup(payload.get("target", ""))
            elif module_name == "bgp_asn_lookup":
                from backend.modules.bgp_asn_lookup import bgp_asn_lookup

                result = bgp_asn_lookup(payload.get("target", ""))
            elif module_name == "wayback_machine":
                from backend.modules.wayback_machine import wayback_machine_lookup

                result = wayback_machine_lookup(
                    payload.get("target", ""),
                    payload.get("limit", 50),
                )
            elif module_name == "email_header_analyzer":
                from backend.modules.email_header_analyzer import email_header_analyzer

                result = email_header_analyzer(payload.get("raw_headers", ""))
            elif module_name == "sherlock_hunt":
                from backend.modules.sherlock_hunt import sherlock_hunt

                result = sherlock_hunt(
                    payload.get("username", ""),
                    timeout=payload.get("timeout", 10),
                    max_connections=payload.get("max_connections", 5),
                )
            elif module_name == "robots_sitemap":
                from backend.modules.robots_sitemap import robots_sitemap_ingest

                result = robots_sitemap_ingest(
                    payload.get("domain", ""),
                    max_sitemap_urls=payload.get("max_sitemap_urls", 200),
                )
            elif module_name == "favicon_hash":
                from backend.modules.favicon_hash import favicon_hash_lookup

                result = favicon_hash_lookup(payload.get("domain", ""))
            elif module_name == "username_permutator":
                from backend.modules.username_permutator import username_permutate

                result = username_permutate(
                    payload.get("seed", ""),
                    max_results=payload.get("max_results", 50),
                )
            elif module_name == "github_osint":
                from backend.modules.github_osint import github_osint_lookup

                result = github_osint_lookup(
                    payload.get("target", ""),
                    lookup_type=payload.get("lookup_type", "auto"),
                    api_token=service_config.get("api_token") or payload.get("api_token"),
                    max_repos=payload.get("max_repos", 30),
                )
            elif module_name == "phone_intel":
                from backend.modules.phone_intel import phone_intel_lookup

                result = phone_intel_lookup(
                    payload.get("number", ""),
                    default_region=payload.get("default_region", "US"),
                )
            elif module_name == "email_reputation":
                from backend.modules.email_reputation import email_reputation_check

                result = email_reputation_check(payload.get("email", ""))
            else:
                result = {"error": f"Unknown module: {module_name}", "success": False}
    except Exception as e:
        import traceback

        result = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "success": False,
        }

    try:
        output = json.dumps(result, default=str)
    except Exception as e:
        output = json.dumps({"error": f"Result not JSON-serializable: {e}", "success": False})
    sys.__stdout__.write(output + "\n")
    sys.__stdout__.flush()


if __name__ == "__main__":
    main()
