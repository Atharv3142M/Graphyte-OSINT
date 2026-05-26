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
from backend.normalize import normalize_result

# Strict hard timeout (seconds). Subprocess is killed if exceeded.
TASK_HARD_TIMEOUT = int(os.getenv("CELERY_TASK_HARD_TIMEOUT", "300"))

# Redis pub channel prefix
REDIS_CHAN_PREFIX = "osint:task:stream:"

# Modules that require secrets from the dynamic config system.
MODULE_SECRET_SERVICE: Dict[str, str] = {
    "shodan_recon": "shodan",
    "censys_recon": "censys",
    "github_osint": "github",
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
    playbook_chan: Optional[str] = None,
) -> dict:
    import subprocess

    chan = f"{REDIS_CHAN_PREFIX}{task_id}"
    stdin_json = json.dumps(payload).encode("utf-8")
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

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
                    if playbook_chan:
                        redis_client.publish(
                            playbook_chan,
                            json.dumps({"type": "stdout", "module": module_name, "data": text}),
                        )
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
                    stderr_lines.append(text)
                    msg = json.dumps({"stream": "stderr", "data": text})
                    redis_client.publish(chan, msg)
                    if playbook_chan:
                        redis_client.publish(
                            playbook_chan,
                            json.dumps({"type": "stderr", "module": module_name, "data": text}),
                        )
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

    envelope: dict = {}
    has_error = True
    error_msg: Optional[str] = None

    try:
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
            error_msg = f"Task timeout (SIGKILL after {TASK_HARD_TIMEOUT}s)"
            envelope = normalize_result(module_name, {"error": error_msg, "success": False})
            has_error = True
            return envelope

        # Robust JSON extraction: scan stdout lines from the END for the first
        # parseable JSON object. This guarantees we still recover the result
        # even if stray prints leaked through (third-party libs, deprecation
        # warnings, etc.).
        raw_result: dict | None = None
        for line in reversed(stdout_lines):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                raw_result = parsed
                break

        if raw_result is None:
            err_msg = "\n".join(stderr_lines[-20:]).strip() or "No output from module"
            # Include first stdout line for debugging when JSON parsing failed
            preview = (stdout_lines[0] if stdout_lines else "")[:500]
            raw_result = {
                "error": err_msg,
                "stdout_preview": preview,
                "success": False,
            }

        envelope = normalize_result(module_name, raw_result)
        has_error = not bool(envelope.get("ok"))
        try:
            errors = envelope.get("errors") or []
            if errors and isinstance(errors, list) and isinstance(errors[0], dict):
                error_msg = errors[0].get("message")
        except Exception:
            error_msg = None
        return envelope

    except Exception as e:
        # Last-resort safety net: never let an exception in this function
        # silently leave the WS hanging without a `done` event.
        envelope = normalize_result(
            module_name,
            {"error": f"tasks._spawn_and_stream crashed: {e}", "success": False},
        )
        has_error = True
        error_msg = str(e)
        return envelope

    finally:
        # ALWAYS publish result + done so frontends never wait forever.
        try:
            redis_client.publish(chan, json.dumps({"type": "result", "data": envelope}))
        except Exception:
            pass
        try:
            done_payload = {
                "type": "done",
                "error": bool(has_error),
                "error_msg": error_msg,
            }
            if killed.is_set():
                done_payload["killed"] = True
            redis_client.publish(chan, json.dumps(done_payload))
        except Exception:
            pass
        if playbook_chan:
            try:
                redis_client.publish(
                    playbook_chan,
                    json.dumps({"type": "result", "module": module_name, "data": envelope}),
                )
                redis_client.publish(
                    playbook_chan,
                    json.dumps(
                        {
                            "type": "done",
                            "module": module_name,
                            "status": "failure" if has_error else "success",
                            "error": error_msg if has_error else None,
                        }
                    ),
                )
            except Exception:
                pass


