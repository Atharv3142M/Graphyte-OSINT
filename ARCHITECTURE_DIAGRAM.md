# Clean Architecture — Visual Diagrams

## 1. Layered Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                          │
│ FastAPI Routes, WebSocket Handlers, OpenAPI Docs                    │
│ ✓ HTTP request/response validation                                  │
│ ✓ No business logic                                                 │
└─────────────────────────┬──────────────────────────────────────────┘
                          │
                          │ Dependency Injection
                          │ (Container provides dependencies)
                          ▼
┌────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                             │
│ Usecases: DispatchInvestigationUsecase, GetStatusUsecase, etc.     │
│ ✓ Business workflows and orchestration                              │
│ ✓ No knowledge of HTTP, database, queue implementation              │
│ ✓ Depends only on domain entities and port interfaces               │
└─────────────────────────┬──────────────────────────────────────────┘
                          │
                          │ Domain Entities & Port Interfaces
                          │
                          ▼
┌────────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                                 │
│ Entities, Business Rules, Value Objects                             │
│ • Investigation, Task, Result, Artifact, Playbook                  │
│ • Domain Errors & Exceptions                                       │
│ ✓ NO framework code (no FastAPI, Celery, Redis, etc.)              │
│ ✓ 100% testable without any external dependencies                  │
│ ✓ Pure business logic                                               │
└─────────────────────────┬──────────────────────────────────────────┘
                          │
                          │ Port Interfaces (ITaskQueue, IResultStore, etc.)
                          │
┌─────────────────────────┴──────────────────────────────────────────┐
│                       ADAPTER LAYER                                 │
│ Implementations of Port Interfaces                                  │
│                                                                      │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐   │
│  │  Task Queue Adapter      │  │  Module Registry Adapter     │   │
│  │ (Celery Implementation)  │  │ (Plugin Loader)              │   │
│  │                          │  │                              │   │
│  │ • Enqueue task           │  │ • Register modules           │   │
│  │ • Get task status        │  │ • Discover modules           │   │
│  │ • Cancel task            │  │ • Auto-load at startup       │   │
│  └─────────────────────────┘  └──────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐   │
│  │  Result Store Adapter    │  │  Logger Adapter              │   │
│  │ (Redis Implementation)   │  │ (Structured Logging)         │   │
│  │                          │  │                              │   │
│  │ • Store results          │  │ • JSON structured logs       │   │
│  │ • Publish events         │  │ • Prometheus metrics         │   │
│  │ • Subscribe to channel   │  │ • Distributed tracing        │   │
│  └─────────────────────────┘  └──────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐   │
│  │  STIX Graph Adapter      │  │  Config Adapter              │   │
│  │ (Neo4j Implementation)   │  │ (Settings Validation)        │   │
│  │                          │  │                              │   │
│  │ • Ingest bundles         │  │ • Load from env vars         │   │
│  │ • Resolve entities       │  │ • Validate on startup        │   │
│  │ • Query relationships    │  │ • Health check services      │   │
│  └─────────────────────────┘  └──────────────────────────────┘   │
│                                                                      │
└──────────────────┬─────────────────────────────────────────────────┘
                   │
                   │ External Service Calls
                   │
        ┌──────────┼──────────┬─────────────┐
        ▼          ▼          ▼             ▼
    ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐
    │Redis │  │Neo4j │  │ Celery  │  │PostgreSQL│
    │6379  │  │7687  │  │Broker   │  │5432      │
    └──────┘  └──────┘  └──────┘  └──────────┘
