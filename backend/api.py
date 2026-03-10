"""
Unified Enterprise OSINT Platform - FastAPI Command Dispatcher & State Manager.
All OSINT work is dispatched to Celery; no direct execution in the main thread.
WebSocket streams real-time stdout/stderr from worker to frontend.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from redis import Redis

from backend.tasks import task_shodan, task_censys, task_scrape, task_port_scan


def _log_audit(tenant_id: Optional[str], action: str, target: Optional[str] = None, status: str = "initiated") -> None:
    try:
        from postgres_client import log_audit_event
        log_audit_event(tenant_id, action, target, status)
    except Exception:
        pass


app = FastAPI(title="Unified Enterprise OSINT Platform API", version="0.1.0")


_consumer_task = None


async def _rabbitmq_audit_consumer():
    """Background task: consume osint.* events and log to PostgreSQL audit_events."""
    try:
        import aio_pika
        from rabbitmq_client import RABBITMQ_URL, EXCHANGE_NAME
    except ImportError:
        return
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=10)
                exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True)
                queue = await channel.declare_queue("", exclusive=True, durable=False)
                await queue.bind(exchange, routing_key="osint.#")
                async with queue.iterator() as it:
                    async for message in it:
                        async with message.process():
                            try:
                                body = json.loads(message.body.decode())
                                routing_key = message.routing_key or ""
                                action = body.get("action") or routing_key.replace(".", "_")
                                target = str(body.get("target") or body.get("goal") or body.get("thread_id") or "")[:512]
                                tenant_id = body.get("tenant_id")
                                loop = asyncio.get_event_loop()
                                await loop.run_in_executor(
                                    None,
                                    lambda t=tenant_id, a=action, tg=target: _log_audit(t, a, tg, "event_received"),
                                )
                            except Exception:
                                pass
        except asyncio.CancelledError:
            break
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning("RabbitMQ consumer error: %s", e)
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup():
    global _consumer_task
    try:
        from postgres_client import ensure_schema

        ensure_schema()
    except Exception:
        pass
    try:
        _consumer_task = asyncio.create_task(_rabbitmq_audit_consumer())
    except Exception:
        pass


@app.on_event("shutdown")
def shutdown():
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()


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


class AgentInvestigateRequest(BaseModel):
    goal: str
    thread_id: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


def _publish_event(routing_key: str, payload: dict) -> None:
    try:
        from rabbitmq_client import publish_enterprise_event_sync

        publish_enterprise_event_sync(routing_key, payload)
    except Exception:
        pass


@app.post("/api/shodan")
def api_shodan(req: ShodanRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "shodan_recon", req.target, "initiated")
    _publish_event("osint.investigation.started", {"action": "shodan_recon", "target": req.target})
    t = task_shodan.delay(req.target, req.api_key)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/censys")
def api_censys(req: CensysRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "censys_recon", req.target, "initiated")
    _publish_event("osint.investigation.started", {"action": "censys_recon", "target": req.target})
    t = task_censys.delay(req.target, req.api_id, req.api_secret)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/scrape")
def api_scrape(req: ScraperRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "scrape", ",".join(req.urls[:3]) if req.urls else None, "initiated")
    _publish_event(
        "osint.investigation.started",
        {"action": "scrape", "target": ",".join(req.urls[:3]) if req.urls else ""},
    )
    t = task_scrape.delay(req.urls, req.max_workers)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/port-scan")
def api_port_scan(req: PortScannerRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "port_scan", req.host, "initiated")
    _publish_event("osint.investigation.started", {"action": "port_scan", "target": req.host})
    t = task_port_scan.delay(req.host, req.ports, req.max_workers, req.timeout)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/ingest")
def api_ingest(req: IngestRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """Ingest URLs via GraySentinel pipeline (scrape, chunk, NER, embed, Weaviate)."""
    _log_audit(x_tenant_id, "graysentinel_ingest", ",".join(req.urls[:3]) if req.urls else None, "initiated")
    _publish_event(
        "osint.investigation.started",
        {"action": "graysentinel_ingest", "target": ",".join(req.urls[:3]) if req.urls else ""},
    )
    from backend.modules.graysentinel_pipeline import run_pipeline

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


@app.post("/api/agent/investigate")
def api_agent_investigate(req: AgentInvestigateRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """
    Run goal-directed multi-agent investigation (LangGraph).
    Orchestrator -> Searcher | Analyzer | Pentester with checkpoint memory.
    Pass thread_id to resume or continue a prior investigation chain.
    """
    _log_audit(x_tenant_id, "agent_investigate", req.goal[:200] if req.goal else None, "initiated")
    _publish_event(
        "osint.investigation.started",
        {"action": "agent_investigate", "goal": req.goal[:200] if req.goal else ""},
    )
    try:
        from backend.agents.graph import build_osint_graph

        graph = build_osint_graph(use_memory=True)
        thread_id = req.thread_id or f"inv-{os.urandom(8).hex()}"
        config = {"configurable": {"thread_id": thread_id}}
        initial: dict = {"goal": req.goal, "investigation_context": [], "messages": []}
        result = graph.invoke(initial, config=config)
        threat = result.get("threat_score") or 0
        _publish_event("osint.investigation.completed", {"thread_id": thread_id, "threat_score": threat})
        if threat >= 0.8:
            _publish_event("osint.threat.critical", {"thread_id": thread_id, "threat_score": threat})
        if result.get("stix_bundle"):
            _publish_event("osint.stix.published", {"thread_id": thread_id})
        return {
            "success": True,
            "thread_id": thread_id,
            "summary": result.get("orchestrator_summary"),
            "threat_score": result.get("threat_score"),
            "stix_bundle": result.get("stix_bundle"),
            "investigation_context": result.get("investigation_context", []),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/graph")
def get_graph():
    """Fetch STIX graph from Neo4j in Cytoscape format."""
    try:
        from backend.neo4j_client import Neo4jClient

        client = Neo4jClient()
        data = client.get_graph_cytoscape()
        client.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/tasks/{task_id}")
def get_task_result(task_id: str):
    from backend.celery_app import celery_app

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

