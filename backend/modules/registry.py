"""Module registry - Plugin discovery and registration system."""

import importlib
import os
from pathlib import Path
from typing import Dict, Tuple, List, Type, Optional
import inspect

from backend.modules.base import BaseModule, ModuleMetadata


# Global module registry
_MODULE_REGISTRY: Dict[str, Tuple[Type[BaseModule], ModuleMetadata]] = {}


def register_module(metadata: ModuleMetadata):
    """
    Decorator to register a module.
    
    Usage:
        @register_module(ModuleMetadata(
            name="dns_intel",
            display_name="DNS Intelligence",
            description="DNS reconnaissance",
            category=ModuleCategory.RECON,
        ))
        class DnsIntelModule(BaseModule):
            async def execute(self, payload):
                ...
    """
    def decorator(cls: Type[BaseModule]) -> Type[BaseModule]:
        if not issubclass(cls, BaseModule):
            raise TypeError(f"{cls.__name__} must inherit from BaseModule")
        
        _MODULE_REGISTRY[metadata.name] = (cls, metadata)
        print(f"✓ Registered module: {metadata.name}")
        return cls
    
    return decorator


def get_module(module_name: str) -> Tuple[Type[BaseModule], ModuleMetadata]:
    """
    Get a module class and metadata by name.
    
    Args:
        module_name: Module name
    
    Returns:
        Tuple of (module_class, metadata)
    
    Raises:
        ValueError: If module not found
    """
    if module_name not in _MODULE_REGISTRY:
        raise ValueError(f"Module '{module_name}' not found in registry")
    
    return _MODULE_REGISTRY[module_name]


def list_modules() -> List[Tuple[str, ModuleMetadata]]:
    """List all registered modules."""
    return [(name, meta) for name, (_, meta) in _MODULE_REGISTRY.items()]


def list_modules_by_category(category) -> List[Tuple[str, ModuleMetadata]]:
    """List modules by category."""
    return [(name, meta) for name, meta in list_modules() if meta.category == category]


def is_registered(module_name: str) -> bool:
    """Check if module is registered."""
    return module_name in _MODULE_REGISTRY


def discover_modules(search_path: str) -> int:
    """
    Auto-discover and import modules from a directory.
    This triggers all @register_module decorators.
    
    Args:
        search_path: Directory to search
    
    Returns:
        Number of modules discovered
    """
    path = Path(search_path)
    if not path.is_dir():
        raise ValueError(f"Search path is not a directory: {search_path}")
    
    initial_count = len(_MODULE_REGISTRY)
    
    # Walk through directory structure
    for py_file in path.rglob("*.py"):
        if py_file.name.startswith("_") or py_file.name == "base.py" or py_file.name == "registry.py":
            continue
        
        # Convert file path to module path
        try:
            relative_path = py_file.relative_to(path.parent)
            module_path = str(relative_path).replace(os.sep, ".").replace(".py", "")
            
            # Import the module (triggers decorators)
            importlib.import_module(module_path)
        
        except (ImportError, ValueError, ModuleNotFoundError) as e:
            print(f"⚠️  Failed to import module from {py_file}: {e}")
            continue
    
    discovered = len(_MODULE_REGISTRY) - initial_count
    return discovered


def get_registry_info() -> Dict[str, any]:
    """Get registry information for diagnostics."""
    return {
        "total_modules": len(_MODULE_REGISTRY),
        "modules": [
            {
                "name": name,
                "display_name": meta.display_name,
                "category": meta.category.value,
                "version": meta.version,
                "timeout_seconds": meta.timeout_seconds,
                "supports_async": meta.supports_async,
            }
            for name, meta in list_modules()
        ],
    }


# Legacy compatibility - expose _REGISTRY for backward compatibility
def get_all_modules_dict() -> Dict[str, Tuple[Type[BaseModule], ModuleMetadata]]:
    """Get raw registry dictionary."""
    return _MODULE_REGISTRY.copy()
