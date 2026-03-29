"""
CLI entry point for subprocess execution of OSINT modules.
Invoked as: python -m run_module <module_name>
Reads JSON payload from stdin, calls the module function, writes JSON result to stdout.
Any progress or errors go to stderr.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict


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
        print(json.dumps({"error": "Module name required"}), file=sys.stderr)
        sys.exit(1)
    module_name = sys.argv[1]
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON stdin: {e}"}), file=sys.stderr)
        sys.exit(1)

    service_config = _load_service_config()
    result: Dict[str, Any] = {}

    try:
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
        elif module_name == "graysentinel_ingest":
            from backend.modules.graysentinel_pipeline import run_pipeline
            result = run_pipeline(
                payload.get("urls", []),
                payload.get("strategies"),
            )
        elif module_name == "cyberninja_passive":
            try:
                from backend.modules.cyberninja_passive import cyberninja_passive
            except ImportError:
                result = {"error": "CyberNinja passive module not available"}
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
        elif module_name == "graysentinel_pipeline":
            from backend.modules.graysentinel_pipeline import run_pipeline
            result = run_pipeline(
                payload.get("urls", []),
                payload.get("strategies"),
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
        else:
            result = {"error": f"Unknown module: {module_name}"}
    except Exception as e:
        # Catch any exception from module execution and return as valid JSON
        import traceback
        result = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "success": False,
        }

    # Always output valid JSON to stdout and flush immediately
    output = json.dumps(result)
    print(output)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
