# Backend Scripts

Operational utility scripts for backend verification and local development.

## Prerequisites

- Docker containers running: `docker compose up -d`
- Run from `backend/` directory: `cd backend`

## Seed database

Seeds the default tenant and baseline provider configuration.

```bash
python scripts/seed_db.py
```

Output includes the default tenant UUID for `X-Tenant-ID` header.

## Check infrastructure

Verifies connectivity to core services.

```bash
python scripts/check_services.py
```

## Simulate investigation

Runs a backend-level investigation simulation with streaming.

```bash
# Ensure FastAPI and Celery are running first
python scripts/simulate_investigation.py
```

Uses `X-Tenant-ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee` (default tenant).
