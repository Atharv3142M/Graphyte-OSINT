"""
Unified Enterprise OSINT Platform - FastAPI Backend
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from modules.shodan_recon import shodan_search
from modules.censys_recon import censys_search
from modules.scraper import scrape_urls
from modules.port_scanner import scan_ports

USE_CELERY = os.getenv("USE_CELERY", "false").lower() == "true"
if USE_CELERY:
    from tasks import task_shodan, task_censys, task_scrape, task_port_scan

app = FastAPI(title="Unified Enterprise OSINT Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/shodan")
def api_shodan(req: ShodanRequest):
    if USE_CELERY:
        t = task_shodan.delay(req.target, req.api_key)
        return {"task_id": t.id, "status": "queued", "result_url": f"/api/tasks/{t.id}"}
    result = shodan_search(req.target, req.api_key)
    if result.get("error") and not result.get("success"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/censys")
def api_censys(req: CensysRequest):
    if USE_CELERY:
        t = task_censys.delay(req.target, req.api_id, req.api_secret)
        return {"task_id": t.id, "status": "queued", "result_url": f"/api/tasks/{t.id}"}
    result = censys_search(req.target, req.api_id, req.api_secret)
    if result.get("error") and not result.get("success"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/scrape")
def api_scrape(req: ScraperRequest):
    if USE_CELERY:
        t = task_scrape.delay(req.urls, req.max_workers)
        return {"task_id": t.id, "status": "queued", "result_url": f"/api/tasks/{t.id}"}
    return scrape_urls(req.urls, req.max_workers)


@app.post("/api/port-scan")
def api_port_scan(req: PortScannerRequest):
    if USE_CELERY:
        t = task_port_scan.delay(req.host, req.ports, req.max_workers, req.timeout)
        return {"task_id": t.id, "status": "queued", "result_url": f"/api/tasks/{t.id}"}
    return scan_ports(req.host, req.ports, req.max_workers, req.timeout)


@app.get("/api/tasks/{task_id}")
def get_task_result(task_id: str):
    if not USE_CELERY:
        raise HTTPException(status_code=400, detail="Celery not enabled")
    from celery_app import celery_app
    r = celery_app.AsyncResult(task_id)
    if r.ready():
        return {"task_id": task_id, "status": r.status, "result": r.result}
    return {"task_id": task_id, "status": r.status}
