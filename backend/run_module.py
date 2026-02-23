"""
CLI entry point for subprocess execution of OSINT modules.
Invoked as: python -m run_module <module_name>
Reads JSON payload from stdin, calls the module function, writes JSON result to stdout.
Any progress or errors go to stderr.
"""
from __future__ import annotations

import json
import sys


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

    if module_name == "shodan_recon":
        from modules.shodan_recon import shodan_search
        result = shodan_search(
            payload.get("target", ""),
            payload.get("api_key"),
        )
    elif module_name == "censys_recon":
        from modules.censys_recon import censys_search
        result = censys_search(
            payload.get("target", ""),
            payload.get("api_id"),
            payload.get("api_secret"),
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
    else:
        result = {"error": f"Unknown module: {module_name}"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
