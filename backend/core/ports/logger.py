"""Logger port - Interface for structured logging and observability."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ILogger(ABC):
    """Interface for structured logging with metrics and tracing."""
    
    @abstractmethod
    def log(
        self,
        level: LogLevel,
        message: str,
        **kwargs: Any,
    ) -> None:
        """
        Log a message with structured fields.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Structured fields (will be JSON-encoded)
        """
        pass
    
    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log at DEBUG level."""
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """Log at INFO level."""
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log at WARNING level."""
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """Log at ERROR level."""
        pass
    
    @abstractmethod
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log at CRITICAL level."""
        pass
    
    @abstractmethod
    def record_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a metric value.
        
        Args:
            metric_name: Metric identifier
            value: Numeric value
            labels: Optional labels for the metric
        """
        pass
    
    @abstractmethod
    def start_span(
        self,
        span_name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> 'Span':
        """
        Start a distributed tracing span.
        
        Args:
            span_name: Span identifier
            attributes: Optional span attributes
        
        Returns:
            Span context manager
        """
        pass


class Span:
    """Distributed tracing span (context manager)."""
    
    def __init__(self, span_name: str):
        self.span_name = span_name
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        pass
    
    def record_exception(self, exception: Exception) -> None:
        """Record exception in span."""
        pass
