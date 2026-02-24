"""
CyberNinja passive sandbox wrapper.

This wrapper restricts CyberNinja to passive attack surface discovery:
- No Tor routing
- No custom proxies
- No browser launching
- No interactive prompts

It reuses CyberNinja's core username enumeration logic when the package
is available, but ensures only read-only HTTP(S) requests are performed.
"""
from __future__ import annotations

from typing import Any, Dict, List


def cyberninja_passive(
    usernames: List[str],
    timeout: float | None = None,
    site_list: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Run CyberNinja in a passive, sandboxed mode for one or more usernames.

    Args:
        usernames: List of usernames to investigate.
        timeout: Optional request timeout in seconds.
        site_list: Optional subset of sites to limit enumeration.

    Returns:
        Dictionary keyed by username with the raw results CyberNinja reports.
    """
    if not usernames:
        return {"error": "At least one username is required", "success": False}

    try:
        # Import from the vendored CyberNinja code if available.
        import importlib.util
        import os
        import sys

        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        cyber_path = os.path.join(
            base_dir, "CyberNinja-main", "CyberNinja", "Cyber-Ninja"
        )
        if cyber_path not in sys.path:
            sys.path.insert(0, cyber_path)

        from sites import SitesInformation  # type: ignore
        from notify import QueryNotifyPrint  # type: ignore
        from cyberninja import cyberninja as _cyberninja  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        return {
            "error": f"CyberNinja passive wrapper unavailable: {exc}",
            "success": False,
        }

    results: Dict[str, Any] = {}

    # Load site data once.
    site_data_all = SitesInformation().sites

    if site_list:
        site_data = {
            name: info for name, info in site_data_all.items() if name in site_list
        }
    else:
        site_data = site_data_all

    for username in usernames:
        notifier = QueryNotifyPrint(verbose=False, color=False, print_all=False)

        # Passive mode: tor=False, unique_tor=False, proxy=None
        res = _cyberninja(
            username=username,
            site_data=site_data,
            query_notify=notifier,
            tor=False,
            unique_tor=False,
            proxy=None,
            timeout=timeout,
        )
        results[username] = res

    return {"success": True, "data": results}

