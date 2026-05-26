"""
Dynamic, headless configuration injection for OSINT modules.

Retrieves credentials from PostgreSQL user_configs (or env fallback)
and materializes them as ephemeral config files in a per-task temporary
directory. The directory is destroyed immediately after the subprocess exits.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Dict, Iterator, Optional, Tuple


def _fetch_credentials(service: str, tenant_id: Optional[str] = None) -> Dict[str, str]:
    """
    Fetch credentials for the given service.
    Tries PostgreSQL user_configs first (when tenant_id or DEFAULT_TENANT_ID is set),
    then falls back to environment variables.
    """
    service = service.lower()
    tid = tenant_id or os.getenv("DEFAULT_TENANT_ID")

    if tid:
        try:
            from postgres_client import fetch_service_credentials
            creds = fetch_service_credentials(tid, service)
            if creds:
                return creds
        except Exception:
            pass

    # Fallback to environment variables
    if service == "shodan":
        key = os.getenv("VAULT_SHODAN_API_KEY", "") or os.getenv("SHODAN_API_KEY", "")
        return {"api_key": key} if key else {}
    if service == "censys":
        api_id = os.getenv("VAULT_CENSYS_API_ID", "") or os.getenv("CENSYS_API_ID", "")
        api_secret = os.getenv("VAULT_CENSYS_API_SECRET", "") or os.getenv("CENSYS_API_SECRET", "")
        return {"api_id": api_id, "api_secret": api_secret}
    if service == "github":
        token = os.getenv("VAULT_GITHUB_TOKEN", "") or os.getenv("GITHUB_TOKEN", "")
        return {"api_token": token} if token else {}
    return {}


@contextmanager
def temporary_service_config(
    service: str,
    tenant_id: Optional[str] = None,
) -> Iterator[Tuple[str, str]]:
    """
    Create a temporary, isolated directory with a JSON config file
    for the given service. Directory is destroyed on exit.

    Returns (tmpdir, config_path).
    """
    secrets = _fetch_credentials(service, tenant_id)
    tmpdir = tempfile.mkdtemp(prefix=f"osint_{service.lower()}_")
    config_path = os.path.join(tmpdir, f"{service.lower()}_config.json")

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(secrets, f)

    try:
        yield tmpdir, config_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
