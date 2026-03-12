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
try:
    from .dns_intel import dns_recon
except ImportError:
    dns_recon = None
try:
    from .whois_lookup import whois_lookup
except ImportError:
    whois_lookup = None
try:
    from .ssl_analyzer import ssl_analyze
except ImportError:
    ssl_analyze = None
try:
    from .http_security import http_security_audit
except ImportError:
    http_security_audit = None
try:
    from .tech_stack import detect_tech_stack
except ImportError:
    detect_tech_stack = None
try:
    from .metadata_extractor import extract_metadata
except ImportError:
    extract_metadata = None

__all__ = [
    "shodan_search", "censys_search", "scrape_urls", "scan_ports",
    "cyberninja_passive", "dns_recon", "whois_lookup", "ssl_analyze",
    "http_security_audit", "detect_tech_stack", "extract_metadata",
]
