# Unified Enterprise OSINT Platform - Project Context

## Overview

Independent project building a Unified Enterprise OSINT Platform with a rigid, distributed backend and polyglot persistence strategy. Original source repos are in the root folder and will be deleted once the platform is complete.

## Architecture: Polyglot Persistence

| Store | Purpose | Port(s) |
|-------|---------|---------|
| **Redis** | Celery task broker (in-memory queue) | 6379 |
| **RabbitMQ** | Enterprise Pub/Sub event bus | 5672 (AMQP), 15672 (Mgmt UI) |
| **Neo4j** | Graph DB for relational STIX data | 7474 (HTTP), 7687 (Bolt) |
| **Weaviate** | Vector DB for unstructured/semantic data | 8080, 50051 |
| **PostgreSQL** | User configs, multi-tenant state, audit logs | 5432 |

## Project Structure

```
├── frontend/              # Next.js 15, React 18, TypeScript
│   └── src/app/           # Dashboard UI with OSINT tool forms
├── backend/               # FastAPI + Celery
│   ├── main.py            # FastAPI app, API routes, optional Celery dispatch
│   ├── celery_app.py      # Celery configuration (Redis broker)
│   ├── tasks.py           # Celery tasks for OSINT modules
│   └── modules/           # Extracted OSINT modules
├── docker-compose.yml     # Redis, RabbitMQ, Neo4j, Weaviate, PostgreSQL
├── .env.example           # Ports, dev passwords, API keys
└── context.md
```

## API Endpoints

| Method | Endpoint | Body |
|--------|----------|------|
| POST | `/api/shodan` | `{ "target": "1.2.3.4" or "example.com", "api_key": "optional" }` |
| POST | `/api/censys` | `{ "target": "1.2.3.4", "api_id": "optional", "api_secret": "optional" }` |
| POST | `/api/scrape` | `{ "urls": ["https://..."], "max_workers": 5 }` |
| POST | `/api/port-scan` | `{ "host": "example.com", "ports": [80,443], ... }` |
| GET | `/api/tasks/{task_id}` | Celery task result (when `USE_CELERY=true`) |

## Extracted Modules (backend/modules/)

| Module | Source | Methodology |
|--------|--------|-------------|
| `shodan_recon` | am0nt31r0/OSINT-Search | Shodan API (host/domain) |
| `censys_recon` | am0nt31r0/OSINT-Search | Censys API (IPv4, protocols, certs) |
| `scraper` | Hamed233/Digital-Footprint-OSINT-Tool | Multi-threaded scraping |
| `port_scanner` | Kcisti/bat-security-toolkit | TCP connect port scan |

## Celery Integration

- **Broker**: Redis (`REDIS_URL` / `CELERY_BROKER_URL`)
- **Behavior**: Set `USE_CELERY=true` to enqueue tasks; otherwise run synchronously.
- **Task result**: `GET /api/tasks/{task_id}` returns status and result when ready.

## Run

```bash
# 1. Copy env
cp .env.example .env

# 2. Start polyglot stack
docker compose up -d

# 3. Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# 4. Celery worker (optional, for async tasks)
cd backend && celery -A celery_app worker --loglevel=info

# 5. Frontend
cd frontend && npm install && npm run dev
```

## API Keys (Placeholders)

- **Shodan**: `SHODAN_API_KEY` in .env
- **Censys**: `CENSYS_API_ID`, `CENSYS_API_SECRET` in .env

Replace in production; never hardcode.

## Status

- [x] Project structure (frontend + backend)
- [x] backend/modules/ with Shodan, Censys, scraper, port_scanner
- [x] FastAPI routes
- [x] Celery integration (optional async dispatch)
- [x] Frontend dashboard UI
- [x] docker-compose.yml (Redis, RabbitMQ, Neo4j, Weaviate, PostgreSQL)
- [x] .env.example (ports, dev passwords)
- [ ] Wire Neo4j for STIX graph writes (planned)
- [ ] Wire Weaviate for vector embeddings (planned)
- [ ] Wire PostgreSQL for multi-tenant configs (planned)
- [ ] RabbitMQ Pub/Sub event handlers (planned)
- [ ] Remove original repo folders (after confirmation)

## Original Repos (Reference Only)

- am0nt31r0/OSINT-Search, Hamed233/Digital-Footprint-OSINT-Tool, Kcisti/bat-security-toolkit
- CyberNinja-main, Forensight-main, GraySentinel-main, TraceGraph-main, xRec0n-main
