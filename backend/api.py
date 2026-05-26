"""
Unified Enterprise OSINT Platform - FastAPI Command Dispatcher & State Manager.
All OSINT work is dispatched to Celery; no direct execution in the main thread.
WebSocket streams real-time stdout/stderr from worker to frontend.
"""
from __future__ import annotations

import asyncio
import json
import os
import ipaddress
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from redis import Redis
from jose import jwt, JWTError
from passlib.context import CryptContext
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.tasks import (
    task_shodan, task_censys, task_scrape, task_port_scan,
    task_dns_intel, task_whois_lookup, task_ssl_analyze,
    task_http_security, task_tech_stack, task_metadata_extract,
    task_graysentinel_ingest, task_cyberninja_passive, task_xrecon,
    task_social_hunter, task_cert_transparency, task_deep_scraper,
    task_ip_geolocation, task_reverse_ip_lookup, task_bgp_asn_lookup,
    task_wayback_machine, task_email_header_analyzer, task_sherlock_hunt,
    task_robots_sitemap, task_favicon_hash, task_username_permutator,
    task_github_osint, task_phone_intel, task_email_reputation,
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
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-osint-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_MIN = int(os.getenv("JWT_TTL_MIN", "60"))
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "false").lower() in {"1", "true", "yes"}
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _create_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=JWT_TTL_MIN)).timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


def require_auth(authorization: Optional[str] = Header(None, alias="Authorization")) -> Optional[str]:
    if not AUTH_REQUIRED:
        return "dev-anonymous"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    payload = _decode_token(token)
    return payload.get("sub")


def _is_ssrf_blocked(value: str) -> bool:
    if not value:
        return True
    lowered = value.lower()
    if any(x in lowered for x in ("localhost", "127.0.0.1", "169.254.169.254")):
        return True
    host = lowered.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True
    except ValueError:
        pass
    return False


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


class TargetRequest(BaseModel):
    target: str


class WaybackRequest(BaseModel):
    target: str
    limit: int = 50


class EmailHeaderRequest(BaseModel):
    raw_headers: str


class SherlockRequest(BaseModel):
    username: str
    timeout: int = 10
    max_connections: int = 5


class RobotsSitemapRequest(BaseModel):
    domain: str
    max_sitemap_urls: int = 200


class FaviconHashRequest(BaseModel):
    domain: str


class UsernamePermutatorRequest(BaseModel):
    seed: str
    max_results: int = 50


class GithubOsintRequest(BaseModel):
    target: str
    lookup_type: str = "auto"
    api_token: str | None = None
    max_repos: int = 30


class PhoneIntelRequest(BaseModel):
    number: str
    default_region: str = "US"


class EmailReputationRequest(BaseModel):
    email: str


class IngestRequest(BaseModel):
    urls: list[str]
    strategies: list[str] | None = None


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 10


class AgentInvestigateRequest(BaseModel):
    goal: str
    thread_id: str | None = None


class AuthLoginRequest(BaseModel):
    username: str
    password: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
@limiter.limit("10/minute")
def auth_login(request: Request, req: AuthLoginRequest):
    admin_user = os.getenv("OSINT_ADMIN_USER", "admin")
    admin_hash = os.getenv("OSINT_ADMIN_PASSWORD_HASH")
    dev_password = os.getenv("OSINT_ADMIN_PASSWORD", "admin123")
    if req.username != admin_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if admin_hash:
        ok = pwd_context.verify(req.password, admin_hash)
    else:
        ok = req.password == dev_password
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": _create_token(req.username), "token_type": "bearer", "expires_in_minutes": JWT_TTL_MIN}


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
@limiter.limit("20/minute")
def api_deep_scraper(
    request: Request,
    req: DeepScraperRequest,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    _user: Optional[str] = Depends(require_auth),
):
    """
    Deep recursive scraper extracting emails, phones, links, documents, and social profiles.
    """
    if _is_ssrf_blocked(req.url):
        raise HTTPException(status_code=400, detail="Blocked target by SSRF policy")
    _log_audit(x_tenant_id, "deep_scraper", req.url[:200], "initiated")
    _publish_event("osint.investigation.started", {"action": "deep_scraper", "target": req.url[:200]})
    t = task_deep_scraper.delay(req.url, req.max_depth, req.max_pages, req.max_concurrent)
    return {
        "task_id": t.id,
        "status": "queued",
        "stream_url": f"/ws/task/{t.id}",
        "result_url": f"/api/tasks/{t.id}",
    }


