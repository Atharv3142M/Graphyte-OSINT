# Backend Scripts

Operational utilities for verification, seeding, and local development.

Run from the **repository root** unless noted otherwise.

## Prerequisites

- Docker: `docker compose up -d` (or `npm run up`)
- For API scripts: full stack running (`npm run dev`)

## Scripts

### `module_smoke.py` — API module smoke test

Exercises module endpoints through the running FastAPI server. Polls task results and classifies outcomes (`ok`, `needs_key`, `needs_deps`, `soft_fail`, etc.) using the **normalized envelope** (`ok`, `errors[]`).

```bash
# Stack must be running
python backend/scripts/module_smoke.py
```

Environment overrides:

| Variable | Default |
|----------|---------|
| `OSINT_SMOKE_API_BASE` | `http://127.0.0.1:8000` |
| `OSINT_SMOKE_TENANT_ID` | `aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` |
| `OSINT_SMOKE_POLL_MAX_S` | `45` |

Set `OSINT_SMOKE_API_BASE=http://127.0.0.1:8001` if the API bound to port 8001.

### `check_services.py` — Infrastructure connectivity

Verifies Redis, Neo4j, PostgreSQL, RabbitMQ, and Weaviate reachability.

```bash
cd backend
python scripts/check_services.py
```

### `seed_db.py` — Database seed

Seeds the default tenant and baseline provider configuration.

```bash
cd backend
python scripts/seed_db.py
```

Outputs the default tenant UUID for the `X-Tenant-ID` header.

### `simulate_investigation.py` — End-to-end simulation

Runs a backend-level investigation with streaming (requires FastAPI + Celery).

```bash
cd backend
python scripts/simulate_investigation.py
```

Uses `X-Tenant-ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee`.

### `ws_smoke.py` — WebSocket smoke

Validates task WebSocket streaming behavior.

```bash
cd backend
python scripts/ws_smoke.py
```

## Related root-level scripts

| Script | Purpose |
|--------|---------|
| `python test_all.py` | Subprocess-only module test (no API server; uses `normalize_result`) |
| `python verify.py` | Infrastructure verification wrapper |

## Default tenant header

```
X-Tenant-ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
```
