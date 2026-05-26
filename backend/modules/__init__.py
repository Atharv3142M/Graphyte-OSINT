"""
OSINT modules - self-contained reconnaissance functions.
All modules are dependency-clean with graceful fallback when optional libs are missing.
"""
from .shodan_recon import shodan_search
from .censys_recon import censys_search
from .scraper import scrape_urls
from .port_scanner import scan_ports
from .cyberninja_passive import cyberninja_passive
from .dns_intel import dns_recon
from .whois_lookup import whois_lookup
from .ssl_analyzer import ssl_analyze
from .http_security import http_security_audit
from .tech_stack import detect_tech_stack
from .metadata_extractor import extract_metadata
from .graysentinel_pipeline import run_pipeline
from .xrecon import xrecon_search
from .social_hunter import social_hunter
from .cert_transparency import cert_transparency
from .deep_scraper import deep_scraper
from .robots_sitemap import robots_sitemap_ingest
from .favicon_hash import favicon_hash_lookup
from .username_permutator import username_permutate
from .github_osint import github_osint_lookup
from .phone_intel import phone_intel_lookup
from .email_reputation import email_reputation_check

__all__ = [
    "shodan_search",
    "censys_search",
    "scrape_urls",
    "scan_ports",
    "cyberninja_passive",
    "dns_recon",
    "whois_lookup",
    "ssl_analyze",
    "http_security_audit",
    "detect_tech_stack",
    "extract_metadata",
    "run_pipeline",
    "xrecon_search",
    "social_hunter",
    "cert_transparency",
    "deep_scraper",
    "robots_sitemap_ingest",
    "favicon_hash_lookup",
    "username_permutate",
    "github_osint_lookup",
    "phone_intel_lookup",
    "email_reputation_check",
]
