"""
social_hunter.py - Sherlock-style username enumeration across 50+ platforms.

Given a username, asynchronously checks HTTP status codes across major social media
platforms to determine if the profile exists. Completely keyless and passive - no
APIs required, only HTTP GET requests with standard browser headers.

Output format:
{
    "success": true,
    "username": "<target>",
    "found": [<list of platforms where username exists>],
    "not_found": [<list of platforms checked but username doesn't exist>],
    "errors": [<list of platforms that failed to check>],
    "profiles": [
        {"platform": "twitter", "url": "...", "status": "found"},
        ...
    ]
}
"""
from __future__ import annotations

import asyncio
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# Known false positive patterns - if response contains these, likely 404 page
FALSE_POSITIVE_PATTERNS = [
    r"page not found",
    r"user not found",
    r"profile not found",
    r"account suspended",
    r"account deleted",
    r"this page isn't available",
    r"the page you requested was not found",
    r"404",
    r"not found",
    r"doesn't exist",
]


@dataclass
class PlatformResult:
    """Result for a single platform check."""
    platform: str
    url: str
    status: str  # "found", "not_found", "error"
    http_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class SocialHunterResult:
    """Complete result from username enumeration."""
    username: str
    platforms_checked: int = 0
    found_count: int = 0
    not_found_count: int = 0
    error_count: int = 0
    profiles: list[PlatformResult] = field(default_factory=list)
    total_time_ms: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "success": True,
            "username": self.username,
            "platforms_checked": self.platforms_checked,
            "found_count": self.found_count,
            "not_found_count": self.not_found_count,
            "error_count": self.error_count,
            "found": [p.platform for p in self.profiles if p.status == "found"],
            "not_found": [p.platform for p in self.profiles if p.status == "not_found"],
            "errors": [p.platform for p in self.profiles if p.status == "error"],
            "profiles": [
                {
                    "platform": p.platform,
                    "url": p.url,
                    "status": p.status,
                    "http_status": p.http_status,
                    "response_time_ms": round(p.response_time_ms, 2) if p.response_time_ms else None,
                }
                for p in self.profiles
            ],
            "total_time_ms": round(self.total_time_ms, 2) if self.total_time_ms else None,
        }


