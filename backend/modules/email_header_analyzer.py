from __future__ import annotations

import re
from email import policy
from email.parser import Parser
from typing import Any

IP_RE = re.compile(r"\b(?:(?:\d{1,3}\.){3}\d{1,3})\b")


def email_header_analyzer(raw_headers: str) -> dict[str, Any]:
    if not raw_headers or not raw_headers.strip():
        return {"success": False, "error": "raw_headers is required"}

    try:
        msg = Parser(policy=policy.default).parsestr(raw_headers)
    except Exception as exc:
        return {"success": False, "error": f"Header parse failed: {exc}"}

    received = msg.get_all("Received", [])
    auth_results = msg.get("Authentication-Results", "")
    spf = msg.get("Received-SPF", "")
    dkim_sig = msg.get("DKIM-Signature", "")
    dmarc = "pass" if "dmarc=pass" in auth_results.lower() else ("fail" if "dmarc=fail" in auth_results.lower() else "unknown")

    hops = []
    ips: set[str] = set()
    for hop in received:
        hop_ips = IP_RE.findall(hop)
        for ip in hop_ips:
            ips.add(ip)
        hops.append({"raw": hop, "ips": hop_ips})

    return {
        "success": True,
        "from": msg.get("From"),
        "to": msg.get("To"),
        "subject": msg.get("Subject"),
        "date": msg.get("Date"),
        "message_id": msg.get("Message-ID"),
        "hops": hops,
        "ips": sorted(ips),
        "spf": spf or ("pass" if "spf=pass" in auth_results.lower() else ("fail" if "spf=fail" in auth_results.lower() else "unknown")),
        "dkim": "present" if dkim_sig else "missing",
        "dmarc": dmarc,
        "auth_results": auth_results,
    }
