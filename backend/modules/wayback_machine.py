from __future__ import annotations

import re
from typing import Any

import requests

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-.]+")


def wayback_machine_lookup(target: str, limit: int = 50) -> dict[str, Any]:
    try:
        resp = requests.get(
            "https://web.archive.org/cdx/search/cdx",
            params={
                "url": target,
                "output": "json",
                "fl": "timestamp,original,statuscode,mimetype",
                "filter": "statuscode:200",
                "collapse": "digest",
                "limit": limit,
            },
            timeout=20,
        )
        resp.raise_for_status()
        rows = resp.json()
    except Exception as exc:
        return {"success": False, "error": f"Wayback lookup failed: {exc}", "target": target}

    if not isinstance(rows, list) or len(rows) <= 1:
        return {"success": True, "target": target, "snapshots": [], "count": 0, "emails": []}

    snapshots = []
    emails: set[str] = set()
    for row in rows[1:]:
        if len(row) < 2:
            continue
        ts = row[0]
        original = row[1]
        snapshot_url = f"https://web.archive.org/web/{ts}/{original}"
        snapshots.append(
            {
                "timestamp": ts,
                "original": original,
                "statuscode": row[2] if len(row) > 2 else None,
                "mimetype": row[3] if len(row) > 3 else None,
                "snapshot_url": snapshot_url,
            }
        )
        for match in EMAIL_RE.findall(original):
            emails.add(match.lower())

    return {
        "success": True,
        "target": target,
        "count": len(snapshots),
        "snapshots": snapshots,
        "emails": sorted(emails),
        "source": "archive.org-cdx",
    }
