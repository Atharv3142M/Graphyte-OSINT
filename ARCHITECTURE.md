# Unified Enterprise OSINT Platform – Architecture

## 1. Isolation-and-Wrapper Methodology

The platform enforces strict isolation between the HTTP layer and OSINT execution:

1. **FastAPI** – Command dispatcher only. Receives requests, enqueues Celery tasks, exposes WebSocket. Does **not** execute OSINT logic.
2. **Celery** – Consumes tasks from Redis. Each task spawns a subprocess via `subprocess.Popen`.
3. **run_module.py** – CLI entry point. Reads JSON from stdin, invokes the appropriate module in `backend/modules/`, writes JSON to stdout.
4. **Subprocess isolation** – OSINT runs in a separate process. On timeout (`CELERY_TASK_HARD_TIMEOUT`), the worker sends SIGKILL.
5. **Config injection** – Sensitive credentials (Shodan, Censys) are materialized into ephemeral temp files via `config_injection.temporary_service_config()`; files are deleted after use.

### Data Flow: Task Execution

```
Next.js (fetch) → FastAPI POST /api/shodan
    → Celery task_shodan.delay()
    → Redis queue
    → Celery worker picks task
    → temporary_service_config("shodan") creates temp JSON
    → subprocess.Popen([python, "-m", "run_module", "shodan_recon"])
        → stdin: JSON payload
        → cwd: backend/
    → Worker threads read stdout/stderr line-by-line
    → Each line → redis.publish("osint:task:stream:{task_id}", json)
    → proc.wait() → parse final JSON from stdout
    → redis.publish(..., {"type": "result", "data": ...})
    → redis.publish(..., {"type": "done"})
```

### Data Flow: WebSocket Stream

```
Next.js WebSocket /ws/task/{task_id}
    → FastAPI subscribes to redis channel "osint:task:stream:{task_id}"
    → pubsub.get_message() in loop
    → On message → websocket.send_text(payload)
    → On {"type": "done"} → break, close
```

## 2. Polyglot Persistence Strategy

| Store | Purpose | Client |
|-------|---------|--------|
| **Redis** | Celery broker, task stream pub/sub | celery, redis |
| **RabbitMQ** | Enterprise event bus (planned) | - |
| **Neo4j** | STIX 2.1 graph (ipv4-addr, domain-name, network-traffic, note) | neo4j_client.py |
| **Weaviate** | Vector DB for semantic search (GraySentinel) | weaviate_client.py |
| **PostgreSQL** | Multi-tenant configs, audit logs (planned) | - |

### STIX 2.1 Data Model

`stix_pipeline.build_stix_bundle()` maps module outputs to STIX 2.1 objects:

- **shodan_recon** → `ipv4-addr` with `x_shodan_*` custom properties
- **port_scanner** → `network-traffic` with `x_open`, `x_host`
- **scraper** → `note` with emails/phones

Neo4j ingests these via `neo4j_client.ingest_bundle()` (when wired). The graph is exposed as Cytoscape-compatible elements via `GET /api/graph`.

### Weaviate Schema

Collection `OSINTDocument` with `Vectorizer.none()` (we provide vectors):

- `content` (TEXT)
- `source_url` (TEXT)
- `chunk_strategy` (TEXT)
- `named_entities` (TEXT_ARRAY)

Vectors from `sentence-transformers` (`all-MiniLM-L6-v2`).

## 3. LangGraph Multi-Agent Orchestration

### Graph Structure

```
START → orchestrator → (searcher | analyzer | pentester) → orchestrator → … → END
```

- **Orchestrator** – No tools. Routes to sub-agents, synthesizes results, builds STIX bundle.
- **Searcher** – Tools: `shodan_search`, `censys_search`, `scrape_urls`, `xrecon_search`
- **Analyzer** – Tools: `semantic_search`, `graysentinel_ingest`, `score_threat`
- **Pentester** – Tools: `port_scan`, `cyberninja_passive`

### Zero-Trust Tool Permissions

Each agent has access only to its scoped tools (`backend/agents/tools/`). The Orchestrator never executes tools.

