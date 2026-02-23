"""
Celery tasks for OSINT modules. Invoked via task.delay(...) from FastAPI.
"""
from celery_app import celery_app
from modules.shodan_recon import shodan_search
from modules.censys_recon import censys_search
from modules.scraper import scrape_urls
from modules.port_scanner import scan_ports


@celery_app.task(bind=True, name="tasks.shodan_recon")
def task_shodan(self, target: str, api_key: str | None = None):
    return shodan_search(target, api_key)


@celery_app.task(bind=True, name="tasks.censys_recon")
def task_censys(self, target: str, api_id: str | None = None, api_secret: str | None = None):
    return censys_search(target, api_id, api_secret)


@celery_app.task(bind=True, name="tasks.scrape_urls")
def task_scrape(self, urls: list[str], max_workers: int = 5):
    return scrape_urls(urls, max_workers)


@celery_app.task(bind=True, name="tasks.port_scan")
def task_port_scan(
    self, host: str, ports: list[int] | None = None, max_workers: int = 20, timeout: float = 2.0
):
    return scan_ports(host, ports, max_workers, timeout)
