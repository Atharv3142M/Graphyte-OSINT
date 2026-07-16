"""Domain layer - Pure business logic, no framework dependencies."""

from .investigation import Investigation, Task, TaskStatus
from .result import Result, ModuleResult, Artifact
from .playbook import Playbook, PlaybookDefinition
from .errors import (
    DomainError,
    InvalidTargetError,
    ModuleNotFoundError,
    PlaybookNotFoundError,
    TaskQueueError,
)

__all__ = [
    "Investigation",
    "Task",
    "TaskStatus",
    "Result",
    "ModuleResult",
    "Artifact",
    "Playbook",
    "PlaybookDefinition",
    "DomainError",
    "InvalidTargetError",
    "ModuleNotFoundError",
    "PlaybookNotFoundError",
    "TaskQueueError",
]
