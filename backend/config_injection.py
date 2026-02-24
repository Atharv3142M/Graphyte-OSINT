"""
Dynamic, headless configuration injection for OSINT modules.

Simulates retrieval of encrypted credentials from a secret store (e.g. Vault)
and materializes them as ephemeral config files in a per-task temporary
directory. The directory is destroyed immediately after the subprocess exits.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Dict, Iterator, Tuple


def _simulate_vault_fetch(service: str) -> Dict[str, str]:
    """
    Simulate fetching encrypted credentials from a secret manager.

    In reality this would talk to HashiCorp Vault (or similar) and decrypt
    secrets inside the worker. Here we read from environment variables only.
    """
    service = service.lower()
    if service == "shodan":
        return {
            "api_key": os.getenv("VAULT_SHODAN_API_KEY", ""),
        }
    if service == "censys":
        return {
            "api_id": os.getenv("VAULT_CENSYS_API_ID", ""),
            "api_secret": os.getenv("VAULT_CENSYS_API_SECRET", ""),
        }
    # Other services can be added here later.
    return {}


@contextmanager
def temporary_service_config(service: str) -> Iterator[Tuple[str, str]]:
    """
    Create a temporary, isolated directory with a JSON config file
    for the given service. Directory is destroyed on exit.

    Returns (tmpdir, config_path).
    """
    secrets = _simulate_vault_fetch(service)
    tmpdir = tempfile.mkdtemp(prefix=f"osint_{service.lower()}_")
    config_path = os.path.join(tmpdir, f"{service.lower()}_config.json")

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(secrets, f)

    try:
        yield tmpdir, config_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

