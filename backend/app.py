"""Production-grade FastAPI application with proper error handling and structure."""
import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.settings import settings
from backend.logging_config import logger
from backend.services import ServiceRegistry
from backend.schemas import ErrorResponse, HealthCheckResponse

# Import route handlers
from backend.routes import (
    auth,
    investigations,
    playbooks,
    modules,
    reports,
    graph,
    websockets,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    logger.info("Starting Graphyte OSINT Platform")
    
    # Startup
    try:
        # Initialize services
        ServiceRegistry.get_redis()
        ServiceRegistry.get_celery_app()
        ServiceRegistry.get_neo4j_driver()
        logger.info("✓ All services initialized")
    except Exception as e:
        logger.error(f"✗ Service initialization failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Graphyte OSINT Platform")


# Create application
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": str(exc),
            "error_code": "VALIDATION_ERROR",
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle all uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        },
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Get application health status."""
    health = ServiceRegistry.check_health()
    status_code = 200 if health["status"] == "healthy" else 503
    return HealthCheckResponse(**health)


@app.get("/ready")
async def readiness_check():
    """Get application readiness status."""
    health = ServiceRegistry.check_health()
    if health["status"] == "unhealthy":
        return {"ready": False, "status": health["status"]}
    return {"ready": True, "status": health["status"]}


# Include route handlers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(investigations.router, prefix="/api/investigations", tags=["Investigations"])
app.include_router(playbooks.router, prefix="/api/playbooks", tags=["Playbooks"])
app.include_router(modules.router, prefix="/api/modules", tags=["Modules"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(websockets.router, tags=["WebSockets"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
