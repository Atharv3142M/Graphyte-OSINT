"""Base module class - All OSINT modules inherit from this."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio


class ModuleCategory(str, Enum):
    """Module classification."""
    RECON = "recon"
    ENUMERATION = "enumeration"
    ANALYSIS = "analysis"
    VERIFICATION = "verification"
    CORRELATION = "correlation"


@dataclass
class ModuleMetadata:
    """Module metadata for discovery and documentation."""
    
    name: str
    display_name: str
    description: str
    category: ModuleCategory
    version: str = "1.0.0"
    timeout_seconds: int = 30
    supports_async: bool = False
    requires_api_key: bool = False
    api_keys: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    input_schema: Optional[Dict[str, Any]] = None


@dataclass
class ModuleResult:
    """Standardized result from module execution."""
    
    module_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    artifacts: list[Dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0
    executed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "module_name": self.module_name,
            "success": self.success,
            "data": self.data,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "artifacts": self.artifacts,
            "duration_ms": self.duration_ms,
            "executed_at": self.executed_at.isoformat(),
        }


class BaseModule(ABC):
    """Base class for all OSINT modules."""
    
    metadata: ModuleMetadata
    
    def __init__(self, config: Optional[Any] = None, logger: Optional[Any] = None):
        """
        Initialize module.
        
        Args:
            config: Configuration object (IConfig port)
            logger: Logger object (ILogger port)
        """
        self.config = config
        self.logger = logger
    
    @abstractmethod
    async def execute(self, payload: Dict[str, Any]) -> ModuleResult:
        """
        Execute the module with given payload.
        
        Args:
            payload: Module input data
        
        Returns:
            ModuleResult with execution outcome
        """
        pass
    
    async def before_execute(self) -> None:
        """
        Optional hook called before execution.
        Override to perform setup (API client initialization, etc.)
        """
        pass
    
    async def after_execute(self, result: ModuleResult) -> None:
        """
        Optional hook called after execution.
        Override to perform cleanup or post-processing.
        
        Args:
            result: Execution result
        """
        pass
    
    def _run_sync(self, sync_fn, *args, **kwargs):
        """
        Helper to run synchronous code from async context.
        Uses thread pool executor to avoid blocking event loop.
        
        Args:
            sync_fn: Synchronous function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Result of sync_fn
        """
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, lambda: sync_fn(*args, **kwargs))
    
    def _validate_payload(self, payload: Dict[str, Any], required_keys: list[str]) -> Optional[ModuleResult]:
        """
        Validate that payload contains required keys.
        
        Args:
            payload: Payload to validate
            required_keys: List of required keys
        
        Returns:
            ModuleResult error if validation fails, None if valid
        """
        for key in required_keys:
            if key not in payload:
                return ModuleResult(
                    module_name=self.metadata.name,
                    success=False,
                    error_code="INVALID_PAYLOAD",
                    error_message=f"Missing required field: {key}",
                )
        return None
    
    def _log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        if self.logger:
            self.logger.info(message, module=self.metadata.name, **kwargs)
    
    def _log_error(self, message: str, **kwargs) -> None:
        """Log error message."""
        if self.logger:
            self.logger.error(message, module=self.metadata.name, **kwargs)
    
    def _create_result(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        artifacts: Optional[list[Dict[str, Any]]] = None,
    ) -> ModuleResult:
        """Factory method to create a result."""
        return ModuleResult(
            module_name=self.metadata.name,
            success=success,
            data=data,
            error_code=error_code,
            error_message=error_message,
            artifacts=artifacts or [],
        )
