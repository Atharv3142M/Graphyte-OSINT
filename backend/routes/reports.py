"""Report generation routes."""
import uuid
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header

from backend.logging_config import logger

router = APIRouter()

# In-memory report store (TODO: move to database)
_reports = {}


class ReportRequest:
    """Report generation request."""
    investigation_id: str
    report_type: str  # executive, technical, stix, csv


@router.post("")
async def generate_report(
    investigation_id: str,
    report_type: str = "executive",
    tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
):
    """Generate a report from investigation results."""
    report_id = str(uuid.uuid4())
    
    try:
        report = {
            "id": report_id,
            "investigation_id": investigation_id,
            "type": report_type,
            "status": "generating",
            "created_at": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
        }
        
        _reports[report_id] = report
        logger.info(f"Generating {report_type} report {report_id} for investigation {investigation_id}")
        
        return report
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get report details."""
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    
    return _reports[report_id]


@router.get("/{report_id}/download")
async def download_report(report_id: str, format: str = "pdf"):
    """Download report in specified format."""
    if report_id not in _reports:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    
    # TODO: Implement actual report download
    return {
        "report_id": report_id,
        "format": format,
        "status": "download_not_implemented",
        "message": "Report download functionality coming soon",
    }


@router.get("")
async def list_reports(
    investigation_id: Optional[str] = None,
    report_type: Optional[str] = None,
):
    """List reports."""
    reports = list(_reports.values())
    
    if investigation_id:
        reports = [r for r in reports if r.get("investigation_id") == investigation_id]
    
    if report_type:
        reports = [r for r in reports if r.get("type") == report_type]
    
    return {
        "reports": reports,
        "total": len(reports),
    }
