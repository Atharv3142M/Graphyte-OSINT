"""Playbook domain models for investigation workflows."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class TargetType(str, Enum):
    """Supported target types for investigations."""
    DOMAIN = "domain"
    IP_ADDRESS = "ip"
    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    HASH = "hash"
    URL = "url"
    ASN = "asn"
    ORGANIZATION = "organization"


class Intensity(str, Enum):
    """Investigation intensity levels."""
    LIGHT = "light"      # Quick surface-level scan
    STANDARD = "standard"  # Normal comprehensive scan
    DEEP = "deep"        # Intensive, time-consuming scan


@dataclass
class PlaybookDefinition:
    """Definition of which modules run for target types and intensity levels."""
    
    playbook_id: str
    name: str
    description: str
    # Map: (target_type, intensity) -> list of module names
    module_matrix: Dict[tuple[str, str], List[str]] = field(default_factory=dict)
    
    def get_modules_for(self, target_type: str, intensity: str) -> List[str]:
        """Get modules to run for target type and intensity."""
        key = (target_type, intensity)
        return self.module_matrix.get(key, [])
    
    def add_module_mapping(self, target_types: List[str], intensities: List[str], modules: List[str]) -> None:
        """Register module mapping for target types and intensities."""
        for target_type in target_types:
            for intensity in intensities:
                key = (target_type, intensity)
                self.module_matrix[key] = modules


@dataclass
class Playbook:
    """Runtime playbook configuration for an investigation."""
    
    playbook_id: str
    investigation_id: str
    target: str
    target_type: str
    intensity: str
    modules: List[str]
    execution_order: List[str] = field(default_factory=list)  # Optional parallel execution strategy
    timeout_seconds: int = 300
    retry_policy: Dict[str, int] = field(default_factory=lambda: {"max_retries": 2, "backoff_seconds": 5})
    
    def should_run_in_parallel(self) -> bool:
        """Determine if modules can run in parallel."""
        # All modules can run in parallel by default (no data dependencies)
        return True
    
    def get_module_timeout(self, module_name: str) -> int:
        """Get timeout for a specific module."""
        # Can be overridden per-module if needed
        return 30
    
    def validate(self) -> List[str]:
        """Validate playbook configuration. Returns list of errors."""
        errors = []
        
        if not self.target:
            errors.append("Target cannot be empty")
        if not self.modules:
            errors.append("At least one module must be specified")
        if self.timeout_seconds <= 0:
            errors.append("Timeout must be positive")
        
        return errors
