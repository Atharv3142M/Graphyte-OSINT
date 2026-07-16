"""Playbook management routes."""
from typing import Optional, List

from fastapi import APIRouter, HTTPException

from backend.logging_config import logger
from backend.schemas import PlaybookRequest

router = APIRouter()


# Default playbooks
PLAYBOOKS = {
    "light": {
        "name": "Light Reconnaissance",
        "description": "Fast reconnaissance with minimal impact",
        "modules": [
            "tasks.dns_intel",
            "tasks.whois_lookup",
            "tasks.ip_geolocation",
        ],
        "intensity": "light",
    },
    "standard": {
        "name": "Standard Investigation",
        "description": "Comprehensive OSINT investigation",
        "modules": [
            "tasks.dns_intel",
            "tasks.whois_lookup",
            "tasks.ssl_analyze",
            "tasks.http_security",
            "tasks.tech_stack",
            "tasks.cert_transparency",
            "tasks.ip_geolocation",
            "tasks.reverse_ip_lookup",
        ],
        "intensity": "normal",
    },
    "aggressive": {
        "name": "Aggressive Reconnaissance",
        "description": "Deep reconnaissance with all modules",
        "modules": [
            "tasks.dns_intel",
            "tasks.whois_lookup",
            "tasks.ssl_analyze",
            "tasks.http_security",
            "tasks.tech_stack",
            "tasks.cert_transparency",
            "tasks.deep_scraper",
            "tasks.social_hunter",
            "tasks.github_osint",
            "tasks.email_reputation",
        ],
        "intensity": "aggressive",
    },
}


@router.get("")
async def list_playbooks():
    """List available playbooks."""
    return {
        "playbooks": list(PLAYBOOKS.values()),
        "total": len(PLAYBOOKS),
    }


@router.get("/{playbook_name}")
async def get_playbook(playbook_name: str):
    """Get playbook details."""
    playbook_name = playbook_name.lower()
    
    if playbook_name not in PLAYBOOKS:
        raise HTTPException(
            status_code=404,
            detail=f"Playbook not found: {playbook_name}",
        )
    
    return PLAYBOOKS[playbook_name]


@router.post("/validate")
async def validate_playbook(request: PlaybookRequest):
    """Validate a playbook request."""
    playbook_name = request.playbook_name.lower()
    
    if playbook_name not in PLAYBOOKS:
        return {
            "valid": False,
            "error": f"Playbook not found: {playbook_name}",
        }
    
    playbook = PLAYBOOKS[playbook_name]
    
    # Check if all requested modules exist
    modules_to_check = request.custom_modules or playbook.get("modules", [])
    invalid_modules = [m for m in modules_to_check if not _module_exists(m)]
    
    if invalid_modules:
        return {
            "valid": False,
            "error": f"Invalid modules: {invalid_modules}",
        }
    
    return {
        "valid": True,
        "modules": modules_to_check,
        "target_type": _detect_target_type(request.target),
    }


@router.post("/dispatch")
async def dispatch_playbook(request: PlaybookRequest):
    """Dispatch a playbook for execution."""
    validation = await validate_playbook(request)
    
    if not validation.get("valid"):
        raise HTTPException(
            status_code=400,
            detail=validation.get("error", "Invalid playbook"),
        )
    
    logger.info(f"Dispatching playbook {request.playbook_name} for target: {request.target}")
    
    # TODO: Implement actual playbook dispatch to Celery
    return {
        "status": "dispatched",
        "playbook_name": request.playbook_name,
        "target": request.target,
        "modules": validation.get("modules", []),
    }


def _detect_target_type(target: str) -> str:
    """Detect the type of target."""
    target = target.lower().strip()
    
    if target.startswith("http://") or target.startswith("https://"):
        return "url"
    
    if "@" in target and "." in target:
        return "email"
    
    if target.count(".") >= 2 or (target.count(".") == 1 and not target.replace(".", "").isdigit()):
        return "domain"
    
    if target.replace(".", "").isdigit() and len(target.split(".")) == 4:
        return "ip"
    
    return "unknown"


def _module_exists(module_name: str) -> bool:
    """Check if a module exists."""
    valid_modules = {
        "tasks.dns_intel",
        "tasks.whois_lookup",
        "tasks.ssl_analyze",
        "tasks.http_security",
        "tasks.tech_stack",
        "tasks.cert_transparency",
        "tasks.deep_scraper",
        "tasks.social_hunter",
        "tasks.github_osint",
        "tasks.email_reputation",
        "tasks.ip_geolocation",
        "tasks.reverse_ip_lookup",
        "tasks.port_scan",
        "tasks.metadata_extract",
        "tasks.shodan",
        "tasks.censys",
        "tasks.scrapy",
        "tasks.email_header",
        "tasks.robots_sitemap",
        "tasks.favicon_hash",
        "tasks.username_permutator",
        "tasks.wayback_machine",
        "tasks.phone_intel",
        "tasks.cyberninja",
        "tasks.xrecon",
    }
    return module_name in valid_modules
