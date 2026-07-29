"""Ports - Interface contracts for adapters (Hexagonal Architecture)."""

from .task_queue import ITaskQueue
from .module_registry import IModuleRegistry
from .result_store import IResultStore
from .stix_graph import IStixGraph
from .logger import ILogger
from .config import IConfig

__all__ = [
    "ITaskQueue",
    "IModuleRegistry",
    "IResultStore",
    "IStixGraph",
    "ILogger",
    "IConfig",
]
