# Clean Architecture Refactoring — Graphyte OSINT Platform

**Date:** 2025-07-15 | **Scope:** Production-grade architecture redesign

---

## 🎯 Vision & Principles

Transform Graphyte from a monolithic, tightly-coupled system into a **scalable, maintainable, production-grade platform** using:

- **Clean Architecture (Hexagonal):** Separating business logic from infrastructure
- **Plugin Pattern:** Dynamic module discovery & registration
- **SOLID Principles:** DRY, Single Responsibility, Dependency Injection
- **Domain-Driven Design:** Core domain modeling
- **Event-Driven Communication:** Loose coupling via async events
- **Observable Systems:** Structured logging, metrics, tracing

---

## 📁 New Folder Structure

```
graphyte-osint/
├── backend/
│   ├── core/                           # ← Domain & business logic (NO framework code)
│   │   ├── __init__.py
│   │   ├── domain/                     # Domain models
│   │   │   ├── __init__.py
│   │   │   ├── investigation.py        # Investigation, Task, Module entities
│   │   │   ├── result.py               # Result envelope, artifact types
│   │   │   ├── playbook.py             # Playbook definition, workflow
│   │   │   └── errors.py               # Domain exceptions
│   │   ├── usecases/                   # Application logic (orchestration)
│   │   │   ├── __init__.py
│   │   │   ├── dispatch_investigation.py
│   │   │   ├── get_investigation_status.py
│   │   │   ├── list_modules.py
│   │   │   └── collect_results.py
│   │   ├── ports/                      # Interface contracts (Hexagonal)
│   │   │   ├── __init__.py
│   │   │   ├── module_registry.py      # Ports: IModuleRegistry
│   │   │   ├── task_queue.py           # Ports: ITaskQueue
│   │   │   ├── result_store.py         # Ports: IResultStore
│   │   │   ├── stix_graph.py           # Ports: IStixGraph
│   │   │   ├── logger.py               # Ports: ILogger
│   │   │   └── config.py               # Ports: IConfig
│   │   └── utils/                      # Pure utility functions
│   │       ├── __init__.py
│   │       └── normalizers.py
│   │
│   ├── adapters/                       # ← Implementation of ports (framework-specific)
│   │   ├── __init__.py
│   │   ├── module_registry/            # IModuleRegistry implementation
│   │   │   ├── __init__.py
│   │   │   ├── plugin_loader.py
│   │   │   ├── registry.py
│   │   │   └── module_discovery.py
│   │   ├── task_queue/                 # ITaskQueue implementation (Celery)
│   │   │   ├── __init__.py
│   │   │   ├── celery_adapter.py
│   │   │   ├── celery_config.py
│   │   │   └── celery_tasks.py
│   │   ├── result_store/               # IResultStore implementation (Redis)
│   │   │   ├── __init__.py
│   │   │   ├── redis_adapter.py
│   │   │   └── result_cache.py
│   │   ├── stix_graph/                 # IStixGraph implementation (Neo4j)
│   │   │   ├── __init__.py
│   │   │   ├── neo4j_adapter.py
│   │   │   └── stix_builder.py
│   │   ├── logger/                     # ILogger implementation (structured logging)
│   │   │   ├── __init__.py
│   │   │   ├── structured_logger.py
│   │   │   ├── metrics.py
│   │   │   └── tracer.py
│   │   ├── config/                     # IConfig implementation (environment validation)
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   └── http/                       # FastAPI request/response adapters
│   │       ├── __init__.py
│   │       ├── middleware.py
│   │       ├── error_handlers.py
│   │       └── response_formatters.py
│   │
│   ├── modules/                        # ← OSINT modules (plugins)
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseModule, ModuleMetadata
│   │   ├── registry.py                 # @register_module decorator
│   │   ├── dns/                        # Module namespace (clean organization)
│   │   │   ├── __init__.py
│   │   │   ├── dns_intel.py
│   │   │   ├── dns_bruteforce.py
│   │   │   └── module.py               # Module factory
│   │   ├── http/
│   │   │   ├── __init__.py
│   │   │   ├── deep_scraper.py
│   │   │   ├── social_hunter.py
│   │   │   └── module.py
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── entity_resolution.py
│   │   │   └── module.py
│   │   ├── verification/
│   │   │   ├── __init__.py
│   │   │   ├── screenshot_capture.py
│   │   │   └── module.py
│   │   └── ... (more module namespaces)
│   │
│   ├── api/                            # ← HTTP API layer (request/response handling)
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI app creation
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── investigations.py    # POST /api/v1/investigations
│   │   │   │   ├── modules.py          # GET /api/v1/modules
│   │   │   │   ├── playbooks.py        # GET /api/v1/playbooks
│   │   │   │   ├── status.py           # GET /api/v1/investigations/{id}
│   │   │   │   ├── results.py          # GET /api/v1/investigations/{id}/results
│   │   │   │   └── websocket.py        # WS /ws/investigations/{id}
│   │   │   └── health.py               # GET /health, /ready
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── requests.py
│   │   │   └── responses.py
│   │   ├── dependencies.py             # FastAPI dependency injection
│   │   └── openapi_schemas.py          # OpenAPI documentation
│   │
│   ├── worker/                         # ← Celery worker entry points
│   │   ├── __init__.py
│   │   ├── main.py                     # Worker startup, signal handlers
│   │   ├── executor.py                 # Module execution logic
│   │   └── handlers.py                 # Task complete/failed handlers
│   │
│   ├── bin/                            # ← Command-line entry points
│   │   ├── __init__.py
│   │   ├── api.py                      # python -m backend.bin.api
│   │   ├── worker.py                   # python -m backend.bin.worker
│   │   ├── init_modules.py             # Module discovery & registration
│   │   └── health_check.py             # Production health checks
│   │
│   ├── __init__.py
│   ├── config.py                       # Global config (imports from adapters)
│   └── container.py                    # Dependency injection container
│
├── frontend/
│   ├── src/
│   │   ├── api/                        # API client (auto-generated from OpenAPI)
│   │   ├── hooks/                      # React hooks
│   │   ├── store/                      # Zustand stores
│   │   ├── components/                 # React components
│   │   ├── pages/                      # Pages
│   │   └── lib/                        # Utilities
│   └── ...
│
├── shared/                             # ← Shared types (TypeScript definitions)
│   ├── __init__.py
│   ├── domain.ts                       # Investigation, Task, Result types
│   └── errors.ts                       # Error codes
│
├── docker/                             # Docker configs
├── k8s/                                # Kubernetes manifests
├── docs/                               # Architecture docs
└── tests/                              # Test suites

```

