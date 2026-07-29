"""Universal module wrapper with error handling, retries, and monitoring."""
import json
import logging
import sys
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ModuleError(Exception):
    """Base module error."""
    
    def __init__(self, message: str, error_code: str = "MODULE_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class ModuleTimeoutError(ModuleError):
    """Module execution timeout."""
    
    def __init__(self, message: str, timeout_seconds: int):
        super().__init__(message, "MODULE_TIMEOUT", {"timeout_seconds": timeout_seconds})


class ModuleNotFoundError(ModuleError):
    """Module not found."""
    
    def __init__(self, module_name: str):
        super().__init__(f"Module not found: {module_name}", "MODULE_NOT_FOUND", {"module_name": module_name})


class ModuleResult:
    """Standard module result format."""
    
    def __init__(
        self,
        module_name: str,
        status: str = "success",
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        duration_ms: int = 0,
        artifacts: Optional[list] = None,
        warnings: Optional[list] = None,
    ):
        self.module_name = module_name
        self.status = status  # success, error, timeout, skipped
        self.data = data or {}
        self.error = error
        self.error_code = error_code
        self.duration_ms = duration_ms
        self.artifacts = artifacts or []
        self.warnings = warnings or []
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "module_name": self.module_name,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "duration_ms": self.duration_ms,
            "artifacts": self.artifacts,
            "warnings": self.warnings,
            "timestamp": self.timestamp,
        }
    
    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict())


def with_error_handling(max_retries: int = 2, timeout_seconds: int = 300):
    """Decorator for module functions with error handling."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> ModuleResult:
            module_name = kwargs.get("module_name") or getattr(func, "__module__", "unknown")
            start_time = time.time()
            last_error = None
            
            # Retry logic
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Executing {module_name} (attempt {attempt + 1}/{max_retries + 1})")
                    
                    # Call the wrapped function
                    result = func(*args, **kwargs)
                    
                    # Ensure result is ModuleResult
                    if not isinstance(result, ModuleResult):
                        result = ModuleResult(
                            module_name=module_name,
                            status="success",
                            data=result if isinstance(result, dict) else {},
                        )
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    result.duration_ms = duration_ms
                    
                    logger.info(f"✓ {module_name} completed in {duration_ms}ms")
                    return result
                
                except ModuleTimeoutError as e:
                    logger.error(f"✗ {module_name} timeout: {e.message}")
                    duration_ms = int((time.time() - start_time) * 1000)
                    return ModuleResult(
                        module_name=module_name,
                        status="timeout",
                        error=e.message,
                        error_code=e.error_code,
                        duration_ms=duration_ms,
                    )
                
                except ModuleError as e:
                    logger.warning(f"✗ {module_name} error: {e.message}")
                    last_error = e
                    if attempt < max_retries:
                        logger.info(f"Retrying in 2 seconds...")
                        time.sleep(2)
                    continue
                
                except Exception as e:
                    logger.error(f"✗ {module_name} unexpected error: {str(e)}", exc_info=True)
                    last_error = e
                    if attempt < max_retries:
                        time.sleep(2)
                    continue
            
            # All retries exhausted
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = last_error.message if isinstance(last_error, ModuleError) else str(last_error)
            error_code = last_error.error_code if isinstance(last_error, ModuleError) else "UNKNOWN_ERROR"
            
            logger.error(f"✗ {module_name} failed after {max_retries + 1} attempts")
            return ModuleResult(
                module_name=module_name,
                status="error",
                error=error_msg,
                error_code=error_code,
                duration_ms=duration_ms,
            )
        
        return wrapper
    
    return decorator


def safe_module_runner(module_func: Callable, payload: Dict[str, Any], timeout_seconds: int = 300) -> ModuleResult:
    """Safely run a module function with timeout and error handling."""
    module_name = payload.get("module_name", "unknown")
    start_time = time.time()
    
    try:
        # Try to execute with timeout
        # Note: In real implementation, use signal/multiprocessing for true timeout
        result = module_func(**payload)
        
        if not isinstance(result, ModuleResult):
            result = ModuleResult(module_name=module_name, data=result or {})
        
        result.duration_ms = int((time.time() - start_time) * 1000)
        return result
    
    except Exception as e:
        logger.error(f"Module {module_name} failed: {e}", exc_info=True)
        return ModuleResult(
            module_name=module_name,
            status="error",
            error=str(e),
            error_code="EXECUTION_ERROR",
            duration_ms=int((time.time() - start_time) * 1000),
        )
