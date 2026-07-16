# Clean Architecture Implementation Checklist

**Print this out and check off as you implement!**

---

## Phase 1: Foundation (2 Days)

### Directory Structure
- [ ] Create `backend/core/` directory
- [ ] Create `backend/core/domain/` directory
- [ ] Create `backend/core/ports/` directory
- [ ] Create `backend/core/usecases/` directory
- [ ] Create `backend/adapters/` directory
- [ ] Create `backend/adapters/task_queue/` directory
- [ ] Create `backend/adapters/module_registry/` directory
- [ ] Create `backend/adapters/result_store/` directory
- [ ] Create `backend/adapters/stix_graph/` directory
- [ ] Create `backend/adapters/logger/` directory
- [ ] Create `backend/adapters/config/` directory
- [ ] Create `backend/adapters/http/` directory
- [ ] Create `backend/api/` directory
- [ ] Create `backend/api/routes/v1/` directory
- [ ] Create `backend/api/schemas/` directory
- [ ] Create `backend/worker/` directory
- [ ] Create `backend/bin/` directory

### Domain Models
- [ ] Copy `backend/core/domain/__init__.py`
- [ ] Copy `backend/core/domain/investigation.py`
- [ ] Copy `backend/core/domain/result.py`
- [ ] Copy `backend/core/domain/playbook.py`
- [ ] Copy `backend/core/domain/errors.py`
- [ ] Review domain models with team
- [ ] Add any domain-specific extensions needed

### Port Interfaces
- [ ] Copy `backend/core/ports/__init__.py`
- [ ] Copy `backend/core/ports/task_queue.py`
- [ ] Copy `backend/core/ports/module_registry.py`
- [ ] Copy `backend/core/ports/result_store.py`
- [ ] Copy `backend/core/ports/stix_graph.py`
- [ ] Copy `backend/core/ports/logger.py`
- [ ] Copy `backend/core/ports/config.py`
- [ ] Review port interfaces with team
- [ ] Verify all methods are documented

### Module Framework
- [ ] Copy `backend/modules/base.py`
- [ ] Copy `backend/modules/registry.py`
- [ ] Copy `backend/modules/dns_example.py` as reference
- [ ] Test module registry discovery locally
- [ ] Verify @register_module decorator works
- [ ] Document module development guidelines

### Usecases
- [ ] Copy `backend/core/usecases/__init__.py`
- [ ] Copy `backend/core/usecases/dispatch_investigation.py`
- [ ] Review usecase logic with team
- [ ] Plan other usecases (GetStatus, ListModules, etc.)

### Testing
- [ ] Create `tests/unit/domain/` directory
- [ ] Create `tests/unit/usecases/` directory
- [ ] Create `tests/unit/modules/` directory
- [ ] Write domain model tests (Investigation, Task, Result)
- [ ] Write usecase tests (mock ports)
- [ ] Run tests locally: `pytest tests/unit/`
- [ ] Verify >80% coverage

---

## Phase 2: Adapters (2 Days)

### Task Queue Adapter (Celery)
- [ ] Create `backend/adapters/task_queue/celery_adapter.py`
- [ ] Implement ITaskQueue interface:
  - [ ] `enqueue_task(module_name, payload, task_id) -> task_id`
  - [ ] `get_task_status(task_id) -> TaskInfo`
  - [ ] `cancel_task(task_id) -> bool`
  - [ ] `wait_for_completion(task_id, timeout) -> TaskInfo`
- [ ] Implement dynamic task registration (one per module)
- [ ] Test locally with mock modules
- [ ] Handle timeouts and errors

### Module Registry Adapter
- [ ] Create `backend/adapters/module_registry/plugin_loader.py`
- [ ] Implement IModuleRegistry interface:
  - [ ] `register(name, class, metadata)`
  - [ ] `get_module(name) -> (class, metadata)`
  - [ ] `list_modules() -> [(name, metadata), ...]`
  - [ ] `discover_modules(path) -> count`
  - [ ] `is_module_registered(name) -> bool`
- [ ] Test module discovery on all modules
- [ ] Verify auto-import triggering decorators
- [ ] Generate module inventory

