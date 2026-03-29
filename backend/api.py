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

from backend.tasks import (
    task_shodan, task_censys, task_scrape, task_port_scan,
    task_dns_intel, task_whois_lookup, task_ssl_analyze,
    task_http_security, task_tech_stack, task_metadata_extract,
    task_graysentinel_ingest, task_cyberninja_passive, task_xrecon,
    task_social_hunter, task_cert_transparency, task_deep_scraper,
)
from backend.reporting_engine import (
    generate_executive_summary,
    generate_technical_report,
    generate_stix_bundle,
    generate_raw_data,
    generate_ioc_csv,
)


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


class DnsIntelRequest(BaseModel):
    domain: str
    brute_subdomains: bool = False
    wordlist: list[str] | None = None


class WhoisRequest(BaseModel):
    domain: str


class SslAnalyzeRequest(BaseModel):
    host: str
    port: int = 443
    timeout: int = 10


class HttpSecurityRequest(BaseModel):
    url: str
    timeout: int = 10


class TechStackRequest(BaseModel):
    url: str
    timeout: int = 10


class MetadataExtractRequest(BaseModel):
    file_path: str


class CyberNinjaRequest(BaseModel):
    usernames: list[str]
    timeout: float | None = None
    site_list: list[str] | None = None


class XReconRequest(BaseModel):
    query: str
    query_type: str = "username"


class SocialHunterRequest(BaseModel):
    username: str
    max_concurrent: int = 20


class CertTransparencyRequest(BaseModel):
    domain: str
    use_html_fallback: bool = True


class DeepScraperRequest(BaseModel):
    url: str
    max_depth: int = 2
    max_pages: int = 50
    max_concurrent: int = 10


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


@app.post("/api/dns-intel")
def api_dns_intel(req: DnsIntelRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "dns_intel", req.domain, "initiated")
    _publish_event("osint.investigation.started", {"action": "dns_intel", "target": req.domain})
    t = task_dns_intel.delay(req.domain, req.brute_subdomains, req.wordlist)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/whois")
def api_whois(req: WhoisRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "whois_lookup", req.domain, "initiated")
    _publish_event("osint.investigation.started", {"action": "whois_lookup", "target": req.domain})
    t = task_whois_lookup.delay(req.domain)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/ssl-analyze")
def api_ssl_analyze(req: SslAnalyzeRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "ssl_analyze", req.host, "initiated")
    _publish_event("osint.investigation.started", {"action": "ssl_analyze", "target": req.host})
    t = task_ssl_analyze.delay(req.host, req.port, req.timeout)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/http-security")
def api_http_security(req: HttpSecurityRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "http_security", req.url, "initiated")
    _publish_event("osint.investigation.started", {"action": "http_security", "target": req.url})
    t = task_http_security.delay(req.url, req.timeout)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/tech-stack")
def api_tech_stack(req: TechStackRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "tech_stack", req.url, "initiated")
    _publish_event("osint.investigation.started", {"action": "tech_stack", "target": req.url})
    t = task_tech_stack.delay(req.url, req.timeout)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/metadata-extract")
def api_metadata_extract(req: MetadataExtractRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "metadata_extract", req.file_path, "initiated")
    _publish_event("osint.investigation.started", {"action": "metadata_extract", "target": req.file_path})
    t = task_metadata_extract.delay(req.file_path)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/cyberninja")
def api_cyberninja(req: CyberNinjaRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "cyberninja_passive", ",".join(req.usernames[:3]), "initiated")
    _publish_event("osint.investigation.started", {"action": "cyberninja_passive", "target": ",".join(req.usernames[:3])})
    t = task_cyberninja_passive.delay(req.usernames, req.timeout, req.site_list)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/xrecon")
def api_xrecon(req: XReconRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "xrecon", req.query[:100], "initiated")
    _publish_event("osint.investigation.started", {"action": "xrecon", "target": req.query[:100]})
    t = task_xrecon.delay(req.query, req.query_type)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/social-hunter")
