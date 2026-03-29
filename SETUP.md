# Unified Enterprise OSINT Platform – Setup Guide

This guide walks you through installing prerequisites, setting up a Python virtual environment, installing dependencies, starting infrastructure, verifying the stack, and launching the unified app.

---

## 1. Prerequisites

### Windows (PowerShell)

- **Docker Desktop** installed and running
- **Node.js 18+** (`node -v`)
- **Python 3.10+** (`python --version`)
- **Git Bash** recommended for best shell experience

### macOS / Linux

- **Docker** and **Docker Compose** (`docker compose version`)
- **Node.js 18+** (`node -v`)
- **Python 3.10+** (`python3 --version`)

---

### Python Dependencies

All dependencies are installed via `pip install -r backend/requirements.txt`. Key packages:
- `fastapi`, `uvicorn` - Web framework
- `celery[redis]` - Task queue
- `psycopg2-binary`, `redis`, `pika`, `neo4j`, `weaviate-client` - Data stores
- `dnspython`, `beautifulsoup4`, `requests` - OSINT modules
- `colorama` - Cross-platform colored terminal output

---

## 2. Clone Repository & Environment File

### Windows (PowerShell)

```powershell
git clone <repo-url>
cd OSINT-Digital-Footprint-Visualizer
Copy-Item .env.example .env
```

### macOS / Linux

```bash
git clone <repo-url>
cd OSINT-Digital-Footprint-Visualizer
cp .env.example .env
```

Edit `.env` to set any real API keys or secrets as needed.

---

## 3. Python Virtual Environment

Create and activate a virtual environment in the project root.

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

> The orchestration scripts (`verify.py`, `main.py`) will automatically prefer `venv` or `.venv` if present.

---

## 4. Install Backend Dependencies

With the virtual environment **activated**:

### Windows (PowerShell)

```powershell
cd backend
pip install -r requirements.txt
cd ..
```

### macOS / Linux

```bash
cd backend
pip install -r requirements.txt
cd ..
```

---

## 5. Install Frontend Dependencies & Fix Audits

### Windows (PowerShell)

```powershell
cd frontend
npm install
npm audit fix
# If necessary:
# npm audit fix --force
cd ..
```

### macOS / Linux

```bash
cd frontend
npm install
npm audit fix
# If necessary:
# npm audit fix --force
cd ..
```

> `npm audit fix --force` may apply breaking changes; use it only if `npm audit fix` alone is insufficient.

---

## 6. Start Infrastructure (Docker)

Ensure Docker is running, then from the project root:

### Windows (PowerShell)

```powershell
docker compose up -d
```

### macOS / Linux

```bash
docker compose up -d
```

This starts Redis, RabbitMQ, Neo4j, Weaviate, and PostgreSQL.

---

## 7. Unified Verification

Run the unified verification CLI to:
- Check connectivity to all services (PostgreSQL, Redis, RabbitMQ, Neo4j, Weaviate)
- Seed PostgreSQL with the default tenant
- Perform a dry-run E2E investigation (FastAPI + Celery)

With the virtual environment activated, from the project root:

### Windows (PowerShell)

```powershell
python .\verify.py
```

### macOS / Linux

```bash
python verify.py
```

If any service fails, the script will print diagnostics and exit with a non-zero code.

**Note:** The verification script uses ASCII-safe status markers (`[OK]`, `[FAIL]`) for cross-platform compatibility.

---

## 8. Launch the Unified App

Start FastAPI, Celery, and Next.js together using the master orchestrator.

With the virtual environment activated, from the project root:

### Windows (PowerShell)

```powershell
python .\main.py
```

### macOS / Linux

```bash
python main.py
```

This will:
- Run `uvicorn backend.api:app --reload --port 8000`
- Run `celery -A backend.celery_app worker --loglevel=info`
  - **Windows:** Automatically adds `--pool=solo --concurrency=1` (required for Windows compatibility)
- Run `npm run dev --prefix frontend`

Logs from each process are multiplexed and prefixed:
- `[FASTAPI]` – backend API
- `[CELERY]` – worker
- `[NEXTJS]` – frontend

Press **Ctrl+C** to gracefully stop all services.

### Windows-Specific Notes

- The orchestrator automatically detects Windows (`os.name == 'nt'`) and:
  - Adds `--pool=solo` to Celery (prevents worker freeze)
  - Uses `shell=True` for npm command (required for `.cmd` file execution)
  - Sets working directory to project root for all subprocesses
- All processes run from the project root to ensure proper Python module resolution

---

## 9. Accessing the UI

Open the browser at:

- `http://localhost:3000` – Unified Enterprise OSINT Platform UI

You can now perform investigations via the Omnibar, view graph intelligence, inspect STIX metadata, and monitor live logs.