### Result Store Adapter (Redis)
- [ ] Create `backend/adapters/result_store/redis_adapter.py`
- [ ] Implement IResultStore interface:
  - [ ] `store_result(investigation_id, task_id, result)`
  - [ ] `get_result(investigation_id, task_id) -> Optional[dict]`
  - [ ] `get_all_results(investigation_id) -> Dict`
  - [ ] `delete_results(investigation_id)`
  - [ ] `publish_event(channel, event_type, payload)`
  - [ ] `subscribe_to_channel(channel) -> AsyncIterator`
- [ ] Test Redis connectivity
- [ ] Test pub/sub functionality
- [ ] Handle connection errors

### STIX Graph Adapter (Neo4j)
- [ ] Create `backend/adapters/stix_graph/neo4j_adapter.py`
- [ ] Implement IStixGraph interface:
  - [ ] `ingest_bundle(investigation_id, bundle)`
  - [ ] `resolve_entity(entity_type, value) -> Optional[dict]`
  - [ ] `get_entity_relationships(entity_id) -> List[dict]`
  - [ ] `get_investigation_subgraph(investigation_id) -> dict`
  - [ ] `health_check() -> bool`
- [ ] Test Neo4j connectivity
- [ ] Test STIX bundle ingestion
- [ ] Handle connection errors

### Logger Adapter
- [ ] Create `backend/adapters/logger/structured_logger.py`
- [ ] Implement ILogger interface:
  - [ ] `log(level, message, **kwargs)`
  - [ ] `debug(message, **kwargs)`
  - [ ] `info(message, **kwargs)`
  - [ ] `warning(message, **kwargs)`
  - [ ] `error(message, **kwargs)`
  - [ ] `critical(message, **kwargs)`
  - [ ] `record_metric(name, value, labels)`
  - [ ] `start_span(name, attributes) -> Span`
- [ ] Configure structlog for JSON output
- [ ] Setup Prometheus metrics
- [ ] Setup OpenTelemetry tracing

### Config Adapter
- [ ] Create `backend/adapters/config/settings.py`
- [ ] Implement IConfig interface:
  - [ ] `get_environment() -> Environment`
  - [ ] `is_debug() -> bool`
  - [ ] All service URLs (Redis, Neo4j, PostgreSQL, etc.)
  - [ ] JWT configuration
  - [ ] CORS origins
  - [ ] Module timeouts
- [ ] Add pydantic-settings for validation
- [ ] Implement `validate() -> List[str]`
- [ ] Implement `health_check() -> Dict[service -> bool]`
- [ ] Test validation with invalid config

### Dependency Injection Container
- [ ] Create `backend/container.py`
- [ ] Define all adapters as singletons
- [ ] Wire up dependencies:
  - [ ] Settings (required for all)
  - [ ] ModuleRegistry (depends on PluginLoader)
  - [ ] CeleryAdapter (depends on Settings, ModuleRegistry)
  - [ ] RedisAdapter (depends on Settings)
  - [ ] Neo4jAdapter (depends on Settings)
  - [ ] StructuredLogger (depends on Settings)
  - [ ] Usecases (depend on adapters)
- [ ] Test container initialization

### Integration Tests
- [ ] Create `tests/integration/test_adapters.py`
- [ ] Test CeleryAdapter with real Celery
- [ ] Test RedisAdapter with real Redis
- [ ] Test Neo4jAdapter with real Neo4j
- [ ] Test StructuredLogger output format
- [ ] Test Settings validation
- [ ] Run: `pytest tests/integration/`

---

## Phase 3: API Layer (1 Day)

### API Schema & Models
- [ ] Create `backend/api/schemas/requests.py`
  - [ ] DispatchInvestigationRequest
  - [ ] GetInvestigationStatusRequest
  - [ ] ListModulesRequest
- [ ] Create `backend/api/schemas/responses.py`
  - [ ] DispatchInvestigationResponse
  - [ ] GetInvestigationStatusResponse
  - [ ] ListModulesResponse
  - [ ] ErrorResponse
- [ ] Add request/response validation
- [ ] Add OpenAPI documentation

### API Routes (v1)
- [ ] Create `backend/api/routes/v1/investigations.py`
  - [ ] `POST /api/v1/investigations` (dispatch)
  - [ ] `GET /api/v1/investigations/{id}` (get status)
  - [ ] `GET /api/v1/investigations` (list)
- [ ] Create `backend/api/routes/v1/modules.py`
  - [ ] `GET /api/v1/modules` (list all modules)
  - [ ] `GET /api/v1/modules/{name}` (get module details)
