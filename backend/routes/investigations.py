"""Investigation management routes."""
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Header

from backend.logging_config import logger
from backend.schemas import Investigation, InvestigationStatus, Task, ModuleStatus
from backend.services import ServiceRegistry

router = APIRouter()


class StartInvestigationRequest:
    """Request to start investigation."""
    target: str
    playbook_name: Optional[str] = None
    intensity: str = "normal"
    custom_modules: Optional[List[str]] = None


# In-memory store (TODO: move to Redis/PostgreSQL)
_investigations: dict[str, Investigation] = {}


def get_investigation_or_404(investigation_id: str) -> Investigation:
    """Get investigation or raise 404."""
    if investigation_id not in _investigations:
        raise HTTPException(status_code=404, detail=f"Investigation not found: {investigation_id}")
    return _investigations[investigation_id]


@router.post("")
async def start_investigation(
    target: str,
    playbook_name: Optional[str] = None,
    intensity: str = "normal",
    custom_modules: Optional[List[str]] = None,
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
):
    """Start a new OSINT investigation."""
    investigation_id = str(uuid.uuid4())
    
    try:
        investigation = Investigation(
            id=investigation_id,
            target=target,
            target_type=_detect_target_type(target),
            status=InvestigationStatus.PENDING,
            tenant_id=tenant_id,
        )
        
        _investigations[investigation_id] = investigation
        logger.info(f"Created investigation {investigation_id} for target: {target}")
        
        return investigation
    except Exception as e:
        logger.error(f"Failed to create investigation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{investigation_id}")
async def get_investigation(investigation_id: str):
    """Get investigation status and results."""
    investigation = get_investigation_or_404(investigation_id)
    return investigation


@router.get("/{investigation_id}/results")
async def get_investigation_results(investigation_id: str):
    """Get investigation results."""
    investigation = get_investigation_or_404(investigation_id)
    
    # Extract artifacts from all completed tasks
    artifacts = []
    for task in investigation.tasks:
        if task.result and task.result.artifacts:
            artifacts.extend(task.result.artifacts)
    
    return {
        "investigation_id": investigation_id,
        "status": investigation.status,
        "artifacts": artifacts,
        "total_tasks": len(investigation.tasks),
        "completed_tasks": sum(1 for t in investigation.tasks if t.status == ModuleStatus.SUCCESS),
    }


@router.get("")
async def list_investigations(
    status: Optional[str] = None,
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
):
    """List all investigations."""
    investigations = list(_investigations.values())
    
    if status:
        investigations = [i for i in investigations if i.status == status]
    
    if tenant_id:
        investigations = [i for i in investigations if i.tenant_id == tenant_id]
    
    return {"investigations": investigations, "total": len(investigations)}


@router.delete("/{investigation_id}")
async def cancel_investigation(investigation_id: str):
    """Cancel an investigation."""
    investigation = get_investigation_or_404(investigation_id)
    
    if investigation.status in (InvestigationStatus.COMPLETED, InvestigationStatus.FAILED, InvestigationStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Cannot cancel investigation with status: {investigation.status}")
    
    investigation.status = InvestigationStatus.CANCELLED
    logger.info(f"Cancelled investigation: {investigation_id}")
    
    return {"message": "Investigation cancelled", "investigation_id": investigation_id}


def _detect_target_type(target: str) -> str:
    """Detect the type of target."""
    target = target.lower().strip()
    
    if target.startswith("http://") or target.startswith("https://"):
        return "url"
    
    if "@" in target and "." in target:
        return "email"
    
    if target.count(".") >= 2 or target.count(".") == 1 and not target.replace(".", "").isdigit():
        return "domain"
    
    if target.replace(".", "").isdigit() and len(target.split(".")) == 4:
        return "ip"
    
    if target.startswith("@") or target.replace("_", "").replace(".", "").isalnum():
        return "username"
    
    if target.isdigit() and 7 <= len(target) <= 15:
        return "phone"
    
    return "unknown"
