# Unified Enterprise OSINT Platform - Project Context

## Overview

Independent project building a Unified Enterprise OSINT Platform with a rigid, distributed backend and polyglot persistence strategy. **Isolation-and-wrapper methodology**: FastAPI acts as command dispatcher and state manager; Celery workers execute OSINT modules via subprocess with strict timeouts. No direct execution in the FastAPI main thread.

## Architecture

### Command Dispatcher & Task Isolation

1. **FastAPI** – Command dispatcher and state manager. Receives requests, enqueues Celery tasks, exposes WebSocket for real-time stream. Does **not** run OSINT logic.
2. **Celery** – Consumes tasks from Redis. Each task uses `subprocess.Popen` to run `python -m run_module <module>`, isolating execution from the worker process.
3. **run_module.py** – CLI entry point. Reads JSON from stdin, invokes the appropriate module function, writes JSON result to stdout.
4. **Async capture** – Worker threads read stdout/stderr line-by-line, publish each chunk to Redis pub/sub.
5. **WebSocket** – FastAPI subscribes to Redis channel `osint:task:stream:{task_id}`, pushes chunks to the Next.js frontend in real time.
6. **Hard timeout** – `CELERY_TASK_HARD_TIMEOUT` (default 300s). On expiry, worker sends SIGKILL to the child process to reclaim resources.

### Polyglot Persistence

| Store | Purpose | Port(s) |
|-------|---------|---------|
| **Redis** | Celery broker + task stream pub/sub | 6379 |
| **RabbitMQ** | Enterprise Pub/Sub event bus | 5672 (AMQP), 15672 (Mgmt) |
| **Neo4j** | Graph DB for STIX data | 7474 (HTTP), 7687 (Bolt) |
| **Weaviate** | Vector DB (semantic search, GraySentinel) | 8080, 50051 |
| **PostgreSQL** | Configs, multi-tenant, audit logs | 5432 |

## Project Structure

```
├── frontend/              # Next.js 15, React 18, TypeScript, Tailwind, Radix UI
│   ├── src/app/           # layout, page (dashboard)
│   ├── src/components/    # Sidebar, Omnibar, GraphCanvas, NodeDetailPanel,
│   │                      # ResizableTerminal, MediaForensicsModal, ActivityTimelineModal
│   ├── src/lib/           # utils (cn)
│   └── src/styles/        # ansi.css for terminal colors
├── backend/
│   ├── main.py            # Dispatcher, WebSocket, no OSINT execution
│   ├── celery_app.py      # Celery config (Redis broker)
│   ├── tasks.py           # Subprocess wrapper, async capture, Redis pub, SIGKILL, temp config
│   ├── run_module.py      # CLI for subprocess (stdin JSON → stdout JSON, reads OSINT_CONFIG_FILE)
│   ├── config_injection.py# Dynamic, headless config injection (simulated Vault)
│   ├── stix_pipeline.py   # STIX 2.1 mapping helpers
│   ├── neo4j_client.py    # Minimal Neo4j ingestion client
│   ├── weaviate_client.py # Weaviate v4: schema, add_documents, semantic_search (cosine)
│   ├── semantic_search.py # Natural-language query → embed → Weaviate near_vector
│   ├── agents/            # LangGraph multi-agent (state, tools, nodes, graph)
│   └── modules/           # Self-contained OSINT modules (no repos dependency)
│       ├── graysentinel_pipeline.py # Scrape, chunk (by-title/similarity/context-aware), NER, embed, Weaviate
├── docker-compose.yml
├── .env.example
└── context.md
```

## API Endpoints

| Method | Endpoint | Body |
|--------|----------|------|
| POST | `/api/shodan` | `{ "target", "api_key"? }` |
| POST | `/api/censys` | `{ "target", "api_id"?,"api_secret"? }` |
| POST | `/api/scrape` | `{ "urls", "max_workers"? }` |
| POST | `/api/port-scan` | `{ "host", "ports"?,"max_workers"?,"timeout"? }` |
| POST | `/api/ingest` | `{ "urls", "strategies"? }` – GraySentinel pipeline, store in Weaviate |
| POST | `/api/semantic-search` | `{ "query", "limit"? }` – Natural-language → cosine similarity |
| POST | `/api/agent/investigate` | `{ "goal", "thread_id"? }` – LangGraph multi-agent investigation (memory-backed) |
| GET | `/api/tasks/{task_id}` | Poll task result |
| GET | `/api/graph` | Cytoscape elements (nodes/edges) from Neo4j |
| WebSocket | `/ws/task/{task_id}` | Real-time stdout/stderr stream |

## GraySentinel / Semantic Search

Traditional boolean search is insufficient for massive unstructured text (e.g. leaked forums, corporate docs). The GraySentinel methodology provides:

