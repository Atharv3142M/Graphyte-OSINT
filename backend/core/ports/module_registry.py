"""Module registry port - Interface for discovering and loading modules."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type, Tuple
from dataclasses import dataclass
from enum import Enum


class ModuleCategory(str, Enum):
    """Module classification."""
    RECON = "recon"
    ENUMERATION = "enumeration"
    ANALYSIS = "analysis"
    VERIFICATION = "verification"


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
    api_keys: List[str] = None
    tags: List[str] = None
    input_schema: Dict[str, Any] = None  # JSON schema
    
    def __post_init__(self):
        if self.api_keys is None:
            self.api_keys = []
        if self.tags is None:
            self.tags = []


class IModuleRegistry(ABC):
    """Interface for module discovery and registration."""
    
    @abstractmethod
    def register(
        self,
        module_name: str,
        module_class: Type,
        metadata: ModuleMetadata,
    ) -> None:
        """
        Register a module.
        
        Args:
            module_name: Unique module identifier
            module_class: Module class (should inherit BaseModule)
            metadata: Module metadata
        """
        pass
    
    @abstractmethod
    def get_module(self, module_name: str) -> Tuple[Type, ModuleMetadata]:
        """
        Get a module class and metadata.
        
        Args:
            module_name: Module to retrieve
        
        Returns:
            Tuple of (module_class, metadata)
        
        Raises:
            ModuleNotFoundError: If module not found
        """
        pass
    
    @abstractmethod
    def list_modules(self) -> List[Tuple[str, ModuleMetadata]]:
        """
        List all registered modules.
        
        Returns:
            List of (module_name, metadata) tuples
        """
        pass
    
    @abstractmethod
    def list_modules_by_category(self, category: ModuleCategory) -> List[Tuple[str, ModuleMetadata]]:
        """
        List modules by category.
        
        Args:
            category: Module category
        
        Returns:
            List of (module_name, metadata) tuples
        """
        pass
    
    @abstractmethod
    def discover_modules(self, search_path: str) -> int:
        """
        Auto-discover modules from a path (imports modules, triggers decorators).
        
        Args:
            search_path: Directory to search for modules
        
        Returns:
            Number of modules discovered
        """
        pass
    
    @abstractmethod
    def is_module_registered(self, module_name: str) -> bool:
        """Check if module is registered."""
        pass
