"""
OSINT modules - extracted and rewritten for programmatic use.
"""
try:
    from .shodan_recon import shodan_search
except ImportError:
    shodan_search = None
try:
    from .censys_recon import censys_search
except ImportError:
    censys_search = None
try:
    from .scraper import scrape_urls
except ImportError:
    scrape_urls = None
try:
    from .port_scanner import scan_ports
except ImportError:
    scan_ports = None
try:
    from .cyberninja_passive import cyberninja_passive
except ImportError:
    cyberninja_passive = None

__all__ = ["shodan_search", "censys_search", "scrape_urls", "scan_ports", "cyberninja_passive"]