```

---

## 2. Data Flow: Investigation Dispatch

```
┌────────────────┐
│  Frontend      │
│  /dashboard    │
└────────┬───────┘
         │ POST /api/v1/investigations
         │ {target: "example.com", types: ["domain"], intensity: "standard"}
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ API Layer (FastAPI Route Handler)                              │
│  backend/api/routes/v1/investigations.py                       │
│                                                                 │
│  1. Deserialize request → DispatchInvestigationRequest        │
│  2. Validate using Pydantic schema                            │
│  3. Call: uc = get_dispatch_uc()                             │
│  4. Call: await uc.execute(target, target_type, intensity)   │
└─────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Usecase Layer (DispatchInvestigationUsecase)                   │
│  backend/core/usecases/dispatch_investigation.py               │
│                                                                 │
│  1. Validate target (domain format)                            │
│  2. Get playbook definition (target_type + intensity)          │
│  3. Get modules to run: ["dns_intel", "whois_lookup", ...]    │
│  4. Verify all modules registered (IModuleRegistry)           │
│  5. Create Investigation domain object                        │
│  6. For each module:                                          │
│     - Create Task domain object                               │
│     - Enqueue via ITaskQueue.enqueue_task(module, payload)    │
│  7. Return response (investigation_id, modules, ws_url)      │
└─────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Domain Layer (Investigation, Task entities)                   │
│  backend/core/domain/investigation.py                          │
│                                                                 │
│  Investigation(                                               │
│    investigation_id="abc123",                                 │
│    target="example.com",                                      │
│    target_type="domain",                                      │
│    tasks=[                                                    │
│      Task(module="dns_intel", payload={...}),                 │
│      Task(module="whois_lookup", payload={...}),             │
│      ...                                                      │
│    ]                                                          │
│  )                                                            │
└─────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────────────────────────┐
│ Adapter Layer (ITaskQueue → CeleryAdapter)                     │
│  backend/adapters/task_queue/celery_adapter.py                 │
│                                                                 │
│  For each task:                                               │
│    sig = celery_app.signature("module.dns_intel")            │
│    result = sig.delay(payload={target: "example.com", ...})  │
│    → Returns task_id (for tracking)                          │
└─────────────────────┬────────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  Celery Worker         │
         │  Subprocess Isolation  │
         └─────────┬──────────────┘
                   │
        ┌──────────┼──────────────┐
        │          │              │
        ▼          ▼              ▼
    ┌────────┐ ┌────────┐ ┌─────────────┐
    │ Worker │ │ Worker │ │... Workers  │
    │ Process│ │ Process│ │             │
    └───┬────┘ └───┬────┘ └──────┬──────┘
        │          │             │
        └──────────┼─────────────┘
                   │
      ┌────────────┴────────────┐
      │ IModuleRegistry         │
      │ Load module by name     │
      │ Instantiate class       │
      │ Call execute()          │
      └──────────┬──────────────┘
                 │
        ┌────────┴────────┬────────────────┐
        ▼                 ▼                ▼
    ┌────────┐        ┌────────┐      ┌────────┐
    │DnsIntel│        │WhoIsLu │      │...     │
    │Module  │        │okup    │      │Modules │
    │        │        │        │      │        │
    │execute()│        │execute()│      │execute()│
    └───┬────┘        └───┬────┘      └───┬────┘
        │                 │               │
        ▼                 ▼               ▼
    ModuleResult      ModuleResult    ModuleResult
    {                 {               {
     success: true,    success: true,   success: false,
     data: {...},      data: {...},     error_code: "...",
     artifacts: [...]  artifacts: []    ...
    }                 }               }
        │                 │               │
        └─────────────────┼───────────────┘
                          │
                          ▼
              ┌──────────────────────┐
              │ Normalize results    │
              │ Extract artifacts    │
              │ Build STIX bundle    │
              └──────────┬───────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        ┌─────────────┐      ┌──────────────┐
        │Redis pub/sub│      │Neo4j graph   │
        │Publish event│      │Ingest bundle │
        │to channel   │      │Update graph  │
        └──────┬──────┘      └──────────────┘
               │
               ▼
        ┌──────────────────────┐
        │ Frontend WebSocket   │
        │ /ws/investigations/  │
        │ {investigation_id}   │
        │                      │
        │ Listen for events    │
        │ on Redis channel     │
        │                      │
        │ Update UI in         │
        │ real-time as         │
        │ modules complete     │
        └──────────────────────┘
```

---

## 3. Module Execution Flow

```
┌─────────────────────────────────────────────────────────┐
│ Old Way (Monolithic - 500+ LOC of hardcoding)           │
└─────────────────────────────────────────────────────────┘

1. run_module.py receives "dns_intel"
   ↓
2. if module_name == "dns_intel":  ← Hardcoded
3.     from backend.modules.dns_intel import dns_recon
4.     result = dns_recon(...)
5. elif module_name == "whois_lookup":  ← Hardcoded
   ...
   (60+ elif clauses!)
   ...
else:
    result = {"error": "Unknown module"}

Problem: Not DRY, hard to extend, no consistency


┌─────────────────────────────────────────────────────────┐
│ New Way (Clean Architecture - Auto-discovery)           │
└─────────────────────────────────────────────────────────┘

