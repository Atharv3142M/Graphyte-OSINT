# Architecture

## High-level system

```
┌─────────────────────────────────────────────────────────────────┐
│  Next.js 15 Frontend                                            │
│  /dashboard (Omnibar + InlineResults)  /workspace (Graph+Term)  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST + WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│  FastAPI (backend/api.py)                                       │
│  Validation · SSRF guard · Playbook dispatch · Task polling       │
└────────────────────────────┬────────────────────────────────────┘
                             │ Celery enqueue
┌────────────────────────────▼────────────────────────────────────┐
│  Celery Worker (backend/tasks.py)                                 │
│  subprocess → run_module.py → normalize → Redis pub/sub + STIX    │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       │                  │                  │
   Redis 6379        Neo4j 7687        PostgreSQL 5432
   pub/sub + broker   STIX graph        tenants / audit
       │
   RabbitMQ (audit events)
   Weaviate (semantic search)
```

## Core data flow

1. User submits a target from the **dashboard Omnibar** or a single module from **Tools**.
2. FastAPI validates input (SSRF policy, rate limits) and enqueues one or more Celery tasks.
3. The worker spawns `python -m backend.run_module <name>` with JSON on stdin.
4. **stdout** receives exactly one JSON line; all logs/prints go to **stderr**.
5. `normalize_result()` wraps raw output in the UI envelope.
6. The envelope is published to Redis (`osint:task:stream:{task_id}`) and returned as the Celery result.
7. The frontend WebSocket (or poll fallback) receives `result` + `done` events.
8. On success, `stix_pipeline.build_stix_bundle()` ingests objects into Neo4j.

## Subprocess contract (`backend/run_module.py`)

| Stream | Content |
|--------|---------|
| **stdout** | Single line: valid JSON module result |
| **stderr** | Logs, tracebacks, third-party `print()` output |

Implementation details:

- Module execution runs inside `_redirect_stdout_to_stderr()` so stray prints cannot corrupt stdout.
- `tasks._spawn_and_stream()` scans stdout lines **from the end** for the first parseable JSON object.
- Failures always produce a normalized envelope with `ok: false` and populated `errors[]`.

## Normalized envelope (`backend/normalize.py`)

Every task result — success or failure — is shaped as:

```
{ ok, module, summary, artifacts, tables, raw, errors }
```

- **artifacts** — regex extraction of IPs, domains, URLs, emails, usernames, ASNs from raw JSON
- **tables** — auto-built from `list[dict]` fields (e.g. `sources`, `sitemap_urls`, `repositories`, `permutations`)
- **errors** — structured codes (`missing_api_key`, `timeout`, `ssrf_blocked`, etc.)

The smoke classifier (`backend/scripts/module_smoke.py`) checks `ok` and `errors[]`, not the legacy `error` key on raw dicts.

## Playbook routing (`backend/playbook.py`)

`POST /api/investigate` uses `ROUTING_MAP` to select modules by detected input type:

| Type | Example modules |
|------|-----------------|
| `domain` | DNS, WHOIS, SSL, HTTP security, tech stack, CT, robots/sitemap, favicon, xRecon, wayback, geo, reverse IP |
| `username` | Permutator, GitHub, social hunter, Sherlock, xRecon, CyberNinja |
| `email` | Email reputation, permutator (local-part), social hunter, CT, xRecon |
| `phone` | Phone intel, xRecon, CyberNinja |
| `ipv4` | DNS, port scan, Shodan, Censys, geo, reverse IP, BGP, … |

**Intensity** filters modules:

- `low` — excludes port scan, deep scraper, Shodan, Censys, social hunter, Sherlock, GraySentinel
- `standard` — default full routing
- `aggressive` — same as standard (reserved for future expansion)

## Backend components

| File | Role |
|------|------|
| `api.py` | REST routes, WebSocket streams, playbook dispatch |
| `tasks.py` | Celery tasks, subprocess streaming, STIX ingestion trigger |
| `run_module.py` | Subprocess CLI router for all modules |
| `normalize.py` | UI envelope generation |
| `playbook.py` | Type → module routing matrix |
| `stix_pipeline.py` | Module result → STIX 2.1 bundle |
| `neo4j_client.py` | Graph ingest and `/api/graph` queries |
| `config_injection.py` | Ephemeral credential files for Shodan/Censys/GitHub |
| `celery_app.py` | Celery application config |
| `modules/*.py` | Isolated OSINT implementations (26 modules) |

## Frontend architecture

### Pages (App Router)

| Route | Components | Audience |
|-------|------------|----------|
| `/dashboard` | `Omnibar`, `InlineResults` | Default — beginners |
| `/workspace` | `GraphCanvas`, `GlobalTerminal`, `ResultPanel` | Advanced analysts |
| `/tools` | `ModuleCards` | Per-module ad-hoc runs |
| `/reports`, `/settings` | Report export, env keys | Operations |

### State & API

- `useInvestigationStore` (Zustand) — playbook results, graph data, terminal logs
- `lib/api.ts` — HTTP client with multi-port fallback (8000, 8001, host variants)
- `lib/classifier.ts` — target type detection for Omnibar
- `createPlaybookStream()` — multiplexed WebSocket per investigation

### Result rendering

- **InlineResults** / **ResultPanel** — summary stats and tables first; artifacts and raw JSON behind Radix accordions
- Errors surfaced prominently with hints from `errors[].hint`

## Persistence

| Store | Usage |
|-------|--------|
| **Redis** | Celery broker, result backend, task/playbook pub/sub channels, playbook plan hash |
| **Neo4j** | STIX object graph for `GraphCanvas` |
| **PostgreSQL** | Multi-tenant configs, audit events |
| **Weaviate** | Semantic search / GraySentinel vectors |
| **RabbitMQ** | `osint.*` audit event fan-out |

## Reliability behaviors

- Hard task timeout (`CELERY_TASK_HARD_TIMEOUT`, default 300s) with SIGKILL on overrun
- `finally` block in `_spawn_and_stream` always publishes `result` + `done` (prevents hung WebSockets)
- API port fallback when 8000 is occupied
- Playbook completion is **`done` event driven**, not socket-close driven
- STIX ingestion is best-effort — Neo4j outages do not fail the Celery task

## Deployment / local scripts

| Command | Behavior |
|---------|----------|
| `npm run dev` | `scripts/run-stack.mjs dev` — full stack |
| `npm run up` | Docker only |
| `npm run prod` | Production-like stack |
| `python main.py` | Direct orchestrator (same as dev stack) |