- [ ] Create `backend/api/routes/v1/websocket.py`
  - [ ] `WS /ws/investigations/{id}` (real-time stream)
- [ ] Create `backend/api/routes/health.py`
  - [ ] `GET /health` (simple health check)
  - [ ] `GET /ready` (readiness check)

### HTTP Adapters
- [ ] Create `backend/api/middleware.py`
  - [ ] Auth middleware (JWT validation)
  - [ ] CORS middleware
  - [ ] Request logging middleware
  - [ ] Tracing middleware (correlation ID)
- [ ] Create `backend/api/error_handlers.py`
  - [ ] Handle DomainError exceptions
  - [ ] Return standardized error responses
  - [ ] Log errors with error codes
- [ ] Create `backend/api/response_formatters.py`
  - [ ] Format investigation responses
  - [ ] Format module listings
  - [ ] Format error responses

### FastAPI Application
- [ ] Create `backend/api/main.py`
  - [ ] Create FastAPI app
  - [ ] Register middleware
  - [ ] Register error handlers
  - [ ] Register routes
  - [ ] Configure CORS
  - [ ] Setup OpenAPI documentation
  - [ ] Setup health check endpoint
  - [ ] Create `/api/v1` router prefix
- [ ] Test API locally: `uvicorn backend.api.main:app`

### API Tests
- [ ] Create `tests/integration/test_api_endpoints.py`
  - [ ] Test POST /api/v1/investigations
  - [ ] Test GET /api/v1/investigations/{id}
  - [ ] Test GET /api/v1/modules
  - [ ] Test WS /ws/investigations/{id}
  - [ ] Test error responses
  - [ ] Test authentication
- [ ] Run: `pytest tests/integration/test_api_endpoints.py`

---

## Phase 4: Module Migration (3 Days)

### Audit Existing Modules
- [ ] List all 26 modules
- [ ] Categorize by type (dns, http, graph, etc.)
- [ ] Identify dependencies for each module
- [ ] Identify error patterns for each module
- [ ] Plan execution order (simplest first)

### Convert Each Module to New Pattern

For each of the 26 modules:

- [ ] Copy template from `dns_example.py`
- [ ] Replace module-specific logic
- [ ] Add ModuleMetadata (name, display_name, category, timeout)
- [ ] Implement async execute(payload) -> ModuleResult
- [ ] Add input validation (required fields)
- [ ] Extract artifacts from results
- [ ] Add error handling with specific error codes
- [ ] Add structured logging
- [ ] Test module locally
- [ ] Add module-specific unit tests
- [ ] Verify module appears in registry

### Module Organization
- [ ] Group modules by namespace:
  - [ ] `backend/modules/dns/` (dns_intel, dns_bruteforce)
  - [ ] `backend/modules/http/` (deep_scraper, social_hunter)
  - [ ] `backend/modules/graph/` (entity_resolution, relationship_map)
  - [ ] `backend/modules/verification/` (screenshot_capture, ssl_verify)
  - [ ] etc.
- [ ] Each namespace has `__init__.py` and `module.py`
- [ ] Each module imports `base.py` and `registry.py`

### Module Testing
- [ ] Unit tests for each module:
  - [ ] Test successful execution
  - [ ] Test error handling
  - [ ] Test artifact extraction
  - [ ] Test input validation
- [ ] Integration tests:
  - [ ] Test with real services (DNS, HTTP, etc.)
  - [ ] Test with mocked services
  - [ ] Test timeout handling
- [ ] Coverage: >80% per module

### Backward Compatibility
- [ ] Keep old module files temporarily
- [ ] Run side-by-side tests (old vs new)
- [ ] Compare results (should be identical)
- [ ] Verify no breaking changes
- [ ] Document any behavior changes

---

## Phase 5: Testing & Quality (2 Days)

### Unit Tests
- [ ] Domain models: 100% coverage
  - [ ] `tests/unit/domain/test_investigation.py`
  - [ ] `tests/unit/domain/test_result.py`
  - [ ] `tests/unit/domain/test_playbook.py`
- [ ] Usecases: >80% coverage
  - [ ] `tests/unit/usecases/test_dispatch_investigation.py`
  - [ ] `tests/unit/usecases/test_get_status.py`
  - [ ] `tests/unit/usecases/test_list_modules.py`
