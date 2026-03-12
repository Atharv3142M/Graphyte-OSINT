"""
Technology Fingerprinter - Detects web technologies from HTTP responses.
Lightweight Wappalyzer-style detection using headers, HTML patterns, scripts, cookies.
No API keys required — uses requests + beautifulsoup4.
"""
from __future__ import annotations

import re
from typing import Any

try:
    import requests as _requests
except ImportError:
    _requests = None  # type: ignore[assignment]

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment]


# Fingerprint rules: each rule maps a category + technology to detection logic
_FINGERPRINTS: list[dict[str, Any]] = [
    # === Server / Infrastructure ===
    {"name": "Nginx", "category": "Web Server", "header": "server", "pattern": r"nginx", "confidence": 95},
    {"name": "Apache", "category": "Web Server", "header": "server", "pattern": r"apache", "confidence": 95},
    {"name": "IIS", "category": "Web Server", "header": "server", "pattern": r"microsoft-iis", "confidence": 95},
    {"name": "LiteSpeed", "category": "Web Server", "header": "server", "pattern": r"litespeed", "confidence": 90},
    {"name": "Caddy", "category": "Web Server", "header": "server", "pattern": r"caddy", "confidence": 90},
    {"name": "Cloudflare", "category": "CDN", "header": "server", "pattern": r"cloudflare", "confidence": 95},
    {"name": "Cloudflare", "category": "CDN", "header": "cf-ray", "pattern": r".", "confidence": 95},
    {"name": "AWS CloudFront", "category": "CDN", "header": "x-amz-cf-id", "pattern": r".", "confidence": 90},
    {"name": "AWS CloudFront", "category": "CDN", "header": "via", "pattern": r"cloudfront", "confidence": 85},
    {"name": "Fastly", "category": "CDN", "header": "x-served-by", "pattern": r"cache-", "confidence": 85},
    {"name": "Vercel", "category": "Hosting", "header": "x-vercel-id", "pattern": r".", "confidence": 95},
    {"name": "Netlify", "category": "Hosting", "header": "x-nf-request-id", "pattern": r".", "confidence": 95},
    {"name": "Heroku", "category": "Hosting", "header": "via", "pattern": r"vegur", "confidence": 90},

    # === Backend Languages / Frameworks ===
    {"name": "PHP", "category": "Language", "header": "x-powered-by", "pattern": r"php", "confidence": 95},
    {"name": "ASP.NET", "category": "Framework", "header": "x-powered-by", "pattern": r"asp\.net", "confidence": 95},
    {"name": "ASP.NET", "category": "Framework", "header": "x-aspnet-version", "pattern": r".", "confidence": 95},
    {"name": "Express.js", "category": "Framework", "header": "x-powered-by", "pattern": r"express", "confidence": 90},
    {"name": "Django", "category": "Framework", "cookie": "csrftoken", "confidence": 80},
    {"name": "Rails", "category": "Framework", "header": "x-powered-by", "pattern": r"phusion passenger", "confidence": 85},
    {"name": "Rails", "category": "Framework", "cookie": "_session_id", "confidence": 60},

    # === CMS ===
    {"name": "WordPress", "category": "CMS", "html": r'wp-content|wp-includes|wp-json', "confidence": 95},
    {"name": "WordPress", "category": "CMS", "meta_generator": r"wordpress", "confidence": 95},
    {"name": "WordPress", "category": "CMS", "cookie": "wp-settings-", "confidence": 90},
    {"name": "Drupal", "category": "CMS", "header": "x-drupal-cache", "pattern": r".", "confidence": 95},
    {"name": "Drupal", "category": "CMS", "html": r'sites/default/files|drupal\.js', "confidence": 90},
    {"name": "Joomla", "category": "CMS", "meta_generator": r"joomla", "confidence": 95},
    {"name": "Joomla", "category": "CMS", "html": r'/media/jui/|/templates/system/', "confidence": 85},
    {"name": "Ghost", "category": "CMS", "meta_generator": r"ghost", "confidence": 95},
    {"name": "Shopify", "category": "E-commerce", "header": "x-shopid", "pattern": r".", "confidence": 95},
    {"name": "Shopify", "category": "E-commerce", "html": r'cdn\.shopify\.com', "confidence": 90},
    {"name": "Squarespace", "category": "CMS", "html": r'squarespace\.com|static\.squarespace', "confidence": 90},
    {"name": "Wix", "category": "CMS", "html": r'static\.wixstatic\.com|wix\.com', "confidence": 90},
    {"name": "Hugo", "category": "Static Site Generator", "meta_generator": r"hugo", "confidence": 95},
    {"name": "Gatsby", "category": "Static Site Generator", "meta_generator": r"gatsby", "confidence": 95},
    {"name": "Gatsby", "category": "Static Site Generator", "html": r'gatsby-', "confidence": 80},

    # === Frontend Frameworks ===
    {"name": "React", "category": "JS Framework", "html": r'__react|data-reactroot|react\.production|reactDOM', "confidence": 85},
    {"name": "Next.js", "category": "JS Framework", "html": r'__NEXT_DATA__|_next/static', "confidence": 95},
    {"name": "Next.js", "category": "JS Framework", "header": "x-nextjs-cache", "pattern": r".", "confidence": 95},
    {"name": "Vue.js", "category": "JS Framework", "html": r'data-v-[a-f0-9]|vue\.runtime|vue\.global', "confidence": 80},
    {"name": "Nuxt.js", "category": "JS Framework", "html": r'__NUXT__|_nuxt/', "confidence": 95},
    {"name": "Angular", "category": "JS Framework", "html": r'ng-version|ng-app|angular\.', "confidence": 85},
    {"name": "Svelte", "category": "JS Framework", "html": r'svelte-[a-z0-9]|__svelte', "confidence": 80},

    # === JavaScript Libraries ===
    {"name": "jQuery", "category": "JS Library", "html": r'jquery[\.-][\d]|jquery\.min\.js', "confidence": 90},
    {"name": "Bootstrap", "category": "CSS Framework", "html": r'bootstrap[\.-][\d]|bootstrap\.min\.(js|css)', "confidence": 90},
    {"name": "Tailwind CSS", "category": "CSS Framework", "html": r'tailwindcss|tailwind\.', "confidence": 80},

    # === Analytics & Marketing ===
    {"name": "Google Analytics", "category": "Analytics", "html": r'google-analytics\.com|gtag/js\?id=|GoogleAnalyticsObject', "confidence": 95},
    {"name": "Google Tag Manager", "category": "Analytics", "html": r'googletagmanager\.com/gtm\.js', "confidence": 95},
    {"name": "Facebook Pixel", "category": "Analytics", "html": r'connect\.facebook\.net/.*fbevents|fbq\(', "confidence": 90},
    {"name": "Hotjar", "category": "Analytics", "html": r'static\.hotjar\.com|hj\(', "confidence": 90},
    {"name": "Mixpanel", "category": "Analytics", "html": r'cdn\.mxpnl\.com|mixpanel', "confidence": 85},
    {"name": "Segment", "category": "Analytics", "html": r'cdn\.segment\.com|analytics\.js', "confidence": 85},
    {"name": "Plausible", "category": "Analytics", "html": r'plausible\.io/js/', "confidence": 90},
]