---

## 🏛️ Clean Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│  API Layer (FastAPI Routes, WebSocket)                  │
│  - Requests/Responses only                              │
│  - No business logic                                    │
└──────────────────────┬──────────────────────────────────┘
                       │ Dependency Injection
┌──────────────────────▼──────────────────────────────────┐
│  Application/Usecase Layer (Orchestration)              │
│  - dispatch_investigation.py                           │
│  - get_investigation_status.py                          │
│  - High-level workflow coordination                     │
└──────────────────────┬──────────────────────────────────┘
                       │ Dependency Injection
┌──────────────────────▼──────────────────────────────────┐
│  Domain Layer (Business Logic)                          │
│  - Investigation, Task, Result entities                │
│  - Playbook definitions                                │
│  - Domain exceptions                                   │
│  - Pure logic (no framework, no I/O)                    │
└──────────────────────┬──────────────────────────────────┘
                       │ Interface contracts (Ports)
┌──────────────────────▼──────────────────────────────────┐
│  Adapter Layer (Implementation)                         │
│  - Celery adapter (ITaskQueue implementation)           │
│  - Redis adapter (IResultStore implementation)          │
│  - Neo4j adapter (IStixGraph implementation)            │
│  - Logger adapter (ILogger implementation)              │
│  - Config adapter (IConfig implementation)              │
└─────────────────────────────────────────────────────────┘
         │
         └─→ External Services (Redis, Neo4j, PostgreSQL, RabbitMQ)
```

---

## 🔄 Data Flow (After Refactoring)

```
1. User submits request
2. FastAPI Route (api/routes/v1/investigations.py)
   ├─ Deserialize request → Request DTO
   ├─ Validate using Pydantic schema
   └─ Call usecase layer

3. UseCase (usecases/dispatch_investigation.py)
   ├─ Fetch playbook definition (domain logic)
   ├─ Enqueue modules via dependency-injected ITaskQueue
   ├─ Log audit event via ILogger
   └─ Return Response DTO

4. Adapter Layer (adapters/task_queue/celery_adapter.py)
   ├─ Convert domain Task → Celery task call
   ├─ Invoke CeleryTask.delay() with payload
   └─ Return task_id

5. Celery Worker (worker/executor.py)
   ├─ Fetch module from IModuleRegistry
   ├─ Execute module.execute(payload)
   ├─ Normalize result
   ├─ Publish event via IResultStore (Redis pub/sub)
   └─ On completion → call handler