# fmt: off
# 50+ major social media platforms - URL patterns for username checks
SOCIAL_PLATFORMS: dict[str, str] = {
    # Major social networks
    "facebook": "https://www.facebook.com/{username}",
    "twitter": "https://twitter.com/{username}",
    "instagram": "https://www.instagram.com/{username}/",
    "linkedin": "https://www.linkedin.com/in/{username}/",
    "tiktok": "https://www.tiktok.com/@{username}",
    "snapchat": "https://www.snapchat.com/add/{username}",
    "pinterest": "https://www.pinterest.com/{username}/",
    "reddit": "https://www.reddit.com/user/{username}/",
    "tumblr": "https://{username}.tumblr.com/",

    # Developer/tech platforms
    "github": "https://github.com/{username}",
    "gitlab": "https://gitlab.com/{username}",
    "stackoverflow": "https://stackoverflow.com/users/{username}",
    "devto": "https://dev.to/{username}",
    "codepen": "https://codepen.io/{username}",
    "replit": "https://replit.com/@{username}",
    "npm": "https://www.npmjs.com/~{username}",
    "pypi": "https://pypi.org/user/{username}",
    "dockerhub": "https://hub.docker.com/u/{username}",
    "keybase": "https://keybase.io/{username}",
    "medium": "https://medium.com/@{username}",
    "hashnode": "https://{username}.hashnode.dev/",

    # Gaming platforms
    "steam": "https://steamcommunity.com/id/{username}",
    "twitch": "https://www.twitch.tv/{username}",
    "roblox": "https://www.roblox.com/user.aspx?username={username}",
    "xbox": "https://xboxgamertag.com/search/{username}",
    "playstation": "https://psnprofiles.com/{username}",
    "origin": "https://www.origin.com/profile/{username}",
    "epicgames": "https://www.epicgames.com/id/{username}",

    # Content sharing
    "youtube": "https://www.youtube.com/@{username}",
    "vimeo": "https://vimeo.com/{username}",
    "soundcloud": "https://soundcloud.com/{username}",
    "spotify": "https://open.spotify.com/user/{username}",
    "bandcamp": "https://bandcamp.com/{username}",
    "flickr": "https://www.flickr.com/photos/{username}/",
    "500px": "https://500px.com/p/{username}",
    "unsplash": "https://unsplash.com/@{username}",
    "behance": "https://www.behance.net/{username}",
    "dribbble": "https://dribbble.com/{username}",
    "artstation": "https://www.artstation.com/{username}",
    "deviantart": "https://www.deviantart.com/{username}",

    # Business/professional
    "angellist": "https://angel.co/u/{username}",
    "producthunt": "https://www.producthunt.com/@{username}",
    "crunchbase": "https://www.crunchbase.com/person/{username}",
    "slideshare": "https://www.slideshare.net/{username}",
    "aboutme": "https://about.me/{username}",
    "linktr": "https://linktr.ee/{username}",
    "carrd": "https://{username}.carrd.co/",

    # Forums/communities
    "discord": "https://discord.com/users/{username}",
    "telegram": "https://t.me/{username}",
    "whatsapp": "https://wa.me/{username}",
    "signal": "https://signal.org/u/{username}",
    "mastodon": "https://mastodon.social/@{username}",
    "bluesky": "https://bsky.app/profile/{username}.bsky.social",
    "4chan": "https://boards.4channel.org/search?q={username}",
    "8kun": "https://8kun.top/search.html?search={username}",

    # Dating (if relevant for investigations)
    "okcupid": "https://www.okcupid.com/profile/{username}",
    "pof": "https://www.pof.com/viewprofile.aspx?user_id={username}",
    "bumble": "https://bumble.com/{username}",

    # Other notable platforms
    "gravatar": "https://en.gravatar.com/{username}",
    "wordpress": "https://{username}.wordpress.com/",
    "blogger": "https://{username}.blogspot.com/",
    "livejournal": "https://{username}.livejournal.com/",
    "vk": "https://vk.com/{username}",
    "ok": "https://ok.ru/{username}",
    "weibo": "https://weibo.com/u/{username}",
    "patreon": "https://www.patreon.com/{username}",
    "onlyfans": "https://onlyfans.com/{username}",
    "cashapp": "https://cash.app/${username}",
    "venmo": "https://venmo.com/{username}",
    "paypal": "https://paypal.me/{username}",
    "gofundme": "https://www.gofundme.com/f/{username}",
    "kickstarter": "https://www.kickstarter.com/profile/{username}",
    "indiegogo": "https://www.indiegogo.com/individual/{username}",
}

# Expected HTTP status codes for "found" profiles
# Most platforms return 200 for existing profiles
FOUND_STATUS_CODES = {200, 201, 202, 301, 302}

# Platforms that redirect non-existent users to a default page
# These need special handling
REDIRECT_PLATFORMS = {"facebook", "instagram", "youtube"}
# fmt: on


async def check_platform(
    session,
    platform: str,
    username: str,
    url_template: str,
) -> PlatformResult:
    """
    Check if a username exists on a specific platform.

    Args:
        session: aiohttp ClientSession
        platform: Platform name
        username: Username to check
        url_template: URL template with {username} placeholder

    Returns:
        PlatformResult with status and metadata
    """
    import aiohttp

    url = url_template.format(username=username)
    start_time = time.perf_counter()

    # Custom headers to look like a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        async with session.get(url, headers=headers, allow_redirects=True, timeout=10) as response:
            response_time = (time.perf_counter() - start_time) * 1000
            status_code = response.status
            text = await response.text()

            # Check for false positives
            text_lower = text.lower()
            is_false_positive = any(
                re.search(pattern, text_lower) for pattern in FALSE_POSITIVE_PATTERNS
            )

            # Special handling for platforms with known behaviors
            if platform in REDIRECT_PLATFORMS:
                # Some platforms redirect to login/home for non-existent users
                # Check if we're still on the expected URL pattern
                if str(response.url) != url and platform not in str(response.url):
                    return PlatformResult(
                        platform=platform,
                        url=url,
                        status="not_found",
                        http_status=status_code,
                        response_time_ms=response_time,
                    )

            if status_code in FOUND_STATUS_CODES and not is_false_positive:
                return PlatformResult(
                    platform=platform,
                    url=url,
                    status="found",
                    http_status=status_code,
                    response_time_ms=response_time,
                )
            elif status_code == 404:
                return PlatformResult(
                    platform=platform,
                    url=url,
                    status="not_found",
                    http_status=status_code,
                    response_time_ms=response_time,
                )
            else:
                # Ambiguous status - might be rate limited or blocked
                return PlatformResult(
                    platform=platform,
                    url=url,
                    status="error",
                    http_status=status_code,
                    response_time_ms=response_time,
                    error_message=f"Ambiguous status code: {status_code}",
                )

    except asyncio.TimeoutError:
        return PlatformResult(
            platform=platform,
            url=url,
            status="error",
            error_message="Request timeout",
        )
    except aiohttp.ClientError as e:
        return PlatformResult(
            platform=platform,
            url=url,
            status="error",
            error_message=str(e),
        )
    except Exception as e:
        return PlatformResult(
            platform=platform,
            url=url,
            status="error",
            error_message=f"Unexpected error: {e}",
        )


