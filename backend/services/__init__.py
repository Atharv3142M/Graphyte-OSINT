"""Service initialization and dependency injection."""
import logging
from typing import Optional
from redis import Redis
from backend.settings import settings

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Central registry for all services."""
    
    _redis: Optional[Redis] = None
    _celery_app = None
    _neo4j_driver = None
    
    @classmethod
    def get_redis(cls) -> Redis:
        """Get or create Redis client."""
        if cls._redis is None:
            try:
                cls._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
                cls._redis.ping()
                logger.info("✓ Redis connected")
            except Exception as e:
                logger.error(f"✗ Redis connection failed: {e}")
                raise
        return cls._redis
    
    @classmethod
    def get_celery_app(cls):
        """Get or create Celery app."""
        if cls._celery_app is None:
            try:
                from celery import Celery
                cls._celery_app = Celery("graphyte")
                cls._celery_app.conf.update(
                    broker_url=settings.CELERY_BROKER_URL,
                    result_backend=settings.CELERY_RESULT_BACKEND,
                    task_track_started=True,
                    task_time_limit=settings.MODULE_TIMEOUT + 60,
                )
                logger.info("✓ Celery configured")
            except Exception as e:
                logger.error(f"✗ Celery setup failed: {e}")
                raise
        return cls._celery_app
    
    @classmethod
    def get_neo4j_driver(cls):
        """Get or create Neo4j driver."""
        if cls._neo4j_driver is None:
            try:
                from neo4j import GraphDatabase
                cls._neo4j_driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
                )
                cls._neo4j_driver.verify_connectivity()
                logger.info("✓ Neo4j connected")
            except Exception as e:
                logger.error(f"✗ Neo4j connection failed: {e}")
                cls._neo4j_driver = None
        return cls._neo4j_driver
    
    @classmethod
    def check_health(cls) -> dict:
        """Check health of all services."""
        health = {"status": "healthy", "services": {}}
        
        # Check Redis
        try:
            redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
            redis_client.ping()
            health["services"]["redis"] = {"status": "healthy"}
        except Exception as e:
            health["services"]["redis"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "degraded"
        
        # Check PostgreSQL
        try:
            from backend import postgres_client
            postgres_client.get_connection()
            health["services"]["postgres"] = {"status": "healthy"}
        except Exception as e:
            health["services"]["postgres"] = {"status": "unhealthy", "error": str(e)}
            health["status"] = "degraded"
        
        # Check Neo4j
        try:
            driver = cls.get_neo4j_driver()
            if driver:
                health["services"]["neo4j"] = {"status": "healthy"}
        except Exception as e:
            health["services"]["neo4j"] = {"status": "unhealthy", "error": str(e)}
        
        return health
