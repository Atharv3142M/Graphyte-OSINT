"""
deep_scraper.py - Recursive entity extraction from web pages.

Enhanced scraper that recursively extracts:
- All email addresses (internal, external, mailto links)
- Internal links (same domain)
- External links (different domains)
- Document metadata from linked PDFs/DOCX files
- Phone numbers, social media profiles, and other PII

This goes far beyond basic scraping by:
1. Following links recursively (configurable depth)
2. Extracting metadata from documents without downloading them fully
3. Identifying and categorizing all discovered entities

Output format:
{
    "success": true,
    "target_url": "<url>",
    "crawl_depth": 2,
    "pages_crawled": 15,
    "emails": [...],
    "phone_numbers": [...],
    "internal_links": [...],
    "external_links": [...],
    "documents": [
        {"url": "...", "type": "pdf", "metadata": {...}},
        ...
    ],
    "social_profiles": [...],
    "all_entities": {...}
}
"""
from __future__ import annotations

import asyncio
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse


@dataclass
class DocumentMetadata:
    """Metadata extracted from a document (PDF/DOCX)."""
    url: str
    doc_type: str  # "pdf", "docx", "xlsx", "pptx"
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    pages: Optional[int] = None
    error: Optional[str] = None


@dataclass
class PageResult:
    """Result from scraping a single page."""
    url: str
    status_code: Optional[int] = None
    emails: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    internal_links: list[str] = field(default_factory=list)
    external_links: list[str] = field(default_factory=list)
    documents: list[DocumentMetadata] = field(default_factory=list)
    social_profiles: list[dict] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DeepScraperResult:
    """Complete result from deep scraping."""
    target_url: str
    crawl_depth: int = 0
    max_depth: int = 2
    pages_crawled: int = 0
    pages_failed: int = 0
    total_emails: int = 0
    total_phones: int = 0
    total_internal_links: int = 0
    total_external_links: int = 0
    total_documents: int = 0
    all_emails: list[str] = field(default_factory=list)
    all_phones: list[str] = field(default_factory=list)
    all_internal_links: list[str] = field(default_factory=list)
    all_external_links: list[str] = field(default_factory=list)
    all_documents: list[DocumentMetadata] = field(default_factory=list)
    all_social_profiles: list[dict] = field(default_factory=list)
    page_results: list[PageResult] = field(default_factory=list)
    crawl_time_ms: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "success": True,
            "target_url": self.target_url,
            "crawl_depth": self.crawl_depth,
            "max_depth": self.max_depth,
            "pages_crawled": self.pages_crawled,
            "pages_failed": self.pages_failed,
            "total_emails": self.total_emails,
            "total_phones": self.total_phones,
            "total_internal_links": self.total_internal_links,
            "total_external_links": self.total_external_links,
            "total_documents": self.total_documents,
            "emails": self.all_emails,
            "phone_numbers": self.all_phones,
            "internal_links": self.all_internal_links,
            "external_links": self.all_external_links,
            "documents": [
                {
                    "url": d.url,
                    "type": d.doc_type,
                    "title": d.title,
                    "author": d.author,
                    "created_date": d.created_date,
                    "modified_date": d.modified_date,
                    "subject": d.subject,
                    "error": d.error,
                }
                for d in self.all_documents
            ],
            "social_profiles": self.all_social_profiles,
        }


# Regex patterns for entity extraction
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

PHONE_PATTERN = re.compile(
    r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}',
    re.IGNORECASE
)

# Document extensions to look for
DOCUMENT_EXTENSIONS = {
    "pdf": "pdf",
    ".pdf": "pdf",
    "doc": "docx",
    ".doc": "docx",
    "docx": "docx",
    ".docx": "docx",
    "xlsx": "xlsx",
    ".xlsx": "xlsx",
    "xls": "xlsx",
    ".xls": "xlsx",
    "pptx": "pptx",
    ".pptx": "pptx",
    "ppt": "pptx",
    ".ppt": "pptx",
}

# Social media URL patterns
SOCIAL_PATTERNS = {
    "facebook": re.compile(r'facebook\.com/([^/\s"?#]+)', re.IGNORECASE),
    "twitter": re.compile(r'twitter\.com/([^/\s"?#]+)', re.IGNORECASE),
    "instagram": re.compile(r'instagram\.com/([^/\s"?#]+)', re.IGNORECASE),
    "linkedin": re.compile(r'linkedin\.com/(?:in|company)/([^/\s"?#]+)', re.IGNORECASE),
    "github": re.compile(r'github\.com/([^/\s"?#]+)', re.IGNORECASE),
    "youtube": re.compile(r'youtube\.com/(?:@|channel/|user/)([^/\s"?#]+)', re.IGNORECASE),
    "tiktok": re.compile(r'tiktok\.com/@([^/\s"?#]+)', re.IGNORECASE),
}


def is_document_url(url: str) -> Optional[str]:
    """Check if URL points to a document and return its type."""
    url_lower = url.lower()
    for ext, doc_type in DOCUMENT_EXTENSIONS.items():
        if url_lower.endswith(ext):
            return doc_type
    return None


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc.lower()