def api_social_hunter(req: SocialHunterRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """
    Hunt for a username across 50+ social media platforms.
    Keyless/passive - uses HTTP status code checks only.
    """
    _log_audit(x_tenant_id, "social_hunter", req.username, "initiated")
    _publish_event("osint.investigation.started", {"action": "social_hunter", "target": req.username})
    t = task_social_hunter.delay(req.username, req.max_concurrent)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/cert-transparency")
def api_cert_transparency(req: CertTransparencyRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """
    Discover subdomains via Certificate Transparency logs (crt.sh).
    Keyless/passive - scrapes public CT logs, no API key required.
    """
    _log_audit(x_tenant_id, "cert_transparency", req.domain, "initiated")
    _publish_event("osint.investigation.started", {"action": "cert_transparency", "target": req.domain})
    t = task_cert_transparency.delay(req.domain, req.use_html_fallback)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/deep-scraper")
def api_deep_scraper(req: DeepScraperRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """
    Deep recursive scraper extracting emails, phones, links, documents, and social profiles.
    """
    _log_audit(x_tenant_id, "deep_scraper", req.url[:200], "initiated")
    _publish_event("osint.investigation.started", {"action": "deep_scraper", "target": req.url[:200]})
    t = task_deep_scraper.delay(req.url, req.max_depth, req.max_pages, req.max_concurrent)
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
    t = task_graysentinel_ingest.delay(req.urls, req.strategies)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


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


class ReportRequest(BaseModel):
    format: str = "markdown"


@app.get("/api/reports")
def list_reports():
    """Available report types."""
    return {
        "reports": [
            {"id": "executive-summary", "name": "Executive Summary", "format": "markdown"},
            {"id": "technical-report", "name": "Technical Report", "format": "markdown"},
            {"id": "stix-bundle", "name": "STIX 2.1 Bundle", "format": "json"},
            {"id": "raw-data", "name": "Raw Data Export", "format": "json"},
            {"id": "ioc-list", "name": "IOC List", "format": "csv"},
        ]
    }


@app.get("/api/reports/{report_type}")
def get_report(report_type: str):
    """
    Generate a report of the given type and return it.
    Supported types: executive-summary, technical-report, stix-bundle, raw-data, ioc-list
    """
    if report_type == "executive-summary":
        content = generate_executive_summary()
        return {
            "success": True,
            "report_type": report_type,
            "format": "markdown",
            "content": content,
        }
    elif report_type == "technical-report":
        content = generate_technical_report()
        return {
            "success": True,
            "report_type": report_type,
            "format": "markdown",
            "content": content,
        }
    elif report_type == "stix-bundle":
        bundle = generate_stix_bundle()
        return {
            "success": True,
            "report_type": report_type,
            "format": "json",
            "content": bundle,
        }
    elif report_type == "raw-data":
        data = generate_raw_data()
        return {
            "success": True,
            "report_type": report_type,
            "format": "json",
            "content": data,
        }
    elif report_type == "ioc-list":
        csv_content = generate_ioc_csv()
        return {
            "success": True,
            "report_type": report_type,
            "format": "csv",
            "content": csv_content,
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown report type: {report_type}. "
                   f"Valid types: executive-summary, technical-report, stix-bundle, raw-data, ioc-list",
        )


class SettingsEnvRequest(BaseModel):
    key: str
    value: str


class SettingsEnvResponse(BaseModel):
    success: bool
    message: str


@app.post("/api/settings/env")
def update_env_var(req: SettingsEnvRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """
    Update a single environment variable in the running process.
    Note: In production, environment variables are read at startup.
    For persistent changes, update your .env file or vault configuration.
    This endpoint allows runtime adjustment for the current session.
    """
    import os
    _log_audit(x_tenant_id, "update_env_var", req.key, "initiated")
    # Apply to current process environment
    os.environ[req.key] = req.value
    return {"success": True, "message": f"{req.key} updated (session scope)"}


@app.get("/api/settings/env")
def get_env_vars(x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    """
    Return all relevant environment variables (non-sensitive subset).
    Sensitive keys (passwords, secrets) are redacted.
    """
    import os
    sensitive = {"NEO4J_PASSWORD", "RABBITMQ_URL", "VAULT_SHODAN_API_KEY", "VAULT_CENSYS_API_SECRET"}
    env_vars: Dict[str, str] = {}
    for key, val in os.environ.items():
        if any(key.startswith(p) for p in ["VAULT_", "CELERY_", "REDIS_", "NEO4J_", "WEAVIATE", "RABBITMQ", "NEXT_PUBLIC", "POSTGRES"]):
            if any(s in key.upper() for s in sensitive):
                env_vars[key] = "***REDACTED***"
            else:
                env_vars[key] = val
    return {"env_vars": env_vars}


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