def _ingest_stix_bundle(module_name: str, envelope: dict) -> None:
    """Convert module result to STIX bundle and ingest into Neo4j."""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from backend.stix_pipeline import build_stix_bundle
        from backend.neo4j_client import Neo4jClient

        raw = envelope.get("raw") if isinstance(envelope, dict) else None
        if not isinstance(raw, dict):
            raw = {}
        bundle = build_stix_bundle(module_name, raw)
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
    playbook_chan: Optional[str] = None,
) -> dict:
    """
    Optionally create a temporary config for sensitive modules, then spawn and stream.
    After a successful result, ingest STIX bundle into Neo4j.
    """
    import logging
    logger = logging.getLogger(__name__)

    service = MODULE_SECRET_SERVICE.get(module_name)
    if service:
        with temporary_service_config(service) as (_, config_path):
            extra_env = {
                "OSINT_CONFIG_FILE": config_path,
                "OSINT_SERVICE": service,
            }
            result = _spawn_and_stream(module_name, payload, task_id, redis_client, extra_env, playbook_chan)
    else:
        result = _spawn_and_stream(module_name, payload, task_id, redis_client, None, playbook_chan)

    # Best-effort STIX enrichment — don't fail the task if Neo4j is unavailable
    has_error = not bool(result and result.get("ok", False))
    logger.debug("[STIX] module=%s result_success=%s has_error=%s", module_name, not has_error, bool(has_error))
    if not has_error:
        _ingest_stix_bundle(module_name, result)

    return result


