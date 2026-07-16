"""Config port - Interface for configuration management."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum


class Environment(str, Enum):
    """Deployment environment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class IConfig(ABC):
    """Interface for configuration with validation."""
    
    @abstractmethod
    def get_environment(self) -> Environment:
        """Get current environment."""
        pass
    
    @abstractmethod
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        pass
    
    @abstractmethod
    def get_api_host(self) -> str:
        """Get API host."""
        pass
    
    @abstractmethod
    def get_api_port(self) -> int:
        """Get API port."""
        pass
    
    @abstractmethod
    def get_cors_origins(self) -> List[str]:
        """Get CORS allowed origins."""
        pass
    
    @abstractmethod
    def get_jwt_secret(self) -> str:
        """Get JWT signing secret."""
        pass
    
    @abstractmethod
    def get_jwt_algorithm(self) -> str:
        """Get JWT algorithm."""
        pass
    
    @abstractmethod
    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        pass
    
    @abstractmethod
    def get_neo4j_uri(self) -> str:
        """Get Neo4j connection URI."""
        pass
    
    @abstractmethod
    def get_neo4j_credentials(self) -> tuple[str, str]:
        """Get Neo4j username and password."""
        pass
    
    @abstractmethod
    def get_postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        pass
    
    @abstractmethod
    def get_celery_broker_url(self) -> str:
        """Get Celery broker URL."""
        pass
    
    @abstractmethod
    def get_celery_worker_concurrency(self) -> int:
        """Get Celery worker concurrency level."""
        pass
    
    @abstractmethod
    def get_module_timeout_seconds(self) -> int:
        """Get default module timeout."""
        pass
    
    @abstractmethod
    def is_async_modules_enabled(self) -> bool:
        """Check if async module execution is enabled."""
        pass
    
    @abstractmethod
    def get_value(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            default: Default value if not found
        
        Returns:
            Configuration value
        """
        pass
    
    @abstractmethod
    def validate(self) -> List[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all configured services.
        
        Returns:
            Dict of service_name -> is_healthy
        """
        pass
