"""
Scoped tools for the Searcher Agent only.
Zero-trust: Searcher may only call these (OSINT-Search + xRecon style lookups).
"""
from __future__ import annotations

from typing import Any, Callable

# Tool permission tag for audit
SEARCHER_TOOL_NAMES = {"shodan_search", "censys_search", "scrape_urls", "xrecon_search"}


def shodan_search(target: str, api_key: str | None = None) -> dict[str, Any]:
    """Shodan host/domain lookup. Searcher-only."""
    from modules.shodan_recon import shodan_search as _run
    return _run(target, api_key)


def censys_search(target: str, api_id: str | None = None, api_secret: str | None = None) -> dict[str, Any]:
    """Censys host/domain lookup. Searcher-only."""
    from modules.censys_recon import censys_search as _run
    return _run(target, api_id, api_secret)


def scrape_urls(urls: list[str], max_workers: int = 5) -> dict[str, Any]:
    """Scrape URLs for content/contacts. Searcher-only."""
    from modules.scraper import scrape_urls as _run
    return _run(urls, max_workers)


def xrecon_search(query: str, query_type: str = "username") -> dict[str, Any]:
    """xRecon-style lookup (username/email). Searcher-only. Delegates to OSINT modules or stub."""
    try:
        from modules.xrecon import xrecon_search as _run
        return _run(query, query_type)
    except ImportError:
        return {"success": True, "data": {"message": "xRecon module not loaded", "query": query, "query_type": query_type}}


def get_searcher_tools() -> dict[str, Callable[..., Any]]:
    """Return only the tools the Searcher agent is allowed to use (zero-trust)."""
    return {
        "shodan_search": shodan_search,
        "censys_search": censys_search,
        "scrape_urls": scrape_urls,
        "xrecon_search": xrecon_search,
    }
