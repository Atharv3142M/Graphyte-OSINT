#!/usr/bin/env python3
"""
Master Orchestrator for Unified Enterprise OSINT Platform.

Launches:
- FastAPI backend (uvicorn backend.api:app --reload --port 8000)
- Celery worker (backend.celery_app)
- Next.js frontend (npm run dev --prefix frontend)

All logs are multiplexed with colored prefixes. Ctrl+C stops everything cleanly.
"""
from __future__ import annotations

import os
import argparse
import signal
import socket
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional


try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    FASTAPI_COLOR = Fore.CYAN + Style.BRIGHT
    CELERY_COLOR = Fore.MAGENTA + Style.BRIGHT
    NEXT_COLOR = Fore.YELLOW + Style.BRIGHT
    RESET = Style.RESET_ALL
except Exception:  # pragma: no cover - optional
    FASTAPI_COLOR = "\033[96m"
    CELERY_COLOR = "\033[95m"
    NEXT_COLOR = "\033[93m"
    RESET = "\033[0m"


def _detect_python() -> str:
    """
    Prefer project virtualenv python if available, otherwise sys.executable.
    """
    root = os.path.dirname(os.path.abspath(__file__))
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


def _spawn(
    name: str,
    cmd: List[str] | str,
    cwd: str | None = None,
    use_shell: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.Popen:
    kwargs: Dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
    }
    if cwd:
        kwargs["cwd"] = cwd
    if use_shell:
        kwargs["shell"] = True
    if env:
        merged_env = dict(os.environ)
        merged_env.update(env)
        kwargs["env"] = merged_env
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        kwargs["creationflags"] = creationflags
    else:
        kwargs["preexec_fn"] = os.setsid  # type: ignore[attr-defined]
    if isinstance(cmd, list):
        launch_cmd = " ".join(cmd)
    else:
        launch_cmd = cmd
    print(f"[LAUNCH] {name}: {launch_cmd}")
    return subprocess.Popen(cmd, **kwargs)  # type: ignore[arg-type]


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _find_api_port(preferred: int = 8000, max_tries: int = 25) -> int:
    if _port_is_available(preferred):
        return preferred
    for p in range(preferred + 1, preferred + 1 + max_tries):
        if _port_is_available(p):
            return p
    return preferred


def _terminate(name: str, proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    print(f"[STOP] {name}")
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


def _stream_output(name: str, color: str, proc: subprocess.Popen) -> None:
    prefix = f"{color}[{name}]{RESET} "
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            if not line:
                break
            print(prefix + line.rstrip("\n"))
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified OSINT Platform orchestrator")
    parser.add_argument("--lite", action="store_true", help="Run API + frontend without Celery worker")
    args = parser.parse_args()
    print("Unified OSINT Platform - Master Orchestrator")
    print("=" * 72)

    # Set project root as working directory for all subprocesses
    ROOT = os.path.dirname(os.path.abspath(__file__))
    os.chdir(ROOT)
    print(f"[INFO] Working directory: {ROOT}")
    print(f"[INFO] Platform: {os.name}")
    if args.lite:
        print("[INFO] Lite mode enabled: Celery worker disabled")

    # Commands
    py = _detect_python()
    api_port = _find_api_port(8000)
    if api_port != 8000:
        print(f"[WARN] Port 8000 unavailable; using {api_port} for FastAPI.")
    uvicorn_cmd = [py, "-m", "uvicorn", "backend.api:app", "--reload", "--port", str(api_port)]
    celery_cmd = [py, "-m", "celery", "-A", "backend.celery_app", "worker", "--loglevel=info"]
    if os.name == "nt":
        celery_cmd += ["--pool=solo", "--concurrency=1"]
        print(f"[INFO] Windows detected: Celery using --pool=solo")
        # On Windows, npm is a .cmd file and requires shell=True
        next_cmd = "npm run dev --prefix frontend"
    else:
        next_cmd = ["npm", "run", "dev", "--prefix", "frontend"]

    procs: Dict[str, subprocess.Popen] = {}
    threads: List[threading.Thread] = []

    try:
        procs["FASTAPI"] = _spawn("FASTAPI", uvicorn_cmd, cwd=ROOT)
        if not args.lite:
            procs["CELERY"] = _spawn("CELERY", celery_cmd, cwd=ROOT)
        # On Windows, next_cmd is a string and needs shell=True
        next_env = {"NEXT_PUBLIC_API_URL": f"http://127.0.0.1:{api_port}"}
        if os.name == "nt":
            procs["NEXTJS"] = _spawn("NEXTJS", next_cmd, cwd=ROOT, use_shell=True, env=next_env)  # type: ignore[arg-type]
        else:
            procs["NEXTJS"] = _spawn("NEXTJS", next_cmd, cwd=ROOT, env=next_env)  # type: ignore[arg-type]

        # Start log streaming threads
        t_fastapi = threading.Thread(
            target=_stream_output,
            args=("FASTAPI", FASTAPI_COLOR, procs["FASTAPI"]),
            daemon=True,
        )
        t_celery = None
        if "CELERY" in procs:
            t_celery = threading.Thread(
                target=_stream_output,
                args=("CELERY", CELERY_COLOR, procs["CELERY"]),
                daemon=True,
            )
        t_next = threading.Thread(
            target=_stream_output,
            args=("NEXTJS", NEXT_COLOR, procs["NEXTJS"]),
            daemon=True,
        )
        threads.extend([t_fastapi, t_next])
        if t_celery:
            threads.append(t_celery)
        for t in threads:
            t.start()

        stop = threading.Event()

        def handle_sigint(signum, frame):  # type: ignore[override]
            print("\n[CTRL+C] Stopping all services...")
            stop.set()

        signal.signal(signal.SIGINT, handle_sigint)

        # Wait until interrupted
        while not stop.is_set():
            time.sleep(0.5)
            # If any core process exits unexpectedly, stop everything
            if any(p.poll() not in (None, 0) for p in procs.values()):
                print("[WARN] One or more processes exited unexpectedly. Shutting down...")
                stop.set()

    finally:
        for name, proc in procs.items():
            _terminate(name, proc)
        for t in threads:
            t.join(timeout=2)

    print("All services stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

