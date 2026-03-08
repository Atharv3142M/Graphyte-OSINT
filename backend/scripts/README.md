# Backend Scripts

Utility scripts for database seeding, infrastructure checks, and E2E simulation.

## Prerequisites

- Docker containers running: `docker compose up -d`
- Run from `backend/` directory: `cd backend`

## 1. Seed Database

Seeds default tenant (Alpha Corp) and mock Shodan/Censys configs.

```bash
python scripts/seed_db.py
```

Output includes the default tenant UUID for `X-Tenant-ID` header.

## 2. Infrastructure Sanity Check

Verifies connectivity to all 5 services.

```bash
python scripts/check_services.py
```

## 3. E2E Investigation Simulator

Simulates frontend: agent investigation + task with WebSocket stream.

```bash
# Ensure FastAPI and Celery are running first
python scripts/simulate_investigation.py
```

Uses `X-Tenant-ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` (default tenant).
