"""Task queue port - Interface for enqueuing and tracking tasks."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TaskState(str, Enum):
    """Task execution state."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class TaskInfo:
    """Information about a task."""
    task_id: str
    state: TaskState
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ITaskQueue(ABC):
    """Interface for task queue abstraction (Celery, RQ, etc.)."""
    
    @abstractmethod
    async def enqueue_task(
        self,
        module_name: str,
        payload: Dict[str, Any],
        task_id: Optional[str] = None,
    ) -> str:
        """
        Enqueue a module execution task.
        
        Args:
            module_name: Name of module to execute
            payload: Task payload/arguments
            task_id: Optional task ID (if None, will be generated)
        
        Returns:
            Task ID for tracking
        
        Raises:
            TaskQueueError: If enqueueing fails
        """
        pass
    
    @abstractmethod
    async def get_task_status(self, task_id: str) -> TaskInfo:
        """
        Get current status of a task.
        
        Args:
            task_id: Task ID to check
        
        Returns:
            TaskInfo with current state and result
        """
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending/running task.
        
        Args:
            task_id: Task ID to cancel
        
        Returns:
            True if cancelled, False if not possible
        """
        pass
    
    @abstractmethod
    async def wait_for_completion(
        self,
        task_id: str,
        timeout_seconds: int = 300,
    ) -> TaskInfo:
        """
        Wait for a task to complete.
        
        Args:
            task_id: Task ID to wait for
            timeout_seconds: Maximum wait time
        
        Returns:
            Final TaskInfo
        
        Raises:
            TimeoutError: If task doesn't complete in time
        """
        pass