6. Result Handler (worker/handlers.py)
   ├─ Build STIX bundle
   ├─ Ingest to Neo4j via IStixGraph
   ├─ Mark investigation complete
   └─ Emit "investigation_complete" event

7. Frontend WebSocket
   ├─ Connected to /ws/investigations/{id}
   ├─ Receives real-time module_result events
   ├─ On investigation_complete event → refresh UI
   └─ Display results
```

---

## 🔧 Key Architectural Improvements

### 1. **Dependency Injection (Inversion of Control)**

```python
# backend/container.py
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    # Configuration
    config = providers.Singleton(Config)
    
    # Adapters (implementation of ports)
    task_queue = providers.Singleton(
        CeleryAdapter,
        config=config,
    )
    result_store = providers.Singleton(
        RedisAdapter,
        config=config,
    )
    module_registry = providers.Singleton(
        PluginRegistry,
        loader=providers.Singleton(PluginLoader),
    )
    logger = providers.Singleton(
        StructuredLogger,
        config=config,
    )
    stix_graph = providers.Singleton(
        Neo4jAdapter,
        config=config,
    )
    
    # Usecases
    dispatch_investigation_uc = providers.Factory(
        DispatchInvestigationUsecase,
        task_queue=task_queue,
        module_registry=module_registry,
        logger=logger,
    )
```

**Benefits:**
- All adapters injected into usecases
- Easy to mock in tests
- Flexible to swap implementations (e.g., Redis → RabbitMQ)

### 2. **Plugin Architecture (Module Discovery)**

```python
# backend/modules/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ModuleMetadata:
    name: str
    display_name: str
    description: str
    category: str  # "recon", "enum", "analysis"
    timeout_seconds: int = 30
    supports_async: bool = False

class BaseModule(ABC):
    metadata: ModuleMetadata
    
    async def execute(self, payload: dict) -> dict:
        """Execute the module. Return normalized result."""
        pass

# backend/modules/registry.py
_REGISTRY = {}

def register_module(metadata: ModuleMetadata):
    """Decorator to register a module."""
    def decorator(cls):
        _REGISTRY[metadata.name] = (cls, metadata)
        return cls
    return decorator

def get_module(name: str) -> tuple[type[BaseModule], ModuleMetadata]:
    return _REGISTRY[name]

def list_modules() -> list[ModuleMetadata]:
    return [meta for _, meta in _REGISTRY.values()]

# backend/modules/dns/dns_intel.py
@register_module(ModuleMetadata(
    name="dns_intel",
    display_name="DNS Intelligence",
    description="Perform DNS reconnaissance",
    category="recon",
    timeout_seconds=30,
))
class DnsIntelModule(BaseModule):
    async def execute(self, payload: dict) -> dict:
        target = payload["target"]
        # Actual implementation
        return {"success": True, "records": [...]}
```

**Benefits:**
- Modules auto-discovered at startup
- No hardcoded if/elif chains
- New modules just inherit BaseModule + decorator
- Can iterate modules without knowing names

### 3. **Ports & Adapters (Hexagonal Architecture)**

```python
# backend/core/ports/task_queue.py (interface)
from abc import ABC, abstractmethod

class ITaskQueue(ABC):
    @abstractmethod
    async def enqueue_task(self, module_name: str, payload: dict) -> str:
        """Enqueue a module execution task. Returns task_id."""
        pass
    
    @abstractmethod
    async def get_task_status(self, task_id: str) -> str:
        """Return task status: pending, running, success, failed."""
        pass

# backend/adapters/task_queue/celery_adapter.py (implementation)
class CeleryAdapter(ITaskQueue):
    def __init__(self, config: IConfig, registry: IModuleRegistry):
        self.config = config
        self.registry = registry
        self.celery_app = Celery("osint")
        # Dynamically register Celery tasks based on module registry
        self._register_dynamic_tasks()
    
    def _register_dynamic_tasks(self):
        """Register a Celery task for each module."""
        for name, metadata in self.registry.list_modules_metadata():
            @self.celery_app.task(name=f"module.{name}", bind=True)
            def execute_module(self_task, payload: dict):
                # Real execution logic
                pass
    
    async def enqueue_task(self, module_name: str, payload: dict) -> str:
        sig = self.celery_app.signature(f"module.{module_name}")
        result = sig.delay(payload)
        return result.id
```

**Benefits:**
- Core domain has NO dependency on Celery, Redis, etc.
- Can swap Celery for RQ, Dramatiq, etc. without changing domain logic
- Easier to test: mock ITaskQueue in tests

### 4. **Structured Logging & Observability**

```python
# backend/adapters/logger/structured_logger.py
import structlog
import prometheus_client