1. Startup: Module discovery
   ├─ Import backend/modules/dns/dns_intel.py
   ├─ @register_module decorator triggered
   ├─ Registry["dns_intel"] = (DnsIntelModule, metadata)
   ├─ Import backend/modules/whois/whois_lookup.py
   ├─ @register_module decorator triggered
   ├─ Registry["whois_lookup"] = (WhoisLookupModule, metadata)
   └─ ... (repeat for all 26 modules)

2. Runtime: Execute module
   ├─ task_queue.enqueue_task("dns_intel", payload)
   │   ├─ Get module: (cls, metadata) = registry.get_module("dns_intel")
   │   ├─ Instantiate: module = cls(config, logger)
   │   ├─ Execute: result = await module.execute(payload)
   │   ├─ Normalize: ModuleResult(...)
   │   └─ Return: result
   │
   ├─ task_queue.enqueue_task("whois_lookup", payload)
   │   ├─ Get module: (cls, metadata) = registry.get_module("whois_lookup")
   │   ├─ Instantiate: module = cls(config, logger)
   │   ├─ Execute: result = await module.execute(payload)
   │   └─ Return: result
   │
   └─ ... (repeat for all modules in parallel)

Benefit: Zero hardcoding, consistent interface, easy to test, extensible
```

---

## 4. Module Structure: Before vs After

```
┌─────────────────────────────────────────────────────────┐
│ BEFORE: Scattered, Inconsistent                          │
└─────────────────────────────────────────────────────────┘

api.py (400+ LOC)
├─ @app.post("/api/shodan")
│  └─ def api_shodan(req: ShodanRequest):
│     └─ t = task_shodan.delay(...)
│        └─ return {...}
├─ @app.post("/api/censys")
│  └─ def api_censys(req: CensysRequest):
│     └─ t = task_censys.delay(...)
│        └─ return {...}
└─ ... (26+ routes, all copy-paste)

tasks.py (300+ LOC)
├─ @celery_app.task
│  def task_shodan(...):
│     result = shodan_search(...)
├─ @celery_app.task
│  def task_censys(...):
│     result = censys_search(...)
└─ ... (26+ tasks, manually registered)

run_module.py (280+ LOC)
├─ if module_name == "shodan":
│  └─ from backend.modules.shodan import shodan_search
├─ elif module_name == "censys":
│  └─ from backend.modules.censys import censys_search
└─ ... (60+ elif clauses)

modules/dns_intel.py (80 LOC)
├─ def dns_recon(domain):
│  ├─ try:
│  │  └─ return {"success": True, ...}
│  └─ except Exception as e:
│     └─ return {"error": str(e), ...}

modules/whois_lookup.py (70 LOC)
├─ def whois_lookup(domain):
│  ├─ try:
│  │  └─ return {...}
│  └─ except Exception as e:
│     └─ return {"error": ..., ...}

Problem: No consistency, error handling all over the place, 500+ LOC of routing


┌─────────────────────────────────────────────────────────┐
│ AFTER: Clean, Consistent, Extensible                     │
└─────────────────────────────────────────────────────────┘

api/routes/v1/investigations.py (50 LOC)
├─ @router.post("/investigations")
│  └─ async def dispatch_investigation(req):
│     └─ result = await uc.execute(...)
│        └─ return DispatchInvestigationResponse(**result)
└─ All 26 modules handled by single endpoint!

modules/base.py (175 LOC)
├─ class BaseModule(ABC):
│  ├─ async def execute(payload) -> ModuleResult:
│  ├─ def _validate_payload(payload, required_keys):
│  ├─ def _create_result(...):
│  └─ def _run_sync(sync_fn):

modules/dns/dns_intel.py (216 LOC)
├─ @register_module(ModuleMetadata(
│  │  name="dns_intel",
│  │  display_name="DNS Intelligence",
│  │  ...
│  └─ ))
└─ class DnsIntelModule(BaseModule):
   ├─ async def execute(self, payload):
   │  ├─ self._validate_payload(payload, ["target"])
   │  ├─ result = await self._run_sync(self._dns_resolve, ...)
   │  └─ return self._create_result(success=True, ...)
   └─ def _dns_resolve(self, domain):
      └─ # Sync DNS resolution

modules/registry.py (135 LOC)
├─ _MODULE_REGISTRY = {}
├─ def register_module(metadata):
│  └─ decorator that adds to registry
├─ def get_module(name):
└─ def discover_modules(path):

Problem solved: 0 hardcoding, 100% consistency, 0 duplicate logic!
```

---

## 5. Dependency Injection Container

```
┌────────────────────────────────────────────────────────────┐
│ backend/container.py                                       │
└────────────────────────────────────────────────────────────┘

