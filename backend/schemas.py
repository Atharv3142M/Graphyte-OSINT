"""Data models and schemas for the OSINT platform."""
from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ModuleType(str, Enum):
    """Types of OSINT modules."""
    RECON = "recon"
    INTEL = "intel"
    SCANNING = "scanning"
    SCRAPING = "scraping"
    SEARCH = "search"
    ANALYSIS = "analysis"
    REPORTING = "reporting"


class ModuleStatus(str, Enum):
    """Module execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class InvestigationStatus(str, Enum):
    """Investigation status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Artifact(BaseModel):
    """Extracted artifact (IOC)."""
    type: str  # domain, ip, email, etc.
    value: str
    source: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = {}


class ModuleResult(BaseModel):
    """Result from a single OSINT module."""
    module_name: str
    status: ModuleStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int = 0
    artifacts: List[Artifact] = []
    raw_data: Dict[str, Any] = {}
    error: Optional[str] = None
    warning: Optional[str] = None
    tags: List[str] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Task(BaseModel):
    """A single task in an investigation."""
    id: str
    module_name: str
    status: ModuleStatus = ModuleStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[ModuleResult] = None
    retry_count: int = 0


class Investigation(BaseModel):
    """Container for investigation with multiple tasks."""
    id: str
    target: str
    target_type: str  # domain, ip, email, etc.
    status: InvestigationStatus = InvestigationStatus.PENDING
    tasks: List[Task] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tenant_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlaybookRequest(BaseModel):
    """Request to execute a playbook."""
    target: str
    playbook_name: str
    intensity: Optional[str] = "normal"  # light, normal, aggressive
    custom_modules: Optional[List[str]] = None
    tenant_id: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str  # healthy, degraded, unhealthy
    services: Dict[str, Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