1. **Weaviate** – Vector DB with cosine similarity search.
2. **Extraction pipeline** (`modules/graysentinel_pipeline.py`) – Scrapes deep-web URLs (requests + BeautifulSoup), chunks text, extracts named entities, generates embeddings via sentence-transformers (`all-MiniLM-L6-v2`), stores in Weaviate.
3. **Chunking** – Three strategies: chunk-by-title (split on h1/h2/h3), similarity-based (sliding window with overlap), context-aware (paragraph-boundary aware).
4. **NER** – Metadata enrichment with regex-based extraction of emails, IPs, domains, phone numbers before embedding.
5. **Natural-language query** – POST `/api/semantic-search` embeds the query, performs `near_vector` cosine search, returns contextual documents with `content`, `source_url`, `chunk_strategy`, `named_entities`, `distance`.

## Multi-Agent Orchestration (LangGraph)

The system supports **autonomous, goal-directed agentic workflows** with multi-agent orchestration:

1. **LangGraph** – Stateful, graph-based framework. The graph is: `START → Orchestrator → (Searcher | Analyzer | Pentester) → Orchestrator → … → END`. Each sub-agent returns to the Orchestrator for routing.

2. **Four agent roles (zero-trust scoped tools)**  
   - **Searcher Agent** – Web lookups only. Allowed tools: `shodan_search`, `censys_search`, `scrape_urls`, `xrecon_search` (OSINT-Search + xRecon modules).  
   - **Analyzer Agent** – Semantic/threat only. Allowed tools: `semantic_search`, `graysentinel_ingest`, `score_threat` (GraySentinel semantic anomalies and threat risk scoring).  
   - **Pentester Agent** – Scanning only. Allowed tools: `port_scan`, `cyberninja_passive` (CyberNinja + bat-security-toolkit).  
   - **Orchestrator Agent** – No tools. Synthesizes results, triggers sub-agents via conditional edges, and produces STIX 2.1-compliant output.

3. **Memory** – Checkpoint memory (e.g. `MemorySaver` / `InMemorySaver`) persists state per `thread_id` so agents maintain context across multi-step investigation chains. Use the same `thread_id` to resume or continue an investigation.

4. **Zero-trust** – Sub-agents only receive and can only call their role-specific tools (see `backend/agents/tools/`). The Orchestrator never executes tools; it only routes and builds STIX.

5. **API** – POST `/api/agent/investigate` with `{ "goal": "natural language objective", "thread_id": "optional" }` runs the graph and returns `summary`, `threat_score`, `stix_bundle`, and `investigation_context`.

## Extracted Modules (backend/modules/)

| Module | Source | Invoked via |
|--------|--------|-------------|
| `shodan_recon` | am0nt31r0/OSINT-Search | `python -m run_module shodan_recon` |
| `censys_recon` | am0nt31r0/OSINT-Search | `python -m run_module censys_recon` |
| `scraper` | Hamed233/Digital-Footprint-OSINT-Tool | `python -m run_module scraper` |
| `port_scanner` | Kcisti/bat-security-toolkit | `python -m run_module port_scanner` |
| `cyberninja_passive` | Self-contained passive username enum | `python -m run_module cyberninja_passive` |
| `graysentinel_ingest` | GraySentinel methodology | `python -m run_module graysentinel_ingest` – scrape, chunk, NER, embed, Weaviate |
| `xrecon` | xRec0n-style | Stub in `modules/xrecon.py`; Searcher agent calls `xrecon_search` |

## Backend Agents (LangGraph)

| Component | Path | Description |
|-----------|------|-------------|
| State | `agents/state.py` | `OSINTAgentState`: goal, per-agent results, discovered_ips, threat_score, stix_bundle, investigation_context |
| Searcher tools | `agents/tools/searcher_tools.py` | shodan_search, censys_search, scrape_urls, xrecon_search |
| Analyzer tools | `agents/tools/analyzer_tools.py` | semantic_search, graysentinel_ingest, score_threat |
| Pentester tools | `agents/tools/pentester_tools.py` | port_scan, cyberninja_passive |
| Nodes | `agents/nodes.py` | searcher_node, analyzer_node, pentester_node, orchestrator_node |
| Graph | `agents/graph.py` | `build_osint_graph(use_memory=True)` with checkpoint memory |

## Run

```bash
cp .env.example .env
docker compose up -d

cd backend && pip install -r requirements.txt

# Terminal 1: FastAPI
uvicorn main:app --reload

# Terminal 2: Celery worker
celery -A celery_app worker --loglevel=info

cd frontend && npm install && npm run dev
```

## Environment

- `CELERY_TASK_HARD_TIMEOUT` – Seconds before SIGKILL (default 300)
- `CELERY_BROKER_URL` / `REDIS_URL` – Redis for Celery and pub/sub
- `VAULT_SHODAN_API_KEY` – Simulated encrypted Shodan key (used by config injection)
- `VAULT_CENSYS_API_ID` / `VAULT_CENSYS_API_SECRET` – Simulated encrypted Censys creds
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` – Neo4j connection for STIX ingestion
- `WEAVIATE_HTTP_URI` – Weaviate HTTP URL (default `http://localhost:8080`) for semantic search