Container
├─ Settings (IConfig)
│  └─ Validates and loads config from env vars
│
├─ ModuleRegistry (IModuleRegistry)
│  ├─ PluginLoader discovers all modules
│  └─ Auto-registers all @register_module classes
│
├─ CeleryAdapter (ITaskQueue)
│  └─ Depends on: settings, module_registry
│
├─ RedisAdapter (IResultStore)
│  └─ Depends on: settings
│
├─ Neo4jAdapter (IStixGraph)
│  └─ Depends on: settings
│
├─ StructuredLogger (ILogger)
│  └─ Depends on: settings
│
├─ DispatchInvestigationUsecase
│  └─ Depends on: task_queue, module_registry, logger, settings
│
├─ GetInvestigationStatusUsecase
│  └─ Depends on: result_store, logger
│
└─ FastAPI Application
   └─ Depends on: all adapters and usecases


┌────────────────────────────────────────────────────────────┐
│ Usage in API Routes                                        │
└────────────────────────────────────────────────────────────┘

@app.post("/api/v1/investigations")
async def dispatch_investigation(
    req: DispatchInvestigationRequest,
    uc: DispatchInvestigationUsecase = Depends(get_dispatch_uc),
):
    # FastAPI injects the usecase via dependency injection
    # Usecase has all dependencies already wired
    result = await uc.execute(req.target, req.target_type, req.intensity)
    return result
```

---

## 6. Test Strategy

```
┌────────────────────────────────────────────────────────────┐
│ Unit Tests (Domain + Usecases)                             │
└────────────────────────────────────────────────────────────┘

tests/unit/domain/
├─ test_investigation.py
│  ├─ test_investigation_add_task()
│  ├─ test_investigation_mark_complete()
│  └─ test_investigation_get_stats()
├─ test_playbook.py
│  └─ test_playbook_get_modules_for_target()
└─ test_result.py
   └─ test_result_extract_artifacts()

tests/unit/usecases/
├─ test_dispatch_investigation.py
│  ├─ test_dispatch_validates_target()
│  ├─ test_dispatch_enqueues_all_modules()
│  └─ test_dispatch_returns_response()
└─ test_get_status.py

tests/unit/modules/
├─ test_dns_intel.py
│  ├─ test_dns_intel_successful()
│  ├─ test_dns_intel_invalid_payload()
│  └─ test_dns_intel_extracts_artifacts()
└─ test_*.py (26 modules total)

Benefits:
✓ Easy to mock: just mock ITaskQueue, ILogger, etc.
✓ No external services needed
✓ Fast: run in <1s
✓ Coverage: >80%


┌────────────────────────────────────────────────────────────┐
│ Integration Tests                                          │
└────────────────────────────────────────────────────────────┘

tests/integration/
├─ test_full_workflow.py
│  ├─ test_dispatch_and_collect_results()
│  └─ test_investigation_completion()
├─ test_api_endpoints.py
│  ├─ test_post_investigations()
│  ├─ test_get_modules()
│  └─ test_websocket_stream()
└─ test_adapters.py
   ├─ test_celery_adapter_enqueue()
   ├─ test_redis_adapter_store()
   └─ test_neo4j_adapter_ingest()

Requirements:
• Docker Compose with all services (Redis, Neo4j, PostgreSQL)
• Celery worker running
• ~5-10 minutes to run


┌────────────────────────────────────────────────────────────┐
│ Load Tests                                                 │
└────────────────────────────────────────────────────────────┘

tests/load/locustfile.py
├─ Simulate 100 concurrent users
├─ Each user dispatches investigations
├─ Measure:
│  ├─ Throughput: playbooks/min
│  ├─ Latency: p50, p95, p99
│  ├─ Error rate: %
│  └─ Resource usage: CPU, memory
└─ Goal: 60+ playbooks/min, <50ms p95 latency

Run: locust -f tests/load/locustfile.py -u 100 -r 10 --headless
```

---

## 7. Error Handling: Before vs After

```
┌─────────────────────────────────────────────────────────┐
│ BEFORE: Silent Failures                                  │
└─────────────────────────────────────────────────────────┘

# Typical module
def dns_recon(domain: str):
    try:
        resolver = dns.resolver.Resolver()
        answers = resolver.resolve(domain, "A")
        return {
            "success": True,
            "a_records": [str(rdata) for rdata in answers],
        }
    except Exception as e:  # ← Catches EVERYTHING
        return {
            "error": str(e),  # ← Loses exception type
            "success": False,
        }

