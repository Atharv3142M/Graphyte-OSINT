#!/usr/bin/env python3
"""
E2E investigation simulator for Unified OSINT Platform.
Simulates frontend: POST to task endpoint, then WebSocket stream.
Uses /api/shodan (returns task_id) for WebSocket streaming demo.
Run from backend/: python scripts/simulate_investigation.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
WS_BASE = API_BASE.replace("http://", "ws://").replace("https://", "wss://")
TENANT_ID = os.getenv("X_TENANT_ID", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
TIMEOUT = 30


async def run_agent_investigation():
    """POST to /api/agent/investigate (sync, no WebSocket)."""
    try:
        import httpx
    except ImportError:
        print("[ERROR] httpx not installed. pip install httpx")
        return False
    print("Phase 1: Agent investigation (sync)")
    print(f"  POST {API_BASE}/api/agent/investigate")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{API_BASE}/api/agent/investigate",
                json={"goal": "Find exposed subdomains for test.com", "thread_id": "test-run-01"},
                headers={"X-Tenant-ID": TENANT_ID},
            )
            r.raise_for_status()
            data = r.json()
            print(f"  Response: success={data.get('success')}, thread_id={data.get('thread_id')}")
            if data.get("threat_score") is not None:
                print(f"  Threat score: {data.get('threat_score')}")
            return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


async def run_task_with_websocket_stream():
    """POST to /api/shodan (returns task_id), then stream via WebSocket."""
    try:
        import httpx
        import websockets
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}. pip install httpx websockets")
        return False

    print("\nPhase 2: Task + WebSocket stream (Shodan recon)")
    print(f"  POST {API_BASE}/api/shodan")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(
                f"{API_BASE}/api/shodan",
                json={"target": "test.com"},
                headers={"X-Tenant-ID": TENANT_ID},
            )
            r.raise_for_status()
            data = r.json()
            task_id = data.get("task_id")
            if not task_id:
                print(f"  [ERROR] No task_id in response: {data}")
                return False
            print(f"  task_id: {task_id}")
    except Exception as e:
        print(f"  [ERROR] POST failed: {e}")
        return False

    ws_url = f"{WS_BASE}/ws/task/{task_id}"
    print(f"  Connecting to WebSocket: {ws_url}")
    try:
        async with websockets.connect(ws_url, close_timeout=5) as ws:
            print("  --- Live stream (stdout/stderr) ---")
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=60)
                    obj = json.loads(msg)
                    if obj.get("type") == "done":
                        print("  --- Stream complete ---")
                        break
                    if obj.get("type") == "result" and obj.get("data"):
                        print(f"  [Result] {json.dumps(obj['data'], indent=2)[:500]}...")
                        continue
                    if obj.get("stream") and obj.get("data"):
                        prefix = "\x1b[31m" if obj["stream"] == "stderr" else ""
                        suffix = "\x1b[0m" if obj["stream"] == "stderr" else ""
                        print(f"  {prefix}[{obj['stream']}] {obj['data']}{suffix}")
                except asyncio.TimeoutError:
                    print("  [Timeout] No message for 60s")
                    break
        return True
    except Exception as e:
        print(f"  [ERROR] WebSocket failed: {e}")
        return False


async def main():
    print("Unified OSINT Platform - E2E Investigation Simulator")
    print("=" * 60)
    ok1 = await run_agent_investigation()
    ok2 = await run_task_with_websocket_stream()
    print("=" * 60)
    if ok1 and ok2:
        print("E2E simulation complete.")
    else:
        print("Some phases failed. Ensure FastAPI and Celery are running.")
    return 0 if (ok1 and ok2) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
