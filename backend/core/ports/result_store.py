"""Result store port - Interface for storing and retrieving results."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncIterator


class IResultStore(ABC):
    """Interface for result persistence and streaming."""
    
    @abstractmethod
    async def store_result(
        self,
        investigation_id: str,
        task_id: str,
        result: Dict[str, Any],
    ) -> None:
        """
        Store a task result.
        
        Args:
            investigation_id: Investigation ID
            task_id: Task ID
            result: Result data
        """
        pass
    
    @abstractmethod
    async def get_result(self, investigation_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a task result.
        
        Args:
            investigation_id: Investigation ID
            task_id: Task ID
        
        Returns:
            Result data or None if not found
        """
        pass
    
    @abstractmethod
    async def get_all_results(self, investigation_id: str) -> Dict[str, Any]:
        """
        Retrieve all results for an investigation.
        
        Args:
            investigation_id: Investigation ID
        
        Returns:
            Dictionary mapping task_id -> result
        """
        pass
    
    @abstractmethod
    async def delete_results(self, investigation_id: str) -> None:
        """
        Delete all results for an investigation.
        
        Args:
            investigation_id: Investigation ID
        """
        pass
    
    @abstractmethod
    async def publish_event(
        self,
        channel: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Publish an event to a channel (for real-time streaming).
        
        Args:
            channel: Channel name (e.g., "investigation:{id}")
            event_type: Type of event (e.g., "module_result", "investigation_complete")
            payload: Event payload
        """
        pass
    
    @abstractmethod
    async def subscribe_to_channel(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Subscribe to a channel and receive events as they're published.
        
        Args:
            channel: Channel name
        
        Yields:
            Events as they arrive
        """
        pass
    
    @abstractmethod
    async def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from a channel."""
        pass