## Frontend

Enterprise-grade UI built with Next.js 15, React 18, Tailwind CSS, Radix UI primitives, and Lucide icons. Dark-mode optimized (slate/zinc) with strategic neon accents: cyan for connections, amber for warnings, red for critical vulnerabilities.

### Layout & Components

1. **Global Navigation (Sidebar)** – Dashboard, Graph Explorer, Spatial Intelligence, Media Forensics, Reports, Secure Settings.
2. **Unified Omnibar** – Prominent target input (Email, Domain, IP, Phone) with workflow dropdown: Low (passive), Standard (Shodan/Censys/scrape), Aggressive (port scan + CyberNinja), Agent (LangGraph multi-agent).
3. **Main Canvas (Graph View)** – Interactive Cytoscape.js node/edge graph with:
   - Floating toolbar: Zoom in/out, Fit to view, Force-directed layout toggle, Leaf-prune switch
   - Vulnerability badges on server nodes (red border)
   - Node click → detail panel
4. **Progressive Disclosure Panel (Right)** – Slides out on node click; shows STIX 2.1 metadata, risk scores, entity resolution, keeping the canvas uncluttered.
5. **Resizable Virtual Terminal (Bottom)** – Drag handle to resize; ANSI colorization for live streaming logs.
6. **Media Forensics Modal** – Image forensics with interactive bounding boxes (faces: cyan, objects: amber).
7. **Activity Timeline Modal** – Chronological bar chart of network activity frequency.

### Design Principles

- Progressive disclosure: macro-level summary first, detail on demand
- Muted dark theme (slate-950, zinc) with cyan/amber/red accents for KPIs
- High information density without cognitive overload

## Status

- [x] FastAPI as command dispatcher (no direct OSINT execution)
- [x] Celery consumes from Redis
- [x] Subprocess wrapper (`run_module` + Popen)
- [x] Async stdout/stderr capture → Redis pub
- [x] WebSocket `/ws/task/{task_id}` → real-time stream
- [x] Hard timeout + SIGKILL on hang
- [x] Frontend dashboard (Next.js 15, sidebar, Omnibar, graph canvas)
- [x] Virtual terminal with ANSI colorization (resizable)
- [x] Cytoscape.js graph (floating toolbar, zoom, force-directed, leaf-prune, vulnerability badges)
- [x] GET `/api/graph` for Neo4j → Cytoscape
- [x] docker-compose, .env.example
- [x] Dynamic config injection (temp files, simulated Vault)
- [x] CyberNinja passive sandbox wrapper
- [x] STIX 2.1 mapping helpers + Neo4j client
- [x] Weaviate integration: schema (OSINTDocument), add_documents, semantic_search (cosine)
- [x] GraySentinel pipeline: scrape → chunk (by-title, similarity-based, context-aware) → NER → embed (sentence-transformers) → Weaviate
- [x] POST `/api/ingest`, POST `/api/semantic-search` – natural-language semantic search
- [x] LangGraph multi-agent orchestration (Searcher, Analyzer, Pentester, Orchestrator)
- [x] Checkpoint memory for multi-step investigation chains; zero-trust scoped tools per agent
- [x] POST `/api/agent/investigate` – goal-directed agentic workflow
- [x] Enterprise UI: Omnibar, NodeDetailPanel (STIX metadata), MediaForensicsModal, ActivityTimelineModal
- [ ] PostgreSQL wiring (planned)
- [ ] RabbitMQ Pub/Sub handlers (planned)

## Repos Purge – Green Light

**The `repos/` folder is 100% safe to delete.** No file in `backend/` or `frontend/` imports from, reads from, or references `repos/`. All methodologies (Shodan, Censys, port scan, scraper, CyberNinja passive, GraySentinel pipeline, xRecon stub) are fully self-contained in `backend/modules/`. The application will run correctly without `repos/`.

## Remaining Task Triage

See [ARCHITECTURE.md](./ARCHITECTURE.md) and [README.md](./README.md) for full documentation.

### PostgreSQL Wiring

- **Purpose**: Multi-tenant state, audit logs, config storage.
- **Scope**: Add `postgres_client.py`, connection from `WEAVIATE_*`-style env vars; schema for tenants, audit_events, configs.
- **Integration**: Config injection can optionally read from PostgreSQL; audit middleware logs requests to audit_events.

### RabbitMQ Pub/Sub Handlers

- **Purpose**: Enterprise event bus (alternative to Redis pub/sub for high-scale).
- **Scope**: Add RabbitMQ consumer for `osint.*` routing keys; optional bridge from Redis pub/sub to RabbitMQ for downstream consumers.
- **Integration**: Keep Redis for Celery and task stream; RabbitMQ for cross-service events (e.g. STIX bundle published, investigation complete).