def detect_tech_stack(
    url: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """
    Detect web technologies used by a URL.

    Args:
        url: Target URL (e.g. 'https://example.com'). Scheme added if missing.
        timeout: Request timeout in seconds.

    Returns:
        Dict with detected technologies (name, category, confidence, evidence),
        server info, and powered_by header.
    """
    if _requests is None:
        return {
            "success": False,
            "error": "requests library is not installed. Run: pip install requests",
            "url": url,
        }

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        resp = _requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OSINT-TechDetect/1.0)"},
        )
    except Exception as e:
        return {"success": False, "error": f"Request failed: {e}", "url": url}

    headers = {k.lower(): v for k, v in resp.headers.items()}
    html_text = resp.text
    cookies = {c.name: c.value for c in resp.cookies}

    # Parse HTML with BeautifulSoup if available
    meta_generator = ""
    if BeautifulSoup:
        soup = BeautifulSoup(html_text, "html.parser")
        gen_tag = soup.find("meta", attrs={"name": re.compile(r"generator", re.I)})
        if gen_tag:
            meta_generator = str(gen_tag.get("content", "")).lower()
    else:
        # Fallback regex for meta generator
        match = re.search(r'<meta\s+name=["\']generator["\'][^>]*content=["\']([^"\']*)', html_text, re.I)
        if match:
            meta_generator = match.group(1).lower()

    # Run fingerprint detection
    detected: dict[str, dict[str, Any]] = {}  # keyed by name to deduplicate

    for rule in _FINGERPRINTS:
        name = rule["name"]
        matched = False
        evidence = ""

        if "header" in rule:
            header_val = headers.get(rule["header"].lower(), "")
            if header_val and re.search(rule["pattern"], header_val, re.I):
                matched = True
                evidence = f"Header '{rule['header']}': {header_val}"

        elif "html" in rule:
            if re.search(rule["html"], html_text, re.I):
                matched = True
                evidence = f"HTML pattern: {rule['html'][:60]}"

        elif "meta_generator" in rule:
            if re.search(rule["meta_generator"], meta_generator, re.I):
                matched = True
                evidence = f"Meta generator: {meta_generator}"

        elif "cookie" in rule:
            cookie_key = rule["cookie"]
            for k in cookies:
                if cookie_key.lower() in k.lower():
                    matched = True
                    evidence = f"Cookie: {k}"
                    break

        if matched:
            if name not in detected or rule["confidence"] > detected[name]["confidence"]:
                detected[name] = {
                    "name": name,
                    "category": rule["category"],
                    "confidence": rule["confidence"],
                    "evidence": evidence,
                }

    technologies = sorted(detected.values(), key=lambda x: (-x["confidence"], x["name"]))

    return {
        "success": True,
        "url": url,
        "final_url": resp.url,
        "status_code": resp.status_code,
        "server": headers.get("server", ""),
        "powered_by": headers.get("x-powered-by", ""),
        "technologies": technologies,
        "tech_count": len(technologies),
        "categories": sorted(set(t["category"] for t in technologies)),
    }