# If error: {"error": "Some DNS error", "success": false}
# But which error? Timeout? NXDOMAIN? No parsing error?
# Silent in logs: no structured logging

Result: Debugging blind in production!


┌─────────────────────────────────────────────────────────┐
│ AFTER: Structured Error Handling                        │
└─────────────────────────────────────────────────────────┘

@register_module(...)
class DnsIntelModule(BaseModule):
    async def execute(self, payload) -> ModuleResult:
        try:
            validation_error = self._validate_payload(payload, ["target"])
            if validation_error:
                return validation_error  # StandardizedError
            
            target = payload["target"]
            self._log_info("Starting DNS resolution", target=target)
            
            # Run sync function in thread pool
            records = await self._run_sync(
                self._dns_resolve,
                target,
                timeout=10,
            )
            
            self._log_info("DNS resolution succeeded", records_count=len(records))
            
            return self._create_result(
                success=True,
                data={"records": records},
                artifacts=[...],
            )
        
        except asyncio.TimeoutError:
            self._log_error("DNS resolution timeout", target=target)
            return self._create_result(
                success=False,
                error_code="DNS_TIMEOUT",  # ← Specific error code!
                error_message="DNS lookup exceeded 10s timeout",
            )
        
        except dns.exception.DNSException as e:
            self._log_error("DNS exception", error_type=type(e).__name__)
            return self._create_result(
                success=False,
                error_code="DNS_LOOKUP_FAILED",  # ← Specific error code!
                error_message=f"DNS lookup failed: {str(e)[:100]}",
            )
        
        except Exception as e:
            self._log_error("Unexpected error", error_type=type(e).__name__)
            return self._create_result(
                success=False,
                error_code="INTERNAL_ERROR",
                error_message="Internal module error",
            )

Result:
✓ Structured logs: {"module": "dns_intel", "error_code": "DNS_TIMEOUT", ...}
✓ Metrics: task_failures_total{module="dns_intel", error_code="DNS_TIMEOUT"} = 10
✓ Debugging: grep logs by error_code, identify patterns
✓ Monitoring: Alert on error_code patterns
```

---

## 8. Deployment Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Blue-Green Deployment                       │
└────────────────────────────────────────────────────────────────┘

BLUE ENVIRONMENT (Current Production)
├─ API Servers (3 instances)
│  └─ Running old monolithic code
├─ Celery Workers (10 instances)
│  └─ Old hardcoded routing
├─ Redis, Neo4j, PostgreSQL
└─ Nginx routing ALL traffic here

       ↓ (Week 1-3: Develop + Test)

GREEN ENVIRONMENT (New Clean Architecture)
├─ API Servers (3 instances)
│  └─ Running new clean architecture code
├─ Celery Workers (10 instances)
│  └─ New plugin registry routing
├─ Redis, Neo4j, PostgreSQL (shared)
└─ Nginx routing ZERO traffic here

       ↓ (Week 4: Smoke Tests + Load Tests)

GRADUAL TRAFFIC SHIFT
Day 1:  Blue 100% / Green 0%
Day 2:  Blue 95%  / Green 5%  ← Monitor metrics
Day 3:  Blue 75%  / Green 25% ← Watch error rates
Day 4:  Blue 50%  / Green 50% ← Check latency
Day 5:  Blue 25%  / Green 75% ← Verify all OK
Day 6:  Blue 0%   / Green 100% ← New code is primary

       ↓ (Week 5: Monitoring + Stability Check)

KEEP BLUE AVAILABLE FOR 2 WEEKS
├─ If issues found: Rollback to Blue
├─ Monitor metrics: Throughput, Latency, Error rate
├─ Compare: Blue vs Green performance
└─ After 2 weeks: Decommission Blue


Rollback Plan:
─────────────
If error rate > 1% or latency > 100ms:
  1. Nginx: Route 100% traffic back to Blue
  2. Page on-call engineer
  3. Investigate issue
  4. Fix in feature branch
  5. Redeploy to Green
  6. Resume traffic shift
```

---

## 9. Key Files Map