async def hunt_usernames(
    username: str,
    platforms: Optional[dict[str, str]] = None,
    max_concurrent: int = 20,
) -> SocialHunterResult:
    """
    Hunt for a username across multiple social media platforms.

    Args:
        username: Username to search for
        platforms: Dict of platform_name -> url_template (defaults to SOCIAL_PLATFORMS)
        max_concurrent: Maximum concurrent requests (default 20)

    Returns:
        SocialHunterResult with all findings
    """
    import aiohttp

    if platforms is None:
        platforms = SOCIAL_PLATFORMS

    start_time = time.perf_counter()

    # Validate username
    if not username or len(username) < 2:
        return SocialHunterResult(
            username=username,
            error_count=1,
            profiles=[
                PlatformResult(
                    platform="validation",
                    url="",
                    status="error",
                    error_message="Username must be at least 2 characters",
                )
            ],
        )

    # Sanitize username - only allow alphanumeric, underscore, hyphen
    clean_username = re.sub(r"[^a-zA-Z0-9_-]", "", username)
    if not clean_username:
        return SocialHunterResult(
            username=username,
            error_count=1,
            profiles=[
                PlatformResult(
                    platform="validation",
                    url="",
                    status="error",
                    error_message="No valid characters in username",
                )
            ],
        )

    async with aiohttp.ClientSession() as session:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_check(platform: str, url_template: str) -> PlatformResult:
            async with semaphore:
                # Small random delay to avoid burst detection
                await asyncio.sleep(0.05)
                return await check_platform(session, platform, clean_username, url_template)

        tasks = [
            bounded_check(platform, url_template)
            for platform, url_template in platforms.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    profiles = []
    for result in results:
        if isinstance(result, Exception):
            profiles.append(
                PlatformResult(
                    platform="unknown",
                    url="",
                    status="error",
                    error_message=str(result),
                )
            )
        elif isinstance(result, PlatformResult):
            profiles.append(result)

    end_time = time.perf_counter()

    return SocialHunterResult(
        username=clean_username,
        platforms_checked=len(profiles),
        found_count=sum(1 for p in profiles if p.status == "found"),
        not_found_count=sum(1 for p in profiles if p.status == "not_found"),
        error_count=sum(1 for p in profiles if p.status == "error"),
        profiles=profiles,
        total_time_ms=(end_time - start_time) * 1000,
    )


def social_hunter(
    username: str,
    platforms: Optional[dict[str, str]] = None,
    max_concurrent: int = 20,
) -> dict:
    """
    Main entry point - hunt for a username across social media platforms.

    Args:
        username: Username to search for
        platforms: Optional custom platform list
        max_concurrent: Max concurrent requests

    Returns:
        Dict with findings (compatible with STIX pipeline)
    """
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(hunt_usernames(username, platforms, max_concurrent))
        finally:
            loop.close()
    return result.to_dict()


if __name__ == "__main__":
    # CLI entry point for subprocess execution
    import json

    payload = json.loads(sys.stdin.read())
    username = payload.get("username", "")
    platforms = payload.get("platforms")
    max_concurrent = payload.get("max_concurrent", 20)

    result = social_hunter(username, platforms, max_concurrent)
    print(json.dumps(result))
