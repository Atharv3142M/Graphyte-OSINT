"""
GitHub OSINT — keyless with optional token for higher rate limits.
"""
from __future__ import annotations

import os
from typing import Any

import requests

_API = "https://api.github.com"
_USER_AGENT = "Graphyte-OSINT/1.0"
_TIMEOUT = 15


def _headers(token: str | None) -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": _USER_AGENT}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(path: str, token: str | None) -> tuple[dict | list | None, int | None, str | None]:
    try:
        r = requests.get(f"{_API}{path}", headers=_headers(token), timeout=_TIMEOUT)
        if r.status_code == 404:
            return None, 404, "Not found"
        if r.status_code == 403:
            return None, 403, r.json().get("message", "Rate limited or forbidden")
        if r.status_code >= 400:
            return None, r.status_code, r.text[:200]
        return r.json(), r.status_code, None
    except requests.RequestException as e:
        return None, None, str(e)


def github_osint_lookup(
    target: str,
    lookup_type: str = "auto",
    api_token: str | None = None,
    max_repos: int = 30,
) -> dict[str, Any]:
    """
    Lookup GitHub user or organization profile and public repositories.
    """
    query = (target or "").strip().removeprefix("@")
    if not query:
        return {"success": False, "error": "Target is required", "target": target}

    token = api_token or os.getenv("GITHUB_TOKEN") or os.getenv("VAULT_GITHUB_TOKEN")
    ltype = (lookup_type or "auto").lower()
    if ltype == "auto":
        ltype = "username"

    result: dict[str, Any] = {
        "success": False,
        "target": query,
        "lookup_type": ltype,
        "profile": None,
        "repositories": [],
        "emails_public": [],
        "error": None,
    }

    if ltype in ("username", "user"):
        data, status, err = _get(f"/users/{query}", token)
        if data is None:
            result["error"] = err or "User lookup failed"
            result["http_status"] = status
            return result
        result["profile"] = {
            "login": data.get("login"),
            "name": data.get("name"),
            "bio": data.get("bio"),
            "company": data.get("company"),
            "blog": data.get("blog"),
            "location": data.get("location"),
            "email": data.get("email"),
            "twitter": data.get("twitter_username"),
            "public_repos": data.get("public_repos"),
            "followers": data.get("followers"),
            "following": data.get("following"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "html_url": data.get("html_url"),
            "avatar_url": data.get("avatar_url"),
        }
        if data.get("email"):
            result["emails_public"].append(data["email"])

        repos, _, repo_err = _get(f"/users/{query}/repos?per_page={min(max_repos, 100)}&sort=updated", token)
        if isinstance(repos, list):
            result["repositories"] = [
                {
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "html_url": r.get("html_url"),
                    "description": (r.get("description") or "")[:200],
                    "language": r.get("language"),
                    "stars": r.get("stargazers_count"),
                    "forks": r.get("forks_count"),
                    "updated_at": r.get("updated_at"),
                }
                for r in repos[:max_repos]
            ]
        elif repo_err:
            result["repos_error"] = repo_err

    elif ltype in ("org", "organization"):
        data, status, err = _get(f"/orgs/{query}", token)
        if data is None:
            result["error"] = err or "Organization lookup failed"
            result["http_status"] = status
            return result
        result["profile"] = {
            "login": data.get("login"),
            "name": data.get("name"),
            "description": data.get("description"),
            "blog": data.get("blog"),
            "location": data.get("location"),
            "email": data.get("email"),
            "public_repos": data.get("public_repos"),
            "html_url": data.get("html_url"),
            "avatar_url": data.get("avatar_url"),
        }
        repos, _, _ = _get(f"/orgs/{query}/repos?per_page={min(max_repos, 100)}", token)
        if isinstance(repos, list):
            result["repositories"] = [
                {
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "html_url": r.get("html_url"),
                    "language": r.get("language"),
                    "stars": r.get("stargazers_count"),
                }
                for r in repos[:max_repos]
            ]
    else:
        result["error"] = f"Unsupported lookup_type: {lookup_type}"
        return result

    result["success"] = True
    result["repo_count"] = len(result["repositories"])
    return result
