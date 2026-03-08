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

    if module_name == "shodan_recon":
        from modules.shodan_recon import shodan_search

        api_key = service_config.get("api_key") or payload.get("api_key")
        result = shodan_search(
            payload.get("target", ""),
            api_key,
        )
    elif module_name == "censys_recon":
        from modules.censys_recon import censys_search

        api_id = service_config.get("api_id") or payload.get("api_id")
        api_secret = service_config.get("api_secret") or payload.get("api_secret")
        result = censys_search(
            payload.get("target", ""),
            api_id,
            api_secret,
        )
    elif module_name == "scraper":
        from modules.scraper import scrape_urls

        result = scrape_urls(
            payload.get("urls", []),
            payload.get("max_workers", 5),
        )
    elif module_name == "port_scanner":
        from modules.port_scanner import scan_ports

        result = scan_ports(
            payload.get("host", ""),
            payload.get("ports"),
            payload.get("max_workers", 20),
            payload.get("timeout", 2.0),
        )
    elif module_name == "graysentinel_ingest":
        from modules.graysentinel_pipeline import run_pipeline
        result = run_pipeline(
            payload.get("urls", []),
            payload.get("strategies"),
        )
    elif module_name == "cyberninja_passive":
        try:
            from modules.cyberninja_passive import cyberninja_passive
        except ImportError:
            result = {"error": "CyberNinja passive module not available"}
        else:
            result = cyberninja_passive(
                payload.get("usernames", []),
                timeout=payload.get("timeout"),
                site_list=payload.get("site_list"),
            )
    else:
        result = {"error": f"Unknown module: {module_name}"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