@app.post("/api/ip-geolocation")
def api_ip_geolocation(req: TargetRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "ip_geolocation", req.target, "initiated")
    t = task_ip_geolocation.delay(req.target)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/reverse-ip")
def api_reverse_ip(req: TargetRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "reverse_ip_lookup", req.target, "initiated")
    t = task_reverse_ip_lookup.delay(req.target)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/bgp-asn")
def api_bgp_asn(req: TargetRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "bgp_asn_lookup", req.target, "initiated")
    t = task_bgp_asn_lookup.delay(req.target)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/wayback")
def api_wayback(req: WaybackRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "wayback_machine", req.target, "initiated")
    t = task_wayback_machine.delay(req.target, req.limit)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/email-header")
def api_email_header(req: EmailHeaderRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "email_header_analyzer", None, "initiated")
    t = task_email_header_analyzer.delay(req.raw_headers)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/robots-sitemap")
def api_robots_sitemap(req: RobotsSitemapRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    if _is_ssrf_blocked(req.domain):
        raise HTTPException(status_code=400, detail="Blocked target by SSRF policy")
    _log_audit(x_tenant_id, "robots_sitemap", req.domain, "initiated")
    _publish_event("osint.investigation.started", {"action": "robots_sitemap", "target": req.domain})
    t = task_robots_sitemap.delay(req.domain, req.max_sitemap_urls)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/favicon-hash")
def api_favicon_hash(req: FaviconHashRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    if _is_ssrf_blocked(req.domain):
        raise HTTPException(status_code=400, detail="Blocked target by SSRF policy")
    _log_audit(x_tenant_id, "favicon_hash", req.domain, "initiated")
    _publish_event("osint.investigation.started", {"action": "favicon_hash", "target": req.domain})
    t = task_favicon_hash.delay(req.domain)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/username-permutator")
def api_username_permutator(req: UsernamePermutatorRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "username_permutator", req.seed[:100], "initiated")
    _publish_event("osint.investigation.started", {"action": "username_permutator", "target": req.seed[:100]})
    t = task_username_permutator.delay(req.seed, req.max_results)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/github-osint")
def api_github_osint(req: GithubOsintRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "github_osint", req.target[:100], "initiated")
    _publish_event("osint.investigation.started", {"action": "github_osint", "target": req.target[:100]})
    t = task_github_osint.delay(req.target, req.lookup_type, req.api_token, req.max_repos)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/phone-intel")
def api_phone_intel(req: PhoneIntelRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "phone_intel", req.number[:50], "initiated")
    _publish_event("osint.investigation.started", {"action": "phone_intel", "target": req.number[:50]})
    t = task_phone_intel.delay(req.number, req.default_region)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/email-reputation")
def api_email_reputation(req: EmailReputationRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "email_reputation", req.email[:100], "initiated")
    _publish_event("osint.investigation.started", {"action": "email_reputation", "target": req.email[:100]})
    t = task_email_reputation.delay(req.email)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


@app.post("/api/sherlock")
def api_sherlock(req: SherlockRequest, x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")):
    _log_audit(x_tenant_id, "sherlock_hunt", req.username, "initiated")
    t = task_sherlock_hunt.delay(req.username, req.timeout, req.max_connections)
    return {"task_id": t.id, "status": "queued", "stream_url": f"/ws/task/{t.id}", "result_url": f"/api/tasks/{t.id}"}


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


class InvestigateRequest(BaseModel):
    """Smart search — fan out to all relevant modules for the detected input type."""
    target: str
    types: list[str]
    intensity: str = "standard"


class InvestigateResponse(BaseModel):
    playbook_id: str
    modules: list[str]
    module_labels: dict[str, str]
    task_ids: list[str]
    ws_url: str
    target: str
    types: list[str]


@app.post("/api/investigate", response_model=InvestigateResponse)
@limiter.limit("30/minute")
def api_investigate(
    request: Request,
    req: InvestigateRequest,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    _user: Optional[str] = Depends(require_auth),
):
    """
    POST /api/investigate
    Accepts a target + detected types, looks up the routing map,
    dispatches all relevant Celery tasks as a group, and returns a playbook_id.
    """
    import uuid

    from backend.playbook import get_modules_for_types, get_module_display_names
    from backend.celery_app import celery_app

    playbook_id = f"pb-{uuid.uuid4().hex[:12]}"

    if _is_ssrf_blocked(req.target):
        raise HTTPException(status_code=400, detail="Blocked target by SSRF policy")

    # Resolve task names for the detected types
    modules = get_modules_for_types(req.types, req.intensity)
    display_names = get_module_display_names(modules)
    MODULE_LABELS = {task_name: label for task_name, label in zip(modules, display_names)}

    _log_audit(x_tenant_id, "playbook_investigate", req.target, "initiated")
    _publish_event("osint.investigation.started", {
        "action": "playbook_investigate",
        "target": req.target,
        "playbook_id": playbook_id,
        "modules": display_names,
    })

    if not modules:
        raise HTTPException(status_code=422, detail=f"No modules available for types: {req.types}")

    # Build a Redis pub/sub channel for this playbook
    playbook_chan = f"osint:playbook:{playbook_id}"
    task_ids: list[str] = []

    try:
        # Import task signatures
        from backend.tasks import (
            task_dns_intel, task_whois_lookup, task_ssl_analyze,
            task_http_security, task_tech_stack, task_cert_transparency,
            task_port_scan, task_social_hunter, task_deep_scraper,
            task_cyberninja_passive, task_xrecon, task_shodan, task_censys,
            task_graysentinel_ingest,
            task_ip_geolocation, task_reverse_ip_lookup, task_bgp_asn_lookup,
            task_wayback_machine, task_email_header_analyzer, task_sherlock_hunt,
            task_robots_sitemap, task_favicon_hash, task_username_permutator,
            task_github_osint, task_phone_intel, task_email_reputation,
        )

        TASK_MAP: dict[str, callable] = {
            "tasks.dns_intel": task_dns_intel,
            "tasks.whois_lookup": task_whois_lookup,
            "tasks.ssl_analyze": task_ssl_analyze,
            "tasks.http_security": task_http_security,
            "tasks.tech_stack": task_tech_stack,
            "tasks.cert_transparency": task_cert_transparency,
            "tasks.port_scan": task_port_scan,
            "tasks.social_hunter": task_social_hunter,
            "tasks.deep_scraper": task_deep_scraper,
            "tasks.cyberninja_passive": task_cyberninja_passive,
            "tasks.xrecon": task_xrecon,
            "tasks.shodan_recon": task_shodan,
            "tasks.censys_recon": task_censys,
            "tasks.graysentinel_ingest": task_graysentinel_ingest,
            "tasks.ip_geolocation": task_ip_geolocation,
            "tasks.reverse_ip_lookup": task_reverse_ip_lookup,
            "tasks.bgp_asn_lookup": task_bgp_asn_lookup,
            "tasks.wayback_machine": task_wayback_machine,
            "tasks.email_header_analyzer": task_email_header_analyzer,
            "tasks.sherlock_hunt": task_sherlock_hunt,
            "tasks.robots_sitemap": task_robots_sitemap,
            "tasks.favicon_hash": task_favicon_hash,
            "tasks.username_permutator": task_username_permutator,
            "tasks.github_osint": task_github_osint,
            "tasks.phone_intel": task_phone_intel,
            "tasks.email_reputation": task_email_reputation,
        }

        def _domain_from_target(target: str) -> str:
            t = target.strip()
            if t.startswith("http://") or t.startswith("https://"):
                from urllib.parse import urlparse
                return urlparse(t).netloc or t
            return t.split("/")[0]

        # Build arguments per task based on its signature
        def build_args(task_name: str, target: str) -> tuple:
            if task_name == "tasks.dns_intel":
                return (target, False, None)
            elif task_name == "tasks.whois_lookup":
                return (target,)
            elif task_name == "tasks.ssl_analyze":
                return (target, 443, 10)
            elif task_name == "tasks.http_security":
                url = target if target.startswith("http") else f"https://{target}"
                return (url, 10)
            elif task_name == "tasks.tech_stack":
                url = target if target.startswith("http") else f"https://{target}"
                return (url, 10)
            elif task_name == "tasks.cert_transparency":
                return (target, True)
            elif task_name == "tasks.port_scan":
                return (target, None, 20, 2.0)
            elif task_name == "tasks.social_hunter":
                return (target, 20)
            elif task_name == "tasks.deep_scraper":
                url = target if target.startswith("http") else f"https://{target}"
                return (url, 2, 50, 10)
            elif task_name == "tasks.cyberninja_passive":
                return ([target], None, None)
            elif task_name == "tasks.xrecon":
                return (target, "auto")
            elif task_name == "tasks.shodan_recon":
                return (target, None)
            elif task_name == "tasks.censys_recon":
                return (target, None, None)
            elif task_name == "tasks.graysentinel_ingest":
                url = target if target.startswith("http") else f"https://{target}"
                return ([url], None)
            elif task_name in ("tasks.ip_geolocation", "tasks.reverse_ip_lookup", "tasks.bgp_asn_lookup"):
                return (target,)
            elif task_name == "tasks.wayback_machine":
                return (target, 50)
            elif task_name == "tasks.email_header_analyzer":
                return (target,)
            elif task_name == "tasks.sherlock_hunt":
                return (target, 10, 5)
            elif task_name == "tasks.robots_sitemap":
                return (_domain_from_target(target), 200)
            elif task_name == "tasks.favicon_hash":
                return (_domain_from_target(target),)
            elif task_name == "tasks.username_permutator":
                seed = target.split("@", 1)[0] if "@" in target else target
                return (seed, 50)
            elif task_name == "tasks.github_osint":
                return (target.lstrip("@"), "auto", None, 30)
            elif task_name == "tasks.phone_intel":
                return (target, "US")
            elif task_name == "tasks.email_reputation":
                return (target,)
            else:
                return (target,)

        # Dispatch all tasks with playbook_id in kwargs for WS correlation
        for task_name in modules:
            task_sig = TASK_MAP.get(task_name)
            if not task_sig:
                continue
            args = build_args(task_name, req.target)
            result = task_sig.delay(*args, playbook_id=playbook_id, playbook_chan=playbook_chan)
            task_ids.append(result.id)

        # Store playbook plan in Redis (for WS to read initial state)
        redis = _redis()
        redis.hset(
            f"osint:playbook:{playbook_id}:plan",
            mapping={
                module_task: json.dumps(
                    {
                        "task_id": tid,
                        "status": "queued",
                        "module": module_task,
                        "label": MODULE_LABELS.get(module_task, module_task),
                    }
                )
                for module_task, tid in zip(modules, task_ids)
            },
        )
        redis.expire(f"osint:playbook:{playbook_id}:plan", 3600)

        module_labels = {m: MODULE_LABELS.get(m, m) for m in modules}
        return {
            "playbook_id": playbook_id,
            "modules": modules,
            "module_labels": module_labels,
            "task_ids": task_ids,
            "ws_url": f"/ws/playbook/{playbook_id}",
            "target": req.target,
            "types": req.types,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
def get_graph(limit: int = 50):
    """Fetch STIX graph from Neo4j in Cytoscape format."""
    try:
        from backend.neo4j_client import Neo4jClient

        client = Neo4jClient()
        data = client.get_graph_cytoscape(limit=limit)
        client.close()
        return data
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/playbook/{playbook_id}/plan")
def get_playbook_plan(playbook_id: str):
    """
    Fetch the module execution plan for a playbook from Redis.
    Returns a dict of module_name -> {task_id, status, module}.
    """
    redis = _redis()
    raw = redis.hgetall(f"osint:playbook:{playbook_id}:plan")
    if not raw:
        return {}
    return {k.decode("utf-8"): json.loads(v.decode("utf-8")) for k, v in raw.items()}


@app.get("/api/tasks/{task_id}")
def get_task_result(task_id: str):
    """
    Poll Celery task status. If the task is complete, waits for the result
    and returns it inline so the caller gets the full payload without a
    second round-trip.
    """
    from backend.celery_app import celery_app
    import time

    r = celery_app.AsyncResult(task_id)
    if r.ready():
        # Task is done — return status + the actual result dict
        return {
            "task_id": task_id,
            "status": str(r.status),
            "result": r.result if r.result is not None else {},
        }

    # Not ready yet — return current status without blocking
    return {"task_id": task_id, "status": str(r.status), "result": None}


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
        idle_ticks = 0
        while True:
            msg = await loop.run_in_executor(
                None,
                lambda: pubsub.get_message(ignore_subscribe_messages=True, timeout=1),
            )
            if msg is None:
                idle_ticks += 1
                if idle_ticks >= 30:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    idle_ticks = 0
                await asyncio.sleep(0.05)
                continue
            idle_ticks = 0
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
        await websocket.send_text(json.dumps({"type": "done", "error": True, "reason": "stream_timeout"}))
    finally:
        pubsub.unsubscribe(chan)
        pubsub.close()
        try:
            await websocket.close()
        except Exception:
            pass
@app.websocket("/ws/playbook/{playbook_id}")
async def websocket_playbook_stream(websocket: WebSocket, playbook_id: str):
    """
    WebSocket for a full playbook — fans out results from all tasks in the group.

    Redis pub/sub channel: osint:playbook:{playbook_id}
    Each task in the group publishes to this channel with:
      {"type": "result", "module": "...", "data": {...}}
      {"type": "done",  "module": "...", "status": "success|failure", "error": "..."}
    """
    await websocket.accept()
    redis = _redis()
    pubsub = redis.pubsub()
    chan = f"osint:playbook:{playbook_id}"
    pubsub.subscribe(chan)

    loop = asyncio.get_event_loop()
    done_modules: set[str] = set()

    async def send_to_client():
        idle_ticks = 0
        while True:
            msg = await loop.run_in_executor(
                None,
                lambda: pubsub.get_message(ignore_subscribe_messages=True, timeout=1),
            )
            if msg is None:
                idle_ticks += 1
                if idle_ticks >= 30:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    idle_ticks = 0
                await asyncio.sleep(0.05)
                continue
            idle_ticks = 0
            if msg["type"] == "message":
                try:
                    payload = msg["data"].decode("utf-8")
                    obj = json.loads(payload)
                    module = obj.get("module", "")
                    await websocket.send_text(payload)
                    if obj.get("type") == "done":
                        done_modules.add(module)
                except (json.JSONDecodeError, WebSocketDisconnect):
                    break

    try:
        await asyncio.wait_for(send_to_client(), timeout=3600)
    except asyncio.TimeoutError:
        await websocket.send_text(json.dumps({"type": "done", "error": True, "reason": "stream_timeout"}))
    finally:
        pubsub.unsubscribe(chan)
        pubsub.close()
        try:
            await websocket.close()
        except Exception:
            pass

