"""Investigation and Task domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a single module execution task."""
    
    task_id: str = field(default_factory=lambda: str(uuid4()))
    investigation_id: str = ""
    module_name: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    
    def start(self) -> None:
        """Mark task as running."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete(self, result: Dict[str, Any], duration_ms: float) -> None:
        """Mark task as succeeded."""
        self.status = TaskStatus.SUCCESS
        self.result = result
        self.duration_ms = duration_ms
        self.completed_at = datetime.utcnow()
    
    def fail(self, error_code: str, error_message: str, duration_ms: float) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.error_code = error_code
        self.error_message = error_message
        self.duration_ms = duration_ms
        self.completed_at = datetime.utcnow()
    
    def timeout(self, duration_ms: float) -> None:
        """Mark task as timed out."""
        self.status = TaskStatus.TIMEOUT
        self.error_code = "TASK_TIMEOUT"
        self.error_message = f"Task exceeded timeout of {duration_ms}ms"
        self.duration_ms = duration_ms
        self.completed_at = datetime.utcnow()
    
    def is_complete(self) -> bool:
        """Check if task has finished execution."""
        return self.status in (
            TaskStatus.SUCCESS,
            TaskStatus.FAILED,
            TaskStatus.TIMEOUT,
            TaskStatus.CANCELLED,
        )


@dataclass
class Investigation:
    """Represents a complete investigation with multiple module tasks."""
    
    investigation_id: str = field(default_factory=lambda: str(uuid4()))
    playbook_id: str = ""
    target: str = ""
    target_type: str = ""  # "domain", "ip", "email", "hash", etc.
    intensity: str = "standard"  # "light", "standard", "deep"
    tenant_id: Optional[str] = None
    tasks: List[Task] = field(default_factory=list)
    status: str = "running"  # "running", "completed", "failed"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[float] = None
    
    def add_task(self, module_name: str, payload: Dict[str, Any]) -> Task:
        """Add a task to this investigation."""
        task = Task(
            investigation_id=self.investigation_id,
            module_name=module_name,
            payload=payload,
        )
        self.tasks.append(task)
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        return next((t for t in self.tasks if t.task_id == task_id), None)
    
    def are_all_tasks_complete(self) -> bool:
        """Check if all tasks have finished."""
        return all(task.is_complete() for task in self.tasks)
    
    def mark_complete(self) -> None:
        """Mark investigation as complete."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        # Calculate total duration
        start = self.created_at
        end = self.completed_at
        self.total_duration_ms = (end - start).total_seconds() * 1000
    
    def get_successful_tasks(self) -> List[Task]:
        """Get all successfully completed tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.SUCCESS]
    
    def get_failed_tasks(self) -> List[Task]:
        """Get all failed tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.FAILED]
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get investigation statistics."""
        return {
            "total_tasks": len(self.tasks),
            "successful": len(self.get_successful_tasks()),
            "failed": len(self.get_failed_tasks()),
            "pending": len([t for t in self.tasks if t.status == TaskStatus.PENDING]),
            "running": len([t for t in self.tasks if t.status == TaskStatus.RUNNING]),
            "total_duration_ms": self.total_duration_ms,
        }
