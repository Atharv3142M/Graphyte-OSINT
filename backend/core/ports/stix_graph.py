"""STIX graph port - Interface for entity resolution and graph storage."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class IStixGraph(ABC):
    """Interface for STIX-based graph persistence and entity resolution."""
    
    @abstractmethod
    async def ingest_bundle(
        self,
        investigation_id: str,
        bundle: Dict[str, Any],
    ) -> None:
        """
        Ingest a STIX bundle into the graph.
        
        Args:
            investigation_id: Investigation ID for tracking
            bundle: STIX bundle object
        
        Raises:
            StixIngestionError: If ingestion fails
        """
        pass
    
    @abstractmethod
    async def resolve_entity(self, entity_type: str, value: str) -> Optional[Dict[str, Any]]:
        """
        Resolve an entity (find connected nodes in graph).
        
        Args:
            entity_type: Type of entity (domain, ip, email, etc.)
            value: Entity value
        
        Returns:
            Entity node data or None if not found
        """
        pass
    
    @abstractmethod
    async def get_entity_relationships(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Get all relationships for an entity.
        
        Args:
            entity_id: Entity node ID
        
        Returns:
            List of relationship objects
        """
        pass
    
    @abstractmethod
    async def get_investigation_subgraph(self, investigation_id: str) -> Dict[str, Any]:
        """
        Get the complete STIX subgraph for an investigation.
        
        Args:
            investigation_id: Investigation ID
        
        Returns:
            Subgraph as nodes and relationships
        """
        pass
    
    @abstractmethod
    async def create_entity(
        self,
        entity_type: str,
        value: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new entity node.
        
        Args:
            entity_type: Type of entity
            value: Entity value
            properties: Additional properties
        
        Returns:
            Created entity data
        """
        pass
    
    @abstractmethod
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Create a relationship between two entities.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            properties: Relationship properties
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if STIX graph service is healthy."""
        pass
