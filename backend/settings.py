"""Production-grade settings and configuration management."""
import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # API
    API_TITLE: str = "Graphyte OSINT Platform"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    if os.getenv("CORS_ORIGINS"):
        CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
    
    # Redis/Celery
    REDIS_URL: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    CELERY_BROKER_URL: str = Field(default_factory=lambda: os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
    CELERY_RESULT_BACKEND: str = Field(default_factory=lambda: os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1"))
    
    # Database
    DATABASE_URL: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://localhost/osint"))
    
    # Neo4j
    NEO4J_URI: str = Field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    NEO4J_USER: str = Field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    NEO4J_PASSWORD: str = Field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password"))
    
    # RabbitMQ
    RABBITMQ_URL: str = Field(default_factory=lambda: os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/"))
    
    # Weaviate
    WEAVIATE_URL: str = Field(default_factory=lambda: os.getenv("WEAVIATE_URL", "http://localhost:8080"))
    
    # JWT
    JWT_SECRET: str = Field(default_factory=lambda: os.getenv("JWT_SECRET", "dev-secret-change-in-production"))
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
    AUTH_REQUIRED: bool = os.getenv("AUTH_REQUIRED", "false").lower() in {"1", "true", "yes"}
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Module Defaults
    MODULE_TIMEOUT: int = int(os.getenv("MODULE_TIMEOUT", "300"))  # 5 minutes
    MODULE_RETRIES: int = int(os.getenv("MODULE_RETRIES", "2"))
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in {"1", "true", "yes"}
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
