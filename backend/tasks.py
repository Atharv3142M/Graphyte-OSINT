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

    proc = subprocess.Popen(
        [sys.executable, "-m", "run_module", module_name],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(os.path.abspath(__file__)),
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


def _run_module_subprocess(
    module_name: str,
    payload: dict,
    task_id: str,
    redis_client,
) -> dict:
    """
    Optionally create a temporary config for sensitive modules, then spawn and stream.
    """
    service = MODULE_SECRET_SERVICE.get(module_name)
    if service:
        with temporary_service_config(service) as (_, config_path):
            extra_env = {
                "OSINT_CONFIG_FILE": config_path,
                "OSINT_SERVICE": service,
            }
            return _spawn_and_stream(module_name, payload, task_id, redis_client, extra_env)
    return _spawn_and_stream(module_name, payload, task_id, redis_client)


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
