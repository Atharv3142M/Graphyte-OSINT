"""
Multi-threaded web scraping module.
Extracted from Hamed233/Digital-Footprint-OSINT-Tool - core methodology: multi-threaded scraping.
Accepts arguments programmatically for FastAPI/Celery integration.
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

try:
    import requests
    from fake_useragent import UserAgent
    import phonenumbers
except ImportError:
    requests = None
    UserAgent = None
    phonenumbers = None

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\+?[1-9][0-9]{7,14}")


def _scrape_single_url(url: str, user_agent: str | None = None) -> tuple[set[str], set[str]]:
    """Scrape a single URL for emails and phone numbers."""
    emails: set[str] = set()
    numbers: set[str] = set()

    if not requests:
        return emails, numbers

    headers = {"User-Agent": user_agent or "Mozilla/5.0 (compatible; OSINT-Bot/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return emails, numbers
        text = resp.text
        emails.update(EMAIL_PATTERN.findall(text))
        for match in PHONE_PATTERN.findall(text):
            try:
                if phonenumbers:
                    parsed = phonenumbers.parse(match)
                    if phonenumbers.is_valid_number(parsed):
                        formatted = phonenumbers.format_number(
                            parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                        )
                        numbers.add(formatted)
                else:
                    numbers.add(match)
            except Exception:
                continue
    except Exception:
        pass
    return emails, numbers


def scrape_urls(
    urls: list[str],
    max_workers: int = 5,
) -> dict[str, Any]:
    """
    Multi-threaded scraping of URLs for emails and phone numbers.

    Args:
        urls: List of URLs to scrape.
        max_workers: Thread pool size (default 5).

    Returns:
        Dict with found_emails, found_numbers, and per-url results.
    """
    result: dict[str, Any] = {
        "found_emails": [],
        "found_numbers": [],
        "per_url": [],
        "success": True,
    }

    ua = UserAgent().random if UserAgent else None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scrape_single_url, u, ua): u for u in urls}
        all_emails: set[str] = set()
        all_numbers: set[str] = set()
        for future in futures:
            url = futures[future]
            try:
                emails, numbers = future.result()
                all_emails.update(emails)
                all_numbers.update(numbers)
                result["per_url"].append({"url": url, "emails": list(emails), "numbers": list(numbers)})
            except Exception as e:
                result["per_url"].append({"url": url, "error": str(e), "emails": [], "numbers": []})

    result["found_emails"] = list(all_emails)
    result["found_numbers"] = list(all_numbers)
    return result
