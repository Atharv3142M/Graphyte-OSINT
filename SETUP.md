# Setup Guide

## Prerequisites

- Docker with Compose
- Node.js `18+`
- Python `3.10+`

## Recommended bootstrap

```bash
git clone <repo-url>
cd Graphyte-OSINT
npm run dev
```

This command initializes dependencies, starts infrastructure, and launches backend + worker + frontend.

## Manual setup (optional)

### 1) Environment file

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

### 2) Python environment

```bash
python -m venv .venv
```

Activate:

- Windows: `.\.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

### 3) Install dependencies

```bash
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt
cd frontend && npm install
```

### 4) Start infrastructure

```bash
docker compose up -d
```

### 5) Launch stack

```bash
python main.py
```

## Validation

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health` (or fallback port logged by `main.py`)
- Worker: verify Celery startup in terminal output
- Testing API modules: `python test_all.py`
- Checking infrastructure: `python verify.py`

## Production-like local mode

```bash
npm run prod
```