def normalize_url(base_url: str, link: str) -> Optional[str]:
    """
    Normalize a link relative to base URL.

    Returns None if the link is invalid (javascript:, mailto:, #, etc.)
    """
    if not link:
        return None

    # Skip non-HTTP links
    if link.startswith(("javascript:", "mailto:", "tel:", "#", "data:")):
        return None

    # Handle relative URLs
    if link.startswith("//"):
        return "https:" + link
    elif link.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{link}"
    elif link.startswith(("http://", "https://")):
        return link
    else:
        # Relative path
        return urljoin(base_url, link)


async def extract_metadata_from_document(url: str) -> DocumentMetadata:
    """
    Extract metadata from a document URL.

    For PDFs, we can often get metadata from headers or partial content.
    For other documents, we extract what we can without full download.
    """
    import aiohttp

    result = DocumentMetadata(url=url, doc_type="unknown")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }

    try:
        async with aiohttp.ClientSession() as session:
            # First, try HEAD request to get content type
            async with session.head(url, headers=headers, timeout=10, allow_redirects=True) as response:
                content_type = response.headers.get("Content-Type", "").lower()

                if "pdf" in content_type:
                    result.doc_type = "pdf"
                elif "word" in content_type or "docx" in content_type:
                    result.doc_type = "docx"
                elif "excel" in content_type or "spreadsheet" in content_type:
                    result.doc_type = "xlsx"
                elif "powerpoint" in content_type or "presentation" in content_type:
                    result.doc_type = "pptx"
                else:
                    # Check URL extension
                    detected_type = is_document_url(url)
                    if detected_type:
                        result.doc_type = detected_type

            # For PDFs, try to extract metadata from first few KB
            if result.doc_type == "pdf":
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        # Read first 8KB (metadata is usually at the start)
                        chunk = await response.content.read(8192)
                        text = chunk.decode("utf-8", errors="ignore")

                        # Extract PDF metadata
                        title_match = re.search(r"/Title\s*\(([^)]+)\)", text)
                        if title_match:
                            result.title = title_match.group(1)

                        author_match = re.search(r"/Author\s*\(([^)]+)\)", text)
                        if author_match:
                            result.author = author_match.group(1)

                        subject_match = re.search(r"/Subject\s*\(([^)]+)\)", text)
                        if subject_match:
                            result.subject = subject_match.group(1)

                        keywords_match = re.search(r"/Keywords\s*\(([^)]+)\)", text)
                        if keywords_match:
                            result.keywords = keywords_match.group(1)

                        # Extract creation/modification dates
                        created_match = re.search(r"/CreationDate\s*\(([^)]+)\)", text)
                        if created_match:
                            result.created_date = created_match.group(1)

                        modified_match = re.search(r"/ModDate\s*\(([^)]+)\)", text)
                        if modified_match:
                            result.modified_date = modified_match.group(1)

    except asyncio.TimeoutError:
        result.error = "Request timeout"
    except aiohttp.ClientError as e:
        result.error = str(e)
    except Exception as e:
        result.error = f"Unexpected error: {e}"

    return result


