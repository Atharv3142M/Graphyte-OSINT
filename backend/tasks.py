"""
Celery tasks using subprocess isolation.
Wrapper executes backend/modules via subprocess.Popen, captures stdout/stderr
asynchronously, publishes chunks to Redis. Hard timeout with SIGKILL on hang.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from typing import Dict, Optional

from backend.celery_app import celery_app
from backend.config_injection import temporary_service_config

# Strict hard timeout (seconds). Subprocess is killed if exceeded.
TASK_HARD_TIMEOUT = int(os.getenv("CELERY_TASK_HARD_TIMEOUT", "300"))

# Redis pub channel prefix
REDIS_CHAN_PREFIX = "osint:task:stream:"

# Modules that require secrets from the dynamic config system.
MODULE_SECRET_SERVICE: Dict[str, str] = {
    "shodan_recon": "shodan",
    "censys_recon": "censys",
}


def _get_redis():
    from redis import Redis

    url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(url)


def _spawn_and_stream(
    module_name: str,
    payload: dict,
    task_id: str,
    redis_client,
    extra_env: Optional[Dict[str, str]] = None,
) -> dict:
    import subprocess

    chan = f"{REDIS_CHAN_PREFIX}{task_id}"
    stdin_json = json.dumps(payload).encode("utf-8")
    stdout_lines: list[str] = []

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    # Project root is one level up from backend/ directory
    # This ensures `python -m backend.run_module` can find the backend package
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    proc = subprocess.Popen(
        [sys.executable, "-m", "backend.run_module", module_name],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        bufsize=0,
        env=env,
    )
    proc.stdin.write(stdin_json)
    proc.stdin.close()

    timeout_expired = threading.Event()
    killed = threading.Event()

    def kill_on_timeout():
        if timeout_expired.wait(timeout=TASK_HARD_TIMEOUT):
            return
        timeout_expired.set()
        if not killed.is_set():
            killed.set()
            try:
                proc.kill()  # SIGKILL on Unix, TerminateProcess on Windows
            except ProcessLookupError:
                pass

    def read_stdout(stream):
        try:
            while not timeout_expired.is_set():
                chunk = stream.readline()
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace").rstrip()
                stdout_lines.append(text)
                if text:
                    msg = json.dumps({"stream": "stdout", "data": text})
                    redis_client.publish(chan, msg)
        except Exception:
            pass

    def read_stderr(stream):
        try:
            while not timeout_expired.is_set():
                chunk = stream.readline()
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace").rstrip()
                if text:
                    msg = json.dumps({"stream": "stderr", "data": text})
                    redis_client.publish(chan, msg)
        except Exception:
            pass

    stdout_thread = threading.Thread(target=read_stdout, args=(proc.stdout,), daemon=True)
    stderr_thread = threading.Thread(target=read_stderr, args=(proc.stderr,), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    proc.wait()
    timeout_expired.set()
    stdout_thread.join(timeout=2)
    stderr_thread.join(timeout=2)

    if killed.is_set():
        redis_client.publish(
            chan,
            json.dumps(
                {
                    "stream": "stderr",
                    "data": f"Task killed after {TASK_HARD_TIMEOUT}s timeout (SIGKILL)",
                }
            ),
        )
        redis_client.publish(chan, json.dumps({"type": "done", "killed": True}))
        return {"error": "Task timeout (SIGKILL)", "success": False}

    out = "\n".join(stdout_lines).strip()
    try:
        result = json.loads(out) if out else {"error": "No output"}
    except json.JSONDecodeError:
        result = {"error": "Invalid JSON output", "raw": out[:500]}

    redis_client.publish(chan, json.dumps({"type": "result", "data": result}))
    redis_client.publish(chan, json.dumps({"type": "done"}))
    return result


def _ingest_stix_bundle(module_name: str, result: dict) -> None:
    """Convert module result to STIX bundle and ingest into Neo4j."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from backend.stix_pipeline import build_stix_bundle
        from backend.neo4j_client import Neo4jClient

        bundle = build_stix_bundle(module_name, result)
        if not bundle:
            logger.warning("[STIX] No bundle produced for module=%s (empty or failed result)", module_name)
            return
        client = Neo4jClient()
        client.ingest_bundle(bundle)
        client.close()
        logger.info("[STIX] Ingested bundle for module=%s: %d objects", module_name, len(bundle.get("objects", [])))
    except Exception as e:
        logger.error("[STIX] Ingestion failed for module=%s: %s", module_name, e)


def _run_module_subprocess(
    module_name: str,
    payload: dict,
    task_id: str,
    redis_client,
) -> dict:
    """
    Optionally create a temporary config for sensitive modules, then spawn and stream.
    After a successful result, ingest STIX bundle into Neo4j.
    """
    service = MODULE_SECRET_SERVICE.get(module_name)
    if service:
        with temporary_service_config(service) as (_, config_path):
            extra_env = {
                "OSINT_CONFIG_FILE": config_path,
                "OSINT_SERVICE": service,
            }
            result = _spawn_and_stream(module_name, payload, task_id, redis_client, extra_env)
    else:
        result = _spawn_and_stream(module_name, payload, task_id, redis_client)

    # Best-effort STIX enrichment — don't fail the task if Neo4j is unavailable
    if result and result.get("success") and not result.get("error"):
        _ingest_stix_bundle(module_name, result)

    return result


