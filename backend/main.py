"""
Unified Enterprise OSINT Platform - FastAPI Command Dispatcher & State Manager.
All OSINT work is dispatched to Celery; no direct execution in the main thread.
WebSocket streams real-time stdout/stderr from worker to frontend.
"""
import asyncio
import json
import os

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from redis import Redis

from tasks import task_shodan, task_censys, task_scrape, task_port_scan

app = FastAPI(title="Unified Enterprise OSINT Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _redis() -> Redis:
    url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(url)


class ShodanRequest(BaseModel):
    target: str
    api_key: str | None = None


class CensysRequest(BaseModel):
    target: str
    api_id: str | None = None
    api_secret: str | None = None


class ScraperRequest(BaseModel):
    urls: list[str]
    max_workers: int = 5


class PortScannerRequest(BaseModel):
    host: str
    ports: list[int] | None = None
    max_workers: int = 20
    timeout: float = 2.0


class IngestRequest(BaseModel):
    urls: list[str]
    strategies: list[str] | None = None


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/shodan")
def api_shodan(req: ShodanRequest):
    t = task_shodan.delay(req.target, req.api_key)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/censys")
def api_censys(req: CensysRequest):
    t = task_censys.delay(req.target, req.api_id, req.api_secret)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/scrape")
def api_scrape(req: ScraperRequest):
    t = task_scrape.delay(req.urls, req.max_workers)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/port-scan")
def api_port_scan(req: PortScannerRequest):
    t = task_port_scan.delay(req.host, req.ports, req.max_workers, req.timeout)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/ingest")
def api_ingest(req: IngestRequest):
    """Ingest URLs via GraySentinel pipeline (scrape, chunk, NER, embed, Weaviate)."""
    from modules.graysentinel_pipeline import run_pipeline
    return run_pipeline(req.urls, req.strategies)


@app.post("/api/semantic-search")
def api_semantic_search(req: SemanticSearchRequest):
    """Natural language query -> cosine similarity search -> contextual documents."""
    try:
        from semantic_search import search
        results = search(req.query, limit=req.limit)
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/graph")
def get_graph():
    """Fetch STIX graph from Neo4j in Cytoscape format."""
    try:
        from neo4j_client import Neo4jClient
        client = Neo4jClient()
        data = client.get_graph_cytoscape()
        client.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/tasks/{task_id}")
def get_task_result(task_id: str):
    from celery_app import celery_app
    r = celery_app.AsyncResult(task_id)
    if r.ready():
        return {"task_id": task_id, "status": r.status, "result": r.result}
    return {"task_id": task_id, "status": r.status}


REDIS_CHAN_PREFIX = "osint:task:stream:"


@app.websocket("/ws/task/{task_id}")
async def websocket_task_stream(websocket: WebSocket, task_id: str):
    await websocket.accept()
    redis = _redis()
    pubsub = redis.pubsub()
    chan = f"{REDIS_CHAN_PREFIX}{task_id}"
    pubsub.subscribe(chan)

    loop = asyncio.get_event_loop()

    async def send_to_client():
        while True:
            msg = await loop.run_in_executor(
                None,
                lambda: pubsub.get_message(ignore_subscribe_messages=True, timeout=1),
            )
            if msg is None:
                await asyncio.sleep(0.05)
                continue
            if msg["type"] == "message":
                try:
                    payload = msg["data"].decode("utf-8")
                    await websocket.send_text(payload)
                    obj = json.loads(payload)
                    if obj.get("type") == "done":
                        break
                except (json.JSONDecodeError, WebSocketDisconnect):
                    break

    try:
        await asyncio.wait_for(send_to_client(), timeout=3600)
    except asyncio.TimeoutError:
        pass
    finally:
        pubsub.unsubscribe(chan)
        pubsub.close()
        try:
            await websocket.close()
        except Exception:
            pass
