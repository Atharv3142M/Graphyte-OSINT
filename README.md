# Unified Enterprise OSINT Platform

A distributed, polyglot Open Source Intelligence (OSINT) platform with multi-agent orchestration, vector search, and STIX 2.1 compliance. Built for enterprise threat intelligence and digital footprint analysis.

## Overview

- **Isolation-and-wrapper methodology**: FastAPI dispatches work to Celery; OSINT logic runs in isolated subprocesses with hard timeouts.
- **Polyglot persistence**: Redis (broker + pub/sub), Neo4j (STIX graph), Weaviate (semantic search), PostgreSQL (planned).
- **LangGraph multi-agent**: Searcher, Analyzer, Pentester, and Orchestrator agents with checkpoint memory and zero-trust scoped tools.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Docker & Docker Compose** (for Redis, RabbitMQ, Neo4j, Weaviate, PostgreSQL)

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd OSINT-Digital-Footprint-Visualizer
cp .env.example .env
# Edit .env with API keys (Shodan, Censys) if needed
```

### 2. Start infrastructure

```bash
docker compose up -d
```

### 3. Backend

```bash
cd backend
pip install -r requirements.txt
```

**Terminal 1 – FastAPI:**
```bash
uvicorn main:app --reload
```

**Terminal 2 – Celery worker:**
```bash
celery -A celery_app worker --loglevel=info
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CELERY_BROKER_URL` | Redis URL for Celery | `redis://localhost:6379/0` |
| `REDIS_URL` | Redis for pub/sub | Same as broker |
| `CELERY_TASK_HARD_TIMEOUT` | Seconds before SIGKILL | `300` |
| `VAULT_SHODAN_API_KEY` | Shodan API key | - |
| `VAULT_CENSYS_API_ID` | Censys API ID | - |
| `VAULT_CENSYS_API_SECRET` | Censys API secret | - |
| `NEO4J_URI` | Neo4j HTTP URI | `http://localhost:7474` |
| `NEO4J_USER` | Neo4j user | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | - |
| `WEAVIATE_HTTP_URI` | Weaviate HTTP URL | `http://localhost:8080` |
| `NEXT_PUBLIC_API_URL` | Backend API URL (frontend) | `http://localhost:8000` |

## Docker Services

| Service | Ports |
|---------|-------|
| Redis | 6379 |
| RabbitMQ | 5672 (AMQP), 15672 (Mgmt) |
| Neo4j | 7474 (HTTP), 7687 (Bolt) |
| Weaviate | 8080, 50051 |
| PostgreSQL | 5432 |

## Project Structure

```
├── backend/          # FastAPI, Celery, modules, agents
├── frontend/         # Next.js 15, React 18, Tailwind
├── docker-compose.yml
├── .env.example
├── README.md
├── ARCHITECTURE.md
└── API_DOCS.md
```

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) – Technical architecture and data flow
- [API_DOCS.md](./API_DOCS.md) – REST and WebSocket API reference
- [context.md](./context.md) – Project context and status

## License

Proprietary / See repository.