- [ ] Modules: >80% coverage (each module)
  - [ ] `tests/unit/modules/test_dns_intel.py`
  - [ ] `tests/unit/modules/test_whois_lookup.py`
  - [ ] etc. (for all 26 modules)
- [ ] Run: `pytest tests/unit/ --cov=backend/core --cov=backend/modules`
- [ ] Target: 80%+ overall coverage

### Integration Tests
- [ ] Full workflow tests
  - [ ] `tests/integration/test_full_workflow.py`
  - [ ] Dispatch → Execute → Collect → Return
  - [ ] Verify STIX ingestion
  - [ ] Verify WebSocket streaming
- [ ] API endpoint tests
  - [ ] `tests/integration/test_api_endpoints.py`
  - [ ] Test all HTTP routes
  - [ ] Test error responses
  - [ ] Test WebSocket handshake
- [ ] Adapter tests
  - [ ] `tests/integration/test_adapters.py`
  - [ ] Test with real services
  - [ ] Test error handling
  - [ ] Test timeouts
- [ ] Run: `pytest tests/integration/ --timeout=300`

### Load Tests
- [ ] Create `tests/load/locustfile.py`
- [ ] Simulate 100 concurrent users
- [ ] Each user dispatches investigations
- [ ] Measure:
  - [ ] Throughput: playbooks/minute
  - [ ] Latency: p50, p95, p99
  - [ ] Error rate: %
  - [ ] Resource usage: CPU, memory
- [ ] Goals:
  - [ ] 60+ playbooks/minute
  - [ ] <50ms p95 latency
  - [ ] <1% error rate
  - [ ] CPU usage <70%
- [ ] Run: `locust -f tests/load/locustfile.py -u 100 -r 10`

### Code Quality
- [ ] Type checking: `mypy backend/`
  - [ ] 0 type errors
  - [ ] 100% type hints
- [ ] Linting: `pylint backend/`
  - [ ] Score >8/10
  - [ ] No major issues
- [ ] Code style: `black backend/`
  - [ ] All files formatted
  - [ ] Consistent style
- [ ] Security: `bandit -r backend/`
  - [ ] No critical issues
  - [ ] Review warnings

### Documentation
- [ ] API documentation (OpenAPI/Swagger)
  - [ ] All endpoints documented
  - [ ] Request/response examples
  - [ ] Error codes documented
- [ ] Module development guide
  - [ ] How to create a new module
  - [ ] Template module provided
  - [ ] Examples for each pattern
- [ ] Architecture documentation
  - [ ] Layers explained
  - [ ] Data flows documented
  - [ ] Deployment procedures documented
- [ ] Deployment guide
  - [ ] Pre-deployment checklist
  - [ ] Deployment steps
  - [ ] Rollback procedures
  - [ ] Monitoring setup

---

## Phase 6: Deployment (1 Day)

### Pre-Deployment
- [ ] All tests passing: `pytest tests/`
- [ ] Load test targets met
- [ ] Code quality targets met
- [ ] Documentation complete
- [ ] Team training completed
- [ ] Runbook created
- [ ] Rollback plan documented

### Blue-Green Setup
- [ ] Blue environment (current production)
  - [ ] Running old monolithic code
  - [ ] All traffic routed here
- [ ] Green environment (new clean architecture)
  - [ ] Running new code
  - [ ] No traffic yet
- [ ] Load balancer configured
  - [ ] Can route to Blue or Green
  - [ ] Health checks configured
  - [ ] Graceful drain configured

### Smoke Tests
- [ ] Deploy Green environment
- [ ] Run smoke tests:
  - [ ] `curl http://green-api:8000/health`
  - [ ] `POST /api/v1/investigations` with test target
  - [ ] `GET /api/v1/modules` returns all modules
  - [ ] `WS /ws/investigations/{id}` connects
  - [ ] All 26 modules available
- [ ] Verify results match Blue environment

### Gradual Traffic Shift
- [ ] Day 1: Blue 100% / Green 0%
  - [ ] Monitor: No changes
- [ ] Day 2: Blue 95% / Green 5%
  - [ ] Monitor: Error rates, latency
  - [ ] Verify metrics match
- [ ] Day 3: Blue 75% / Green 25%
  - [ ] Monitor: Increase load on Green
  - [ ] Watch for resource issues