@celery_app.task(
    bind=True,
    name="tasks.shodan_recon",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_shodan(self, target: str, api_key: str | None = None, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"target": target, "api_key": api_key}
    redis_client = _get_redis()
    return _run_module_subprocess("shodan_recon", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.censys_recon",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_censys(self, target: str, api_id: str | None = None, api_secret: str | None = None, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"target": target, "api_id": api_id, "api_secret": api_secret}
    redis_client = _get_redis()
    return _run_module_subprocess("censys_recon", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.scrape_urls",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_scrape(self, urls: list[str], max_workers: int = 5, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"urls": urls, "max_workers": max_workers}
    redis_client = _get_redis()
    return _run_module_subprocess("scraper", payload, self.request.id, redis_client, playbook_chan)


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
    playbook_id: str | None = None,
    playbook_chan: str | None = None,
):
    payload = {"host": host, "ports": ports, "max_workers": max_workers, "timeout": timeout}
    redis_client = _get_redis()
    return _run_module_subprocess("port_scanner", payload, self.request.id, redis_client, playbook_chan)


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
    playbook_id: str | None = None,
    playbook_chan: str | None = None,
):
    payload = {"domain": domain, "brute_subdomains": brute_subdomains, "wordlist": wordlist}
    redis_client = _get_redis()
    return _run_module_subprocess("dns_intel", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.whois_lookup",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_whois_lookup(self, domain: str, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"domain": domain}
    redis_client = _get_redis()
    return _run_module_subprocess("whois_lookup", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.ssl_analyze",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_ssl_analyze(self, host: str, port: int = 443, timeout: int = 10, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"host": host, "port": port, "timeout": timeout}
    redis_client = _get_redis()
    return _run_module_subprocess("ssl_analyzer", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.http_security",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_http_security(self, url: str, timeout: int = 10, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"url": url, "timeout": timeout}
    redis_client = _get_redis()
    return _run_module_subprocess("http_security", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.tech_stack",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_tech_stack(self, url: str, timeout: int = 10, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"url": url, "timeout": timeout}
    redis_client = _get_redis()
    return _run_module_subprocess("tech_stack", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.metadata_extractor",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_metadata_extract(self, file_path: str, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"file_path": file_path}
    redis_client = _get_redis()
    return _run_module_subprocess("metadata_extractor", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.graysentinel_ingest",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_graysentinel_ingest(self, urls: list[str], strategies: list[str] | None = None, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"urls": urls, "strategies": strategies}
    redis_client = _get_redis()
    return _run_module_subprocess("graysentinel_ingest", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.cyberninja_passive",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_cyberninja_passive(self, usernames: list[str], timeout: float | None = None, site_list: list[str] | None = None, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"usernames": usernames, "timeout": timeout, "site_list": site_list}
    redis_client = _get_redis()
    return _run_module_subprocess("cyberninja_passive", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.xrecon",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_xrecon(self, query: str, query_type: str = "username", playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"query": query, "query_type": query_type}
    redis_client = _get_redis()
    return _run_module_subprocess("xrecon", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.social_hunter",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_social_hunter(self, username: str, max_concurrent: int = 20, playbook_id: str | None = None, playbook_chan: str | None = None):
    """
    Hunt for a username across 50+ social media platforms.
    Keyless/passive - uses HTTP status code checks only.
    """
    payload = {"username": username, "max_concurrent": max_concurrent}
    redis_client = _get_redis()
    return _run_module_subprocess("social_hunter", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.cert_transparency",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_cert_transparency(self, domain: str, use_html_fallback: bool = True, playbook_id: str | None = None, playbook_chan: str | None = None):
    """
    Discover subdomains via Certificate Transparency logs (crt.sh).
    Keyless/passive - scrapes public CT logs.
    """
    payload = {"domain": domain, "use_html_fallback": use_html_fallback}
    redis_client = _get_redis()
    return _run_module_subprocess("cert_transparency", payload, self.request.id, redis_client, playbook_chan)


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
    playbook_id: str | None = None,
    playbook_chan: str | None = None,
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
    return _run_module_subprocess("deep_scraper", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.ip_geolocation",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_ip_geolocation(self, target: str, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"target": target}
    redis_client = _get_redis()
    return _run_module_subprocess("ip_geolocation", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.reverse_ip_lookup",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_reverse_ip_lookup(self, target: str, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"target": target}
    redis_client = _get_redis()
    return _run_module_subprocess("reverse_ip_lookup", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.bgp_asn_lookup",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_bgp_asn_lookup(self, target: str, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"target": target}
    redis_client = _get_redis()
    return _run_module_subprocess("bgp_asn_lookup", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.wayback_machine",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_wayback_machine(self, target: str, limit: int = 50, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"target": target, "limit": limit}
    redis_client = _get_redis()
    return _run_module_subprocess("wayback_machine", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.email_header_analyzer",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_email_header_analyzer(self, raw_headers: str, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"raw_headers": raw_headers}
    redis_client = _get_redis()
    return _run_module_subprocess("email_header_analyzer", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.sherlock_hunt",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_sherlock_hunt(
    self,
    username: str,
    timeout: int = 10,
    max_connections: int = 5,
    playbook_id: str | None = None,
    playbook_chan: str | None = None,
):
    payload = {"username": username, "timeout": timeout, "max_connections": max_connections}
    redis_client = _get_redis()
    return _run_module_subprocess("sherlock_hunt", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.robots_sitemap",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_robots_sitemap(
    self,
    domain: str,
    max_sitemap_urls: int = 200,
    playbook_id: str | None = None,
    playbook_chan: str | None = None,
):
    payload = {"domain": domain, "max_sitemap_urls": max_sitemap_urls}
    redis_client = _get_redis()
    return _run_module_subprocess("robots_sitemap", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.favicon_hash",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_favicon_hash(self, domain: str, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"domain": domain}
    redis_client = _get_redis()
    return _run_module_subprocess("favicon_hash", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.username_permutator",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_username_permutator(
    self,
    seed: str,
    max_results: int = 50,
    playbook_id: str | None = None,
    playbook_chan: str | None = None,
):
    payload = {"seed": seed, "max_results": max_results}
    redis_client = _get_redis()
    return _run_module_subprocess("username_permutator", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.github_osint",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_github_osint(
    self,
    target: str,
    lookup_type: str = "auto",
    api_token: str | None = None,
    max_repos: int = 30,
    playbook_id: str | None = None,
    playbook_chan: str | None = None,
):
    payload = {"target": target, "lookup_type": lookup_type, "api_token": api_token, "max_repos": max_repos}
    redis_client = _get_redis()
    return _run_module_subprocess("github_osint", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.phone_intel",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_phone_intel(
    self,
    number: str,
    default_region: str = "US",
    playbook_id: str | None = None,
    playbook_chan: str | None = None,
):
    payload = {"number": number, "default_region": default_region}
    redis_client = _get_redis()
    return _run_module_subprocess("phone_intel", payload, self.request.id, redis_client, playbook_chan)


@celery_app.task(
    bind=True,
    name="tasks.email_reputation",
    soft_time_limit=TASK_HARD_TIMEOUT,
    time_limit=TASK_HARD_TIMEOUT + 10,
)
def task_email_reputation(self, email: str, playbook_id: str | None = None, playbook_chan: str | None = None):
    payload = {"email": email}
    redis_client = _get_redis()
    return _run_module_subprocess("email_reputation", payload, self.request.id, redis_client, playbook_chan)