async def scrape_page(
    session,
    url: str,
    base_domain: str,
    semaphore: asyncio.Semaphore,
) -> PageResult:
    """
    Scrape a single page for entities.

    Args:
        session: aiohttp ClientSession
        url: URL to scrape
        base_domain: Base domain for determining internal/external links
        semaphore: Concurrency limiter

    Returns:
        PageResult with extracted entities
    """
    import aiohttp
    from bs4 import BeautifulSoup

    result = PageResult(url=url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        async with semaphore:
            async with session.get(url, headers=headers, timeout=30, allow_redirects=True) as response:
                result.status_code = response.status

                if response.status != 200:
                    result.error = f"HTTP {response.status}"
                    return result

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Extract text content for regex matching
                text = soup.get_text()

                # Extract emails
                emails = set(EMAIL_PATTERN.findall(text))
                # Also check href="mailto:" links
                for link in soup.find_all("a", href=True):
                    if link["href"].startswith("mailto:"):
                        email = link["href"][7:].split("?")[0]
                        emails.add(email)
                result.emails = list(emails)

                # Extract phone numbers
                phones = set(PHONE_PATTERN.findall(text))
                result.phone_numbers = [p.strip() for p in phones if len(p) >= 7]

                # Extract links
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    normalized = normalize_url(url, href)

                    if normalized:
                        link_domain = get_domain(normalized)

                        # Check if it's a document
                        doc_type = is_document_url(normalized)
                        if doc_type:
                            result.documents.append(
                                DocumentMetadata(url=normalized, doc_type=doc_type)
                            )

                        # Categorize as internal or external
                        if link_domain == base_domain or link_domain.endswith(f".{base_domain}"):
                            if normalized not in result.internal_links:
                                result.internal_links.append(normalized)
                        else:
                            if normalized not in result.external_links:
                                result.external_links.append(normalized)

                # Extract social media profiles
                for platform, pattern in SOCIAL_PATTERNS.items():
                    for match in pattern.finditer(text):
                        profile = {"platform": platform, "username": match.group(1)}
                        if profile not in result.social_profiles:
                            result.social_profiles.append(profile)

                # Also check links for social profiles
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    for platform, pattern in SOCIAL_PATTERNS.items():
                        match = pattern.search(href)
                        if match:
                            profile = {"platform": platform, "username": match.group(1), "url": href}
                            if profile not in result.social_profiles:
                                result.social_profiles.append(profile)

    except asyncio.TimeoutError:
        result.error = "Request timeout"
    except aiohttp.ClientError as e:
        result.error = str(e)
    except Exception as e:
        result.error = f"Unexpected error: {e}"

    return result


async def deep_crawl(
    start_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    max_concurrent: int = 10,
) -> DeepScraperResult:
    """
    Deep crawl a website extracting all entities.

    Args:
        start_url: Starting URL
        max_depth: Maximum crawl depth
        max_pages: Maximum pages to crawl
        max_concurrent: Maximum concurrent requests

    Returns:
        DeepScraperResult with all extracted entities
    """
    import aiohttp
    from bs4 import BeautifulSoup

    start_time = time.perf_counter()

    # Parse start URL
    parsed = urlparse(start_url)
    if not parsed.scheme:
        start_url = f"https://{start_url}"
        parsed = urlparse(start_url)

    base_domain = parsed.netloc.lower()

    # Track visited URLs
    visited = set()
    to_visit = [(start_url, 0)]  # (url, depth)

    all_emails = set()
    all_phones = set()
    all_internal_links = set()
    all_external_links = set()
    all_documents = []
    all_social_profiles = []
    page_results = []

    semaphore = asyncio.Semaphore(max_concurrent)

    async with aiohttp.ClientSession() as session:
        while to_visit and len(visited) < max_pages:
            url, depth = to_visit.pop(0)

            if url in visited or depth > max_depth:
                continue

            visited.add(url)

            # Scrape the page
            page_result = await scrape_page(session, url, base_domain, semaphore)
            page_results.append(page_result)

            if page_result.error:
                continue

            # Aggregate results
            all_emails.update(page_result.emails)
            all_phones.update(page_result.phone_numbers)
            all_internal_links.update(page_result.internal_links)
            all_external_links.update(page_result.external_links)

            for doc in page_result.documents:
                if doc not in all_documents:
                    all_documents.append(doc)

            for profile in page_result.social_profiles:
                if profile not in all_social_profiles:
                    all_social_profiles.append(profile)

            # Queue internal links for crawling
            if depth < max_depth:
                for link in page_result.internal_links:
                    if link not in visited:
                        to_visit.append((link, depth + 1))

            # Sort to_visit by depth (BFS)
            to_visit.sort(key=lambda x: x[1])

    # Extract metadata from documents
    if all_documents:
        import aiohttp

        async def fetch_metadata(doc: DocumentMetadata) -> DocumentMetadata:
            return await extract_metadata_from_document(doc.url)

        async with aiohttp.ClientSession() as session:
            tasks = [fetch_metadata(doc) for doc in all_documents[:20]]  # Limit to 20 docs
            metadata_results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(metadata_results):
                if isinstance(result, DocumentMetadata):
                    all_documents[i] = result

    end_time = time.perf_counter()

    return DeepScraperResult(
        target_url=start_url,
        crawl_depth=max_depth,
        max_depth=max_depth,
        pages_crawled=len([p for p in page_results if not p.error]),
        pages_failed=len([p for p in page_results if p.error]),
        total_emails=len(all_emails),
        total_phones=len(all_phones),
        total_internal_links=len(all_internal_links),
        total_external_links=len(all_external_links),
        total_documents=len(all_documents),
        all_emails=sorted(all_emails),
        all_phones=sorted(all_phones),
        all_internal_links=sorted(all_internal_links),
        all_external_links=sorted(all_external_links),
        all_documents=all_documents,
        all_social_profiles=all_social_profiles,
        page_results=page_results,
        crawl_time_ms=(end_time - start_time) * 1000,
    )


def deep_scraper(
    url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    max_concurrent: int = 10,
) -> dict:
    """
    Main entry point - deep scrape a URL for all entities.

    Args:
        url: URL to scrape
        max_depth: Maximum crawl depth
        max_pages: Maximum pages to crawl
        max_concurrent: Maximum concurrent requests

    Returns:
        Dict with all extracted entities
    """
    import asyncio, concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(deep_crawl(url, max_depth, max_pages, max_concurrent))
        finally:
            loop.close()
    return result.to_dict()


if __name__ == "__main__":
    # CLI entry point for subprocess execution
    import json

    payload = json.loads(sys.stdin.read())
    url = payload.get("url", "")
    max_depth = payload.get("max_depth", 2)
    max_pages = payload.get("max_pages", 50)
    max_concurrent = payload.get("max_concurrent", 10)

    result = deep_scraper(url, max_depth, max_pages, max_concurrent)
    print(json.dumps(result))