- [ ] Day 4: Blue 50% / Green 50%
  - [ ] Monitor: Equal load
  - [ ] Verify performance
- [ ] Day 5: Blue 25% / Green 75%
  - [ ] Monitor: Green under heavy load
  - [ ] Watch for issues
- [ ] Day 6: Blue 0% / Green 100%
  - [ ] New code is primary
  - [ ] Keep Blue available for rollback

### Monitoring & Alerts
- [ ] Setup Prometheus dashboards
  - [ ] Task throughput (playbooks/min)
  - [ ] Task latency (p50, p95, p99)
  - [ ] Error rates by module
  - [ ] Module execution times
  - [ ] Service availability
- [ ] Setup alert rules
  - [ ] Alert if error rate > 1%
  - [ ] Alert if p95 latency > 100ms
  - [ ] Alert if throughput < 50 playbooks/min
  - [ ] Alert if any service unavailable
- [ ] Configure logging
  - [ ] Centralized log collection
  - [ ] Structured log parsing
  - [ ] Alert on error codes

### Post-Deployment
- [ ] Monitor for 24 hours
  - [ ] Watch error rates
  - [ ] Watch latency
  - [ ] Watch resource usage
- [ ] Collect metrics
  - [ ] Compare Blue vs Green
  - [ ] Verify improvements
  - [ ] Document results
- [ ] After 2 weeks (if stable):
  - [ ] Decommission Blue environment
  - [ ] Archive old code
  - [ ] Update documentation
- [ ] If issues found (any time):
  - [ ] Rollback: Route 100% traffic to Blue
  - [ ] Investigate issue
  - [ ] Fix in development
  - [ ] Test again
  - [ ] Redeploy to Green

---

## Post-Deployment Validation

### Performance Verification
- [ ] Throughput: 60+ playbooks/min (was 20)
  - [ ] Measurement: Monitor metrics
  - [ ] Success: ✅ if > 60 playbooks/min
- [ ] Latency: <30s p95 (was 50-100s)
  - [ ] Measurement: Monitor metrics
  - [ ] Success: ✅ if p95 < 30s
- [ ] Error visibility: 100% observable
  - [ ] Measurement: Review logs
  - [ ] Success: ✅ if all errors logged with error_code
- [ ] Module consistency: All use BaseModule
  - [ ] Measurement: Module registry
  - [ ] Success: ✅ if all 26 modules registered

### Team Readiness
- [ ] Team trained on clean architecture
  - [ ] All developers reviewed CLEAN_ARCHITECTURE_DESIGN.md
  - [ ] All developers reviewed IMPLEMENTATION_GUIDE.md
  - [ ] All developers reviewed dns_example.py
- [ ] Team can add new modules
  - [ ] Developer creates new module in 30 minutes
  - [ ] Module passes tests
  - [ ] Module auto-discovered
- [ ] Support team can debug
  - [ ] Can find errors in logs
  - [ ] Can trace requests
  - [ ] Can identify slow modules

### Documentation Complete
- [ ] Architecture documented
  - [ ] Layers explained
  - [ ] Data flows documented
  - [ ] Decisions recorded
- [ ] API documented
  - [ ] Endpoints listed
  - [ ] Request/response examples
  - [ ] Error codes documented
- [ ] Module development documented
  - [ ] How to create module
  - [ ] Template provided
  - [ ] Examples for each pattern
- [ ] Deployment documented
  - [ ] Setup procedures
  - [ ] Deployment steps
  - [ ] Rollback procedures
  - [ ] Monitoring setup

---

## Final Checklist

- [ ] All phases completed
- [ ] All tests passing
- [ ] All documentation complete
- [ ] Team trained
- [ ] Production deployed
- [ ] Metrics monitored
- [ ] Performance verified
- [ ] No rollbacks needed
- [ ] Legacy code archived
- [ ] Success metrics met:
  - [ ] 3x throughput improvement
  - [ ] 3x latency improvement
  - [ ] 100% error visibility
  - [ ] 30-minute module setup time
  - [ ] >80% test coverage
  - [ ] 99.9% uptime

---

## Success! 🎉

Your Graphyte codebase is now production-grade, scalable, and maintainable using clean architecture principles.

**Next:** Celebrate with your team and start building new OSINT capabilities with confidence! 🚀