class StructuredLogger(ILogger):
    def __init__(self, config: IConfig):
        structlog.configure(
            processors=[
                structlog.processors.JSONRenderer()
            ],
        )
        self.log = structlog.get_logger()
        self.metrics = {
            "task_duration_seconds": prometheus_client.Histogram(
                "osint_task_duration_seconds",
                "Task execution duration",
                labelnames=["module_name", "status"],
            ),
            "task_failures_total": prometheus_client.Counter(
                "osint_task_failures_total",
                "Task failure count",
                labelnames=["module_name", "error_code"],
            ),
        }
    
    def log_module_execution(self, module_name: str, duration_ms: float, status: str, error: Optional[str] = None):
        """Structured log for module execution."""
        self.log.msg(
            "module_executed",
            module_name=module_name,
            duration_ms=duration_ms,
            status=status,
            error=error,
            correlation_id=contextvars.get("correlation_id"),  # For distributed tracing
        )
        self.metrics["task_duration_seconds"].labels(module_name, status).observe(duration_ms / 1000)
        if error:
            self.metrics["task_failures_total"].labels(module_name, error).inc()
```

**Benefits:**
- Machine-readable JSON logs
- Prometheus metrics for monitoring
- Correlation IDs for distributed tracing
- No more silent failures

### 5. **API Versioning & Unified Endpoints**

```python
# backend/api/routes/v1/investigations.py
from fastapi import APIRouter, Depends
from backend.container import Container

router = APIRouter(prefix="/api/v1", tags=["investigations"])
container = Container()

@router.post("/investigations", response_model=DispatchInvestigationResponse)
async def dispatch_investigation(
    req: DispatchInvestigationRequest,
    uc: DispatchInvestigationUsecase = Depends(lambda: container.dispatch_investigation_uc()),
):
    """Dispatch a new investigation.
    
    Replaces: /api/shodan, /api/censys, /api/dns-intel, etc. (26+ old endpoints)
    """
    result = await uc.execute(
        target=req.target,
        types=req.types,
        intensity=req.intensity,
    )
    return DispatchInvestigationResponse(
        investigation_id=result.investigation_id,
        playbook_id=result.playbook_id,
        modules=result.modules,
        status="running",
    )

# This SINGLE endpoint replaces 26+ hardcoded routes
# Internal routing happens via module registry, not URL routing
```

**Benefits:**
- Single POST /api/v1/investigations endpoint
- Easy to version (/api/v2 for breaking changes)
- No hardcoded per-module routes
- OpenAPI auto-documentation

### 6. **Module Framework & Base Class**

```python
# backend/modules/base.py (complete)
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
from enum import Enum

class ModuleCategory(str, Enum):
    RECON = "recon"
    ENUMERATION = "enumeration"
    ANALYSIS = "analysis"
    VERIFICATION = "verification"

@dataclass
class ModuleMetadata:
    name: str
    display_name: str
    description: str
    category: ModuleCategory
    timeout_seconds: int = 30
    supports_async: bool = False
    requires_auth: bool = False
    api_keys_required: Optional[list[str]] = None
    tags: list[str] = field(default_factory=list)

@dataclass
class ModuleResult:
    module_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    artifacts: list[str] = field(default_factory=list)

class BaseModule(ABC):
    metadata: ModuleMetadata
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
    
    @abstractmethod
    async def execute(self, payload: Dict[str, Any]) -> ModuleResult:
        """Execute module. Always async, even if sync internally."""
        pass
    
    def _run_sync(self, sync_fn):
        """Helper to run sync code from async context."""
        return asyncio.get_event_loop().run_in_executor(None, sync_fn)
```

```python
# backend/modules/dns/dns_intel.py (refactored example)
import dns.resolver
from backend.modules.base import BaseModule, ModuleMetadata, ModuleResult, ModuleCategory

