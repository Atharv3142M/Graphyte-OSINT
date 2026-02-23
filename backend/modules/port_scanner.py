"""
TCP port scanner module.
Inspired by port analysis concepts in Kcisti/bat-security-toolkit; implemented as a clean,
ethical connect-based port scanner for OSINT use. Uses concurrent scanning.
Accepts arguments programmatically for FastAPI/Celery integration.
"""
from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

DEFAULT_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443
]
DEFAULT_TIMEOUT = 2.0


def _scan_port(host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> dict[str, Any] | None:
    """Check if a single port is open. Returns port info if open, else None."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return {"port": port, "state": "open", "host": host}
    except (socket.error, socket.timeout, OSError):
        pass
    return None


def scan_ports(
    host: str,
    ports: list[int] | None = None,
    max_workers: int = 20,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    Scan target host for open TCP ports using concurrent connect-based probing.

    Args:
        host: Target hostname or IP.
        ports: List of ports to scan. Uses DEFAULT_PORTS if None.
        max_workers: Concurrent worker count.
        timeout: Socket timeout per port in seconds.

    Returns:
        Dict with host, open_ports list, and scan summary.
    """
    port_list = ports or DEFAULT_PORTS
    result: dict[str, Any] = {
        "host": host,
        "open_ports": [],
        "scanned": len(port_list),
        "success": True,
    }

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_scan_port, host, p, timeout): p
            for p in port_list
        }
        for future in as_completed(futures):
            try:
                r = future.result()
                if r:
                    result["open_ports"].append(r)
            except Exception:
                pass

    result["open_ports"].sort(key=lambda x: x["port"])
    return result