```
Clean Architecture Implementation

backend/
├── core/                          ← Pure business logic (no framework)
│   ├── domain/                    ← Entities, rules, exceptions
│   │   ├── __init__.py
│   │   ├── investigation.py       ← Investigation, Task entities
│   │   ├── result.py              ← Result, Artifact entities
│   │   ├── playbook.py            ← Playbook definitions
│   │   └── errors.py              ← DomainError, specific exceptions
│   │
│   ├── ports/                     ← Interface contracts (Hexagonal)
│   │   ├── __init__.py
│   │   ├── task_queue.py          ← ITaskQueue interface
│   │   ├── module_registry.py     ← IModuleRegistry interface
│   │   ├── result_store.py        ← IResultStore interface
│   │   ├── stix_graph.py          ← IStixGraph interface
│   │   ├── logger.py              ← ILogger interface
│   │   └── config.py              ← IConfig interface
│   │
│   └── usecases/                  ← Application logic
│       ├── __init__.py
│       ├── dispatch_investigation.py  ← Main entry point usecase
│       ├── get_investigation_status.py
│       └── list_modules.py
│
├── adapters/                      ← Implementation of ports
│   ├── task_queue/
│   │   ├── __init__.py
│   │   ├── celery_adapter.py      ← Celery implementation
│   │   └── celery_config.py
│   ├── module_registry/
│   │   ├── __init__.py
│   │   ├── plugin_loader.py       ← Plugin discovery
│   │   └── registry.py
│   ├── result_store/
│   │   ├── __init__.py
│   │   └── redis_adapter.py       ← Redis implementation
│   ├── stix_graph/
│   │   ├── __init__.py
│   │   └── neo4j_adapter.py       ← Neo4j implementation
│   ├── logger/
│   │   ├── __init__.py
│   │   ├── structured_logger.py   ← Structured logging
│   │   └── metrics.py             ← Prometheus
│   └── config/
│       ├── __init__.py
│       └── settings.py            ← Settings validation
│
├── modules/                       ← OSINT module plugins
│   ├── __init__.py
│   ├── base.py                    ← BaseModule class
│   ├── registry.py                ← @register_module decorator
│   ├── dns_example.py             ← Reference implementation
│   ├── dns/
│   │   ├── __init__.py
│   │   ├── dns_intel.py           ← Refactored module
│   │   └── dns_bruteforce.py
│   ├── http/
│   │   ├── __init__.py
│   │   ├── deep_scraper.py
│   │   └── social_hunter.py
│   └── ... (more module categories)
│
├── api/                           ← FastAPI HTTP layer
│   ├── __init__.py
│   ├── main.py                    ← Create FastAPI app
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── investigations.py   ← POST /api/v1/investigations
│   │   │   ├── modules.py         ← GET /api/v1/modules
│   │   │   ├── status.py          ← GET /api/v1/investigations/{id}
│   │   │   └── websocket.py       ← WS /ws/investigations/{id}
│   │   └── health.py              ← GET /health, /ready
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── requests.py
│   │   └── responses.py
│   ├── middleware.py              ← Auth, CORS, tracing
│   ├── error_handlers.py          ← Exception handling
│   └── openapi_schemas.py         ← Auto docs
│
├── worker/                        ← Celery worker entry point
│   ├── __init__.py
│   ├── main.py                    ← Worker startup
│   ├── executor.py                ← Module execution
│   └── handlers.py                ← Task completion handlers
│
├── bin/                           ← CLI entry points
│   ├── __init__.py
│   ├── api.py                     ← python -m backend.bin.api
│   ├── worker.py                  ← python -m backend.bin.worker
│   ├── init_modules.py            ← Module discovery
│   └── health_check.py            ← Service health checks
│
├── __init__.py
├── config.py                      ← Global configuration
└── container.py                   ← Dependency injection container

tests/
├── unit/
│   ├── domain/
│   ├── usecases/
│   └── modules/
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_full_workflow.py
│   └── test_adapters.py
└── load/
    └── locustfile.py

docs/
├── CLEAN_ARCHITECTURE_DESIGN.md   ← Design blueprint (730 lines)
├── IMPLEMENTATION_GUIDE.md         ← Step-by-step (760 lines)
└── ARCHITECTURE_DIAGRAM.md         ← This file

OLD CODE (To Be Replaced)
├── api.py                         → backend/api/main.py + routes/
├── tasks.py                       → backend/adapters/task_queue/
├── run_module.py                  → backend/modules/registry.py
├── playbook.py                    → backend/core/domain/playbook.py
├── normalize.py                   → backend/api/response_formatters.py
└── modules/*                      → backend/modules/* (refactored)
```

---

This clean architecture diagram shows how all components fit together and how data flows through the system! 🏗️

