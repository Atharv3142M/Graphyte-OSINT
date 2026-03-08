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
| **Weaviate** | Vector DB | 8080, 50051 |
| **PostgreSQL** | Configs, multi-tenant, audit logs | 5432 |

## Project Structure

```
├── frontend/              # Next.js 15, React 18, TypeScript
│   ├── src/app/           # Dashboard layout, page
│   ├── src/components/    # VirtualTerminal (ANSI), StixGraph (Cytoscape)
│   └── src/styles/        # ansi.css for terminal colors
├── backend/
│   ├── main.py            # Dispatcher, WebSocket, no OSINT execution
│   ├── celery_app.py      # Celery config (Redis broker)
│   ├── tasks.py           # Subprocess wrapper, async capture, Redis pub, SIGKILL, temp config
│   ├── run_module.py      # CLI for subprocess (stdin JSON → stdout JSON, reads OSINT_CONFIG_FILE)
│   ├── config_injection.py# Dynamic, headless config injection (simulated Vault)
│   ├── stix_pipeline.py   # STIX 2.1 mapping helpers
│   ├── neo4j_client.py    # Minimal Neo4j ingestion client
│   └── modules/           # Extracted OSINT modules (invoked via subprocess)
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
| GET | `/api/tasks/{task_id}` | Poll task result |
| GET | `/api/graph` | Cytoscape elements (nodes/edges) from Neo4j |
| WebSocket | `/ws/task/{task_id}` | Real-time stdout/stderr stream |

## Extracted Modules (backend/modules/)

| Module | Source | Invoked via |
|--------|--------|-------------|
| `shodan_recon` | am0nt31r0/OSINT-Search | `python -m run_module shodan_recon` |
| `censys_recon` | am0nt31r0/OSINT-Search | `python -m run_module censys_recon` |
| `scraper` | Hamed233/Digital-Footprint-OSINT-Tool | `python -m run_module scraper` |
| `port_scanner` | Kcisti/bat-security-toolkit | `python -m run_module port_scanner` |
| `cyberninja_passive` | CyberNinja-main (sandboxed) | `python -m run_module cyberninja_passive` |

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

## Frontend

- **Dashboard** – Sidebar tools, tabbed panels (Terminal | Graph | Result)
- **VirtualTerminal** – ANSI escape code parsing (anser) for colorized logs; listens to WebSocket
- **StixGraph** – Cytoscape.js canvas renderer (GPU-composited) for large graphs; leaf-prune toggle to hide leaf nodes and reduce cognitive load
- **UI/UX** – Tailwind, responsive layout, clear affordances

## Status

- [x] FastAPI as command dispatcher (no direct OSINT execution)
- [x] Celery consumes from Redis
- [x] Subprocess wrapper (`run_module` + Popen)
- [x] Async stdout/stderr capture → Redis pub
- [x] WebSocket `/ws/task/{task_id}` → real-time stream
- [x] Hard timeout + SIGKILL on hang
- [x] Frontend dashboard (Next.js 15, sidebar, tabs)
- [x] Virtual terminal with ANSI colorization
- [x] Cytoscape.js graph visualization (canvas, leaf-prune toggle)
- [x] GET `/api/graph` for Neo4j → Cytoscape
- [x] docker-compose, .env.example
- [x] Dynamic config injection (temp files, simulated Vault)
- [x] CyberNinja passive sandbox wrapper
- [x] STIX 2.1 mapping helpers + Neo4j client
- [ ] Weaviate/PostgreSQL wiring (planned)
- [ ] RabbitMQ Pub/Sub handlers (planned)
- [ ] Remove original repo folders (after confirmation)
