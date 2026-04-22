from __future__ import annotations

import asyncio
import json
import os

import websockets


async def main() -> None:
    playbook_id = os.getenv("PLAYBOOK_ID", "")
    if not playbook_id:
        raise SystemExit("PLAYBOOK_ID env var required")

    uri = f"ws://localhost:8000/ws/playbook/{playbook_id}"
    done: set[str] = set()
    async with websockets.connect(uri) as ws:
        for _ in range(500):
            msg = await asyncio.wait_for(ws.recv(), timeout=30)
            obj = json.loads(msg)
            if obj.get("type") == "done" and obj.get("module"):
                done.add(obj["module"])
                if len(done) >= 3:
                    break
    print("done_modules", sorted(done))


if __name__ == "__main__":
    asyncio.run(main())