@register_module(ModuleMetadata(
    name="dns_intel",
    display_name="DNS Intelligence",
    description="Perform DNS reconnaissance on a domain",
    category=ModuleCategory.RECON,
    timeout_seconds=15,
))
class DnsIntelModule(BaseModule):
    
    async def execute(self, payload: Dict[str, Any]) -> ModuleResult:
        try:
            target = payload.get("target")
            if not target:
                return ModuleResult(
                    module_name=self.metadata.name,
                    success=False,
                    error_code="INVALID_PAYLOAD",
                    error_message="Missing 'target' field",
                )
            
            # Run DNS resolution asynchronously
            records = await self._run_sync(lambda: self._dns_resolve(target))
            
            return ModuleResult(
                module_name=self.metadata.name,
                success=True,
                data={
                    "domain": target,
                    "a_records": records["a"],
                    "mx_records": records["mx"],
                    "ns_records": records["ns"],
                },
                artifacts=["dns_record", "a_record", "mx_record", "ns_record"],
            )
        
        except dns.exception.DNSException as e:
            self.logger.error(f"DNS resolution failed: {e}")
            return ModuleResult(
                module_name=self.metadata.name,
                success=False,
                error_code="DNS_LOOKUP_FAILED",
                error_message=str(e),
            )
        except Exception as e:
            self.logger.exception(f"Unexpected error in DNS Intel: {e}")
            return ModuleResult(
                module_name=self.metadata.name,
                success=False,
                error_code="INTERNAL_ERROR",
                error_message="Internal module error",
            )
    
    def _dns_resolve(self, domain: str) -> Dict[str, list]:
        """Synchronous DNS resolution."""
        resolver = dns.resolver.Resolver()
        result = {"a": [], "mx": [], "ns": []}
        
        try:
            for rtype in ["A", "MX", "NS"]:
                try:
                    answers = resolver.resolve(domain, rtype)
                    result[rtype.lower()] = [str(rdata) for rdata in answers]
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                    pass
        
        return result
```

**Benefits:**
- Consistent error handling via ModuleResult
- Structured error codes (not just "error": str(e))
- Async interface for all modules
- Type hints throughout
- Clear logging

### 7. **Configuration Management with Validation**

```python
# backend/adapters/config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional
from enum import Enum

class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

class Settings(BaseSettings):
    # Core
    environment: Environment = Environment.DEV
    debug: bool = False
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: list[str] = ["http://localhost:3000"]
    
    # Security
    jwt_secret: str  # REQUIRED, no default
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    
    # Services
    redis_url: str = "redis://localhost:6379/0"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str  # REQUIRED
    postgres_url: str = "postgresql://user:pass@localhost/osint"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672"
    
    # Celery
    celery_broker_url: str = None  # Defaults to redis_url
    celery_worker_concurrency: int = 4
    celery_task_timeout_seconds: int = 300
    
    # Modules
    modules_timeout_seconds: int = 30
    modules_async_enabled: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def celery_broker_url_final(self) -> str:
        return self.celery_broker_url or self.redis_url
    
    def validate_startup(self):
        """Called on app startup to ensure all critical services available."""
        if self.jwt_secret == "dev-osint-secret-change-me":
            raise ValueError("⚠️  JWT_SECRET must be changed in production!")
        
        if self.environment == Environment.PROD and self.debug:
            raise ValueError("Debug mode is not allowed in production!")
        
        # Check service connectivity (Redis, PostgreSQL, Neo4j)
        # This will be called from api/main.py on_event("startup")
```

---

## 📊 Implementation Roadmap

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| **1: Foundation** | Create core/domain, adapters, ports structure | 2 days | 🔴 Critical |
| **2: Plugin System** | Module registry, base class, dynamic discovery | 2 days | 🔴 Critical |
| **3: Celery Migration** | Adapt task queue to plugin architecture | 1 day | 🔴 Critical |
| **4: API v1** | Unified endpoints, versioning, schemas | 1 day | 🟠 Important |
| **5: Observability** | Structured logging, metrics, tracing | 2 days | 🟠 Important |
| **6: Config Management** | Settings validation, fail-fast startup | 1 day | 🟠 Important |
| **7: Module Refactoring** | Update all 26 modules to BaseModule | 3 days | 🟡 Medium |
| **8: Testing** | Unit tests for usecases, adapters, modules | 3 days | 🟡 Medium |
| **9: Documentation** | API docs, architecture guide, runbook | 1 day | 🟡 Medium |
| **10: Migration** | Deploy, verify, monitor, rollback plan | 1 day | 🟠 Important |

**Total Estimated: 17 person-days (3 weeks with 1 senior engineer)**

---

## ✅ Success Metrics

After refactoring:

- ✅ **Adding a new module:** < 30 minutes (just create class + decorator)
- ✅ **Module execution:** Async-capable with structured error handling
- ✅ **Debugging:** Full structured logs + Prometheus metrics
- ✅ **Throughput:** 3x improvement (async I/O + concurrent execution)
- ✅ **Testability:** Mock IModuleRegistry/ITaskQueue in unit tests
- ✅ **API Evolution:** Can add v2 endpoints without touching v1
- ✅ **Maintainability:** DRY code, clear separation of concerns, no hardcoded routing
- ✅ **Monitoring:** Per-module metrics, distributed tracing, health checks

