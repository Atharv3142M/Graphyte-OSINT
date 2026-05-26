# Setup Guide

## Prerequisites

- Docker with Compose
- Node.js `18+`
- Python `3.10+`

## Recommended bootstrap

```bash
git clone <repo-url>
cd OSINT-Digital-Footprint-Visualizer
npm run dev
```

This command:

1. Starts Docker services (`docker compose up -d`)
2. Creates/updates the Python venv and installs `backend/requirements.txt`
3. Installs frontend dependencies if needed
4. Launches FastAPI, Celery worker, and Next.js dev server via `main.py`

Open the dashboard: **http://localhost:3000/dashboard**

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
