from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any


def sherlock_hunt(username: str, timeout: int = 10, max_connections: int = 5) -> dict[str, Any]:
    try:
        from sherlock_project.sherlock import sherlock
        from sherlock_project.notify import QueryNotifyPrint
        from sherlock_project.sites import SitesInformation
    except Exception as exc:
        return {
            "success": False,
            "error": f"sherlock-project dependency unavailable: {exc}",
            "username": username,
        }

    if not username:
        return {"success": False, "error": "username is required"}

    sites_info = SitesInformation().sites
    site_data_all = {name: site.information for name, site in sites_info.items()}
    query_notify = QueryNotifyPrint(verbose=False, print_all=False)

    def _run() -> dict[str, Any]:
        return sherlock(
            username=username,
            site_data=site_data_all,
            query_notify=query_notify,
            tor=False,
            unique_tor=False,
            dump_response=False,
            timeout=timeout,
        )

    try:
        with ThreadPoolExecutor(max_workers=max_connections) as pool:
            future = pool.submit(_run)
            raw = future.result(timeout=120)
    except Exception as exc:
        return {"success": False, "error": f"Sherlock execution failed: {exc}", "username": username}

    found: list[dict[str, str]] = []
    for site, result in (raw or {}).items():
        status = str(result.get("status", "")).lower()
        if status == "claimed" or result.get("exists"):
            found.append({"platform": site, "url": result.get("url_user", "")})

    return {
        "success": True,
        "username": username,
        "count": len(found),
        "found": found,
        "source": "sherlock-project",
    }
