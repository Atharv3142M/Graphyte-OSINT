# Graphyte OSINT Platform - Production Setup Guide

**Current Status:** Fixed and production-ready with proper error handling, structured logging, and modular architecture.

## Prerequisites

- **Python 3.10+** 
- **Node.js 18+**
- **Docker with Compose** (recommended for services)
- **Redis** (required for task queue)
- **PostgreSQL 14+** (required for data storage)
- **Neo4j 5+** (optional but recommended for entity graphs)
- **Weaviate** (optional for semantic search)

## Quick Start (5 minutes)

### 1. Clone and Setup
```bash
git clone <repo-url>
cd graphyte-osint

# Copy environment template
cp .env.example .env

# Create Python venv
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r backend/requirements.txt
```

### 2. Start Services
```bash
# Option A: Docker Compose (All services - recommended)
docker-compose up -d

# Option B: Manual (one by one)
redis-server &           # Terminal 1
postgres &               # Terminal 2
```

### 3. Install Frontend & Start Everything
```bash
# Terminal 3
cd frontend
pnpm install
cd ..

# Start backend
python main.py

# Terminal 4: Start frontend
cd frontend && pnpm dev
```

### 4. Access Dashboard
- **Frontend:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs
- **Health:** http://localhost:8000/health

## Environment file

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Key variables:

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Frontend API base (default `http://localhost:8000`) |
| `CELERY_BROKER_URL` | Redis URL for Celery |
| `VAULT_SHODAN_API_KEY` | Optional Shodan key |
| `VAULT_CENSYS_API_ID` / `VAULT_CENSYS_API_SECRET` | Optional Censys credentials |
| `GITHUB_TOKEN` / `VAULT_GITHUB_TOKEN` | Optional GitHub API token (higher rate limits) |

If the API binds to port **8001** (when 8000 is occupied), either set `NEXT_PUBLIC_API_URL=http://localhost:8001` or rely on the built-in port fallback in `frontend/src/lib/api.ts`.

## Manual setup (optional)

### 1) Python environment

```bash
python -m venv .venv
```

Activate:

- Windows: `.\.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

### 2) Install dependencies

```bash
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt
cd frontend && npm install
```

### 3) Start infrastructure

```bash
docker compose up -d
```

### 4) Launch stack

```bash
python main.py
```

## Validation checklist

| Check | Command / URL |
|-------|----------------|
| Frontend | http://localhost:3000/dashboard |
| API health | http://localhost:8000/health (or **8001** — see `main.py` logs) |
| Celery worker | Terminal shows `celery@... ready` and registered `tasks.*` |
| Subprocess modules | `python test_all.py` (from repo root) |
| Infrastructure | `python verify.py` |
| API smoke (stack running) | `python backend/scripts/module_smoke.py` |
| Backend scripts | See [backend/scripts/README.md](backend/scripts/README.md) |

### Expected `npm run dev` output

```
[LAUNCH] FASTAPI: ... uvicorn backend.api:app --reload --port 8000|8001
[LAUNCH] CELERY: ... celery -A backend.celery_app worker ...
[LAUNCH] NEXTJS: npm run dev --prefix frontend
[NEXTJS]   - Local:        http://localhost:3000
```

## Production-like local mode

```bash
npm run prod
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Investigations fail with network error | Confirm API is running; set `NEXT_PUBLIC_API_URL` to the port in logs |
| Modules queue but never complete | Ensure Celery worker is running and Redis is up (`docker compose ps`) |
| Favicon module fails | Requires `mmh3` — reinstall: `pip install -r backend/requirements.txt` |
| Censys returns dependency error | `pip install censys validators`; Censys also requires a valid IPv4 target |
| Graph empty | Neo4j must be running; modules must complete with `ok: true` for STIX ingestion |