@celery_app.task(
    bind=True,
    name="tasks.shodan_recon",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_shodan(self, target: str, api_key: str | None = None):
    payload = {"target": target, "api_key": api_key}
    redis_client = _get_redis()
    return _run_module_subprocess("shodan_recon", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.censys_recon",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_censys(self, target: str, api_id: str | None = None, api_secret: str | None = None):
    payload = {"target": target, "api_id": api_id, "api_secret": api_secret}
    redis_client = _get_redis()
    return _run_module_subprocess("censys_recon", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.scrape_urls",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_scrape(self, urls: list[str], max_workers: int = 5):
    payload = {"urls": urls, "max_workers": max_workers}
    redis_client = _get_redis()
    return _run_module_subprocess("scraper", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.port_scan",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_port_scan(
    self,
    host: str,
    ports: list[int] | None = None,
    max_workers: int = 20,
    timeout: float = 2.0,
):
    payload = {"host": host, "ports": ports, "max_workers": max_workers, "timeout": timeout}
    redis_client = _get_redis()
    return _run_module_subprocess("port_scanner", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.dns_intel",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_dns_intel(
    self,
    domain: str,
    brute_subdomains: bool = False,
    wordlist: list[str] | None = None,
):
    payload = {"domain": domain, "brute_subdomains": brute_subdomains, "wordlist": wordlist}
    redis_client = _get_redis()
    return _run_module_subprocess("dns_intel", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.whois_lookup",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_whois_lookup(self, domain: str):
    payload = {"domain": domain}
    redis_client = _get_redis()
    return _run_module_subprocess("whois_lookup", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.ssl_analyze",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_ssl_analyze(self, host: str, port: int = 443, timeout: int = 10):
    payload = {"host": host, "port": port, "timeout": timeout}
    redis_client = _get_redis()
    return _run_module_subprocess("ssl_analyzer", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.http_security",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_http_security(self, url: str, timeout: int = 10):
    payload = {"url": url, "timeout": timeout}
    redis_client = _get_redis()
    return _run_module_subprocess("http_security", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.tech_stack",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_tech_stack(self, url: str, timeout: int = 10):
    payload = {"url": url, "timeout": timeout}
    redis_client = _get_redis()
    return _run_module_subprocess("tech_stack", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.metadata_extractor",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_metadata_extract(self, file_path: str):
    payload = {"file_path": file_path}
    redis_client = _get_redis()
    return _run_module_subprocess("metadata_extractor", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.graysentinel_ingest",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_graysentinel_ingest(self, urls: list[str], strategies: list[str] | None = None):
    payload = {"urls": urls, "strategies": strategies}
    redis_client = _get_redis()
    return _run_module_subprocess("graysentinel_pipeline", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.cyberninja_passive",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_cyberninja_passive(self, usernames: list[str], timeout: float | None = None, site_list: list[str] | None = None):
    payload = {"usernames": usernames, "timeout": timeout, "site_list": site_list}
    redis_client = _get_redis()
    return _run_module_subprocess("cyberninja_passive", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.xrecon",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_xrecon(self, query: str, query_type: str = "username"):
    payload = {"query": query, "query_type": query_type}
    redis_client = _get_redis()
    return _run_module_subprocess("xrecon", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.social_hunter",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_social_hunter(self, username: str, max_concurrent: int = 20):
    """
    Hunt for a username across 50+ social media platforms.
    Keyless/passive - uses HTTP status code checks only.
    """
    payload = {"username": username, "max_concurrent": max_concurrent}
    redis_client = _get_redis()
    return _run_module_subprocess("social_hunter", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.cert_transparency",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_cert_transparency(self, domain: str, use_html_fallback: bool = True):
    """
    Discover subdomains via Certificate Transparency logs (crt.sh).
    Keyless/passive - scrapes public CT logs.
    """
    payload = {"domain": domain, "use_html_fallback": use_html_fallback}
    redis_client = _get_redis()
    return _run_module_subprocess("cert_transparency", payload, self.request.id, redis_client)


@celery_app.task(
    bind=True,
    name="tasks.deep_scraper",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_deep_scraper(
    self,
    url: str,
    max_depth: int = 2,
    max_pages: int = 50,
    max_concurrent: int = 10,
):
    """
    Deep recursive scraper extracting emails, phones, links, documents, and social profiles.
    """
    payload = {
        "url": url,
        "max_depth": max_depth,
        "max_pages": max_pages,
        "max_concurrent": max_concurrent,
    }
    redis_client = _get_redis()
    return _run_module_subprocess("deep_scraper", payload, self.request.id, redis_client)
