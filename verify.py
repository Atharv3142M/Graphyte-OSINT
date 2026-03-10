#!/usr/bin/env python3
"""
Unified Verification CLI for Unified Enterprise OSINT Platform.

Steps:
1) Infrastructure check (Postgres, Redis, RabbitMQ, Neo4j, Weaviate)
2) Database seeding (default tenant + mock configs)
3) Dry-run E2E: start FastAPI + Celery, run investigation simulator, then tear down
"""
from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import time
from typing import Callable, Tuple

ROOT = os.path.dirname(os.path.abspath(__file__))

# Make backend scripts importable
sys.path.insert(0, os.path.join(ROOT, "backend"))

from scripts import check_services, seed_db, simulate_investigation  # type: ignore  # noqa: E402


try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    GREEN = Fore.GREEN + Style.BRIGHT
    RED = Fore.RED + Style.BRIGHT
    YELLOW = Fore.YELLOW + Style.BRIGHT
    CYAN = Fore.CYAN + Style.BRIGHT
    RESET = Style.RESET_ALL
except Exception:  # pragma: no cover - optional
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def _detect_python() -> str:
    """
    Prefer project virtualenv python if available, otherwise sys.executable.
    """
    root = os.path.dirname(os.path.abspath(__file__))
    candidates = []
    if os.name == "nt":
        candidates = [
            os.path.join(root, ".venv", "Scripts", "python.exe"),
            os.path.join(root, "venv", "Scripts", "python.exe"),
        ]
    else:
        candidates = [
            os.path.join(root, ".venv", "bin", "python"),
            os.path.join(root, "venv", "bin", "python"),
        ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return sys.executable


def step1_infra_check() -> bool:
    print(f"{CYAN}Step 1: Infrastructure Check{RESET}")
    services: list[Tuple[str, Callable[[], Tuple[bool, str]]]] = [
        ("PostgreSQL (Port 5432)", check_services.check_postgres),
        ("Redis (Port 6379)", check_services.check_redis),
        ("RabbitMQ (Port 5672)", check_services.check_rabbitmq),
        ("Neo4j (Port 7687)", check_services.check_neo4j),
        ("Weaviate (Port 8080)", check_services.check_weaviate),
    ]
    all_ok = True
    for name, fn in services:
        ok, msg = fn()
        status = f"{GREEN}[✓]{RESET}" if ok else f"{RED}[ ]{RESET}"
        print(f"  {status} {name} - {msg}")
        if not ok:
            all_ok = False
    if not all_ok:
        print()
        print(f"{RED}One or more services are unreachable.{RESET}")
        print("Ensure Docker is running and containers are up:")
        print(f"  {YELLOW}docker compose up -d{RESET}")
    print()
    return all_ok


def step2_seed_db() -> bool:
    print(f"{CYAN}Step 2: Database Seeding{RESET}")
    ok = seed_db.seed()
    print()
    return ok


def _spawn_process(name: str, cmd: list[str]) -> subprocess.Popen:
    kwargs: dict = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "text": True,
    }
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = creationflags
    else:
        kwargs["preexec_fn"] = os.setsid  # type: ignore[attr-defined]
    print(f"  Starting {name}: {' '.join(cmd)}")
    return subprocess.Popen(cmd, **kwargs)  # type: ignore[arg-type]


def _terminate_process(name: str, proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    print(f"  Stopping {name}...")
    try:
        if os.name == "nt":
            try:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            except Exception:
                proc.terminate()
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # type: ignore[arg-type]
    except Exception:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except Exception:
        proc.kill()


async def _wait_for_health(timeout: float = 30.0) -> bool:
    try:
        import httpx
    except ImportError:
        print(f"{YELLOW}[WARN]{RESET} httpx not installed; skipping /health check.")
        return True
    start = time.time()
    async with httpx.AsyncClient(timeout=5) as client:
        while time.time() - start < timeout:
            try:
                r = await client.get(f"{API_BASE}/health")
                if r.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
    return False


async def step3_dry_run() -> bool:
    print(f"{CYAN}Step 3: Dry-Run E2E (FastAPI + Celery){RESET}")
    py = _detect_python()
    uvicorn_cmd = [py, "-m", "uvicorn", "backend.api:app", "--port", "8000"]
    celery_cmd = [py, "-m", "celery", "-A", "backend.celery_app", "worker", "--loglevel=info"]

    uvicorn_proc = _spawn_process("FastAPI (uvicorn)", uvicorn_cmd)
    celery_proc = _spawn_process("Celery worker", celery_cmd)

    try:
        ok_health = await _wait_for_health(timeout=40)
        if not ok_health:
            print(f"{RED}[ERROR]{RESET} FastAPI /health did not become ready in time.")
            return False

        print("  FastAPI /health OK. Running E2E investigation simulator...")
        rc = await simulate_investigation.main()
        return rc == 0
    finally:
        _terminate_process("FastAPI (uvicorn)", uvicorn_proc)
        _terminate_process("Celery worker", celery_proc)
        print()


def main() -> int:
    print(f"{CYAN}Unified OSINT Platform - Unified Verification CLI{RESET}")
    print("=" * 72)

    if not step1_infra_check():
        return 1
    if not step2_seed_db():
        return 1
    ok = asyncio.run(step3_dry_run())
    if not ok:
        print(f"{RED}Dry-run E2E failed. Check FastAPI/Celery logs and retry.{RESET}")
        return 1

    banner = r"""
  ____  __  __ ____ _____ ___ _   _    ____  _____ ____  ____   __  __  ___ 
 / ___||  \/  / ___|_   _|_ _| \ | |  / ___|| ____|  _ \|  _ \ |  \/  |/ _ \
 \___ \| |\/| \___ \ | |  | ||  \| |  \___ \|  _| | |_) | |_) || |\/| | | | |
  ___) | |  | |___) || |  | || |\  |   ___) | |___|  __/|  _ < | |  | | |_| |
 |____/|_|  |_|____/ |_| |___|_| \_|  |____/|_____|_|   |_| \_\|_|  |_|\___/
"""
    print(f"{GREEN}{banner}{RESET}")
    print(f"{GREEN}SYSTEM READY - ALL SYSTEMS GO{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