### Memory

Checkpoint memory (`MemorySaver` / `InMemorySaver`) persists state per `thread_id`. Use the same `thread_id` to resume an investigation.

## 4. Module Inventory (backend/modules/)

| Module | Function | Self-contained |
|--------|----------|----------------|
| shodan_recon | shodan_search | Yes (shodan, validators) |
| censys_recon | censys_search | Yes (censys) |
| scraper | scrape_urls | Yes (requests, BeautifulSoup) |
| port_scanner | scan_ports | Yes (socket) |
| cyberninja_passive | cyberninja_passive | Yes (requests) |
| graysentinel_pipeline | run_pipeline | Yes (requests, sentence-transformers, weaviate_client) |
| xrecon | xrecon_search | Yes (stub) |

**No module imports from or references the `repos/` directory.** All logic is self-contained in `backend/modules/`.

## 5. Agent Tool Imports

All agent tools import from `backend/modules/` or top-level backend modules:

- `searcher_tools` → modules.shodan_recon, censys_recon, scraper, xrecon
- `analyzer_tools` → semantic_search, modules.graysentinel_pipeline
- `pentester_tools` → modules.port_scanner, modules.cyberninja_passive

## 6. Frontend Architecture (Phase 4)

### State Management — Zustand

All global investigation state lives in `frontend/src/store/useInvestigationStore.ts` (Zustand store). The store is the single source of truth for:

| Field | Type | Purpose |
|-------|------|---------|
| `currentTaskId` | `string \| null` | Active Celery task ID |
| `investigationStatus` | `InvestigationStatus` | `idle \| queued \| running \| done \| error` |
| `threadId` | `string \| null` | LangGraph thread (for agent mode) |
| `threatScore` | `number \| null` | Agent-assessed threat score |
| `orchestratorSummary` | `string \| null` | Agent synthesis summary |
| `streamLog` | `string[]` | Live terminal lines (ANSI-escaped) |
| `graphData` | `GraphData \| null` | STIX 2.1 nodes + edges from `GET /api/graph` |
| `selectedNode` | `NodeDetail \| null` | Currently selected graph node |
| `detailPanelOpen` | `boolean` | Node detail panel visibility |
| `pruneLeaves` | `boolean` | Graph prune toggle state |

### Centralized API Client

`frontend/src/lib/api.ts` provides a single typed interface to the backend:

- `investigate(goal, threadId?)` — POST `/api/agent/investigate` (LangGraph)
- `runModule(endpoint, body)` — POST to any `/api/*` Celery endpoint
- `fetchGraph()` — GET `/api/graph` → `GraphData`
- `getTaskStatus(taskId)` — GET `/api/tasks/{task_id}`
- `createTaskStream(taskId, onMessage, onDone, onError)` — WebSocket at `/ws/task/{task_id}`

All requests include the `X-Tenant-ID` header automatically.

### Data Flow: Investigation Pipeline

```
Omnibar (handleInvestigate)
  ├─ Agent mode:
  │   POST /api/agent/investigate
  │   → wait for response (synchronous LangGraph)
  │   → extract thread_id, threat_score, summary
  │   → GET /api/graph (refreshGraph)
  │
  └─ Celery mode (low/standard/aggressive):
      POST /api/{shodan,port-scan,...}
      → extract task_id
      → WebSocket /ws/task/{task_id}
          → stream stdout/stderr lines → appendLog
          → {"type": "done"} → setStatus("done") → refreshGraph
```

### STIX Graph Rendering

`GraphCanvas` uses Cytoscape 3 to render the graph:
- Loads from `store.graphData` (live) or `GET /api/graph` (fallback)
- Node type → color mapping via `TYPE_COLORS` (cyan=default, green=ipv4, purple=domain, amber=network-traffic, pink=note, red=server)
- Tap node → `openDetailPanel(node)` → right panel slides in
- Tap background → `closeDetailPanel()`
- Prune toggle removes degree ≤ 1 nodes (leaves)

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend HTTP base |
| `NEXT_PUBLIC_DEFAULT_TENANT_ID` | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` | Multi-tenant header value |
