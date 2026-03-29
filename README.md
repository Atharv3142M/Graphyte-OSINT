# OSINT Digital Footprint Visualizer

A distributed, polyglot Open Source Intelligence platform with multi-agent orchestration, vector semantic search, and STIX 2.1 compliance. Built for enterprise threat intelligence and digital footprint analysis.

---

## Zero-Config Quick Start (No API Keys Required)

```bash
# 1. Clone and start all infrastructure
git clone <repo-url>
cd OSINT-Digital-Footprint-Visualizer
docker compose up -d

# 2. Install backend dependencies
cd backend && pip install -r requirements.txt && cd ..

# 3. Launch everything — backend, Celery worker, and frontend
python main.py
```

Open **[http://localhost:3000](http://localhost:3000)** — you are live.

> **No API keys needed.** The platform runs fully keyless. Shodan and Censys are optional enhancements — every core module (DNS intel, WHOIS, SSL analysis, social hunting, subdomain discovery, deep scraping, port scanning, etc.) works without any credentials.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Backend |
| Node.js | 18+ | Frontend |
| Docker & Docker Compose | Latest | Infrastructure services |

---

## Infrastructure Services

All started via `docker compose up -d`:

| Service | Port | Purpose |
|---------|------|---------|
| Redis | 6379 | Celery broker + pub/sub |
| RabbitMQ | 5672, 15672 | Enterprise event bus |
| Neo4j | 7474, 7687 | STIX 2.1 graph database |
| Weaviate | 8080 | Vector semantic search |
| PostgreSQL | 5432 | Audit logs, configs |

---

## Project Structure

```
backend/
├── api.py               # FastAPI — all REST + WebSocket endpoints
├── celery_app.py        # Celery worker configuration
├── tasks.py             # 15 async OSINT task definitions
├── stix_pipeline.py     # STIX 2.1 bundle builder
├── reporting_engine.py  # Report generators (Markdown, JSON, CSV)
├── neo4j_client.py      # Neo4j STIX ingestion + graph export
├── agents/              # LangGraph multi-agent (Searcher, Analyzer, Pentester)
└── modules/             # 15 individual OSINT modules

frontend/
└── src/app/
    ├── dashboard/        # Investigation launcher
    ├── tools/            # OSINT module grid
    ├── workspace/        # Full-screen STIX graph (Cytoscape.js)
    └── reports/          # Report generation and export

docker-compose.yml        # Redis, RabbitMQ, Neo4j, Weaviate, PostgreSQL
main.py                   # Master orchestrator (starts all 3 services)
.env.example              # All environment variables
```

---

## Optional API Keys

Most modules are fully keyless. Add keys for enhanced results:

| Service | Env Variable | Purpose |
|---------|-------------|---------|
| Shodan | `VAULT_SHODAN_API_KEY` | Host enrichment, banner data |
| Censys | `VAULT_CENSYS_API_ID` / `VAULT_CENSYS_API_SECRET` | Certificate enrichment |

Without keys, both modules fall back to public data sources seamlessly.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis for Celery |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for pub/sub |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `dev_neo4j_secret` | Neo4j password |
| `WEAVIATE_HTTP_URI` | `http://localhost:8080` | Weaviate URL |
| `RABBITMQ_URL` | `amqp://admin:dev_rabbitmq_secret@localhost:5672/` | RabbitMQ AMQP |
| `POSTGRES_DB` | `osint_platform` | PostgreSQL database |
| `CELERY_TASK_HARD_TIMEOUT` | `300` | Seconds before task SIGKILL |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend → API URL |

---

## Available OSINT Modules (All Keyless by Default)

| Module | Description |
|--------|-------------|
| **DNS Intel** | A/AAAA/MX/NS/TXT records, subdomain brute-forcing |
| **WHOIS Lookup** | Domain registration and registrant data |
| **SSL Analyzer** | TLS certificate chain and cipher analysis |
| **HTTP Security** | Security headers audit (HSTS, CSP, etc.) |
| **Technology Stack** | Wappalyzer-style fingerprinting |
| **Port Scanner** | Concurrent TCP SYN scan |
| **Social Hunter** | Username enumeration across 50+ platforms |
| **Cert Transparency** | Subdomain discovery via crt.sh CT logs |
| **Deep Scraper** | Recursive crawler: emails, phones, links, docs |
| **Metadata Extractor** | PDF/image/document metadata |
| **Shodan Recon** | Host data, banners, CVEs (key optional) |
| **Censys Recon** | Certificate and host enrichment (key optional) |
| **GraySentinel** | Scrape → chunk → NER → embed → Weaviate |
| **CyberNinja** | Passive username/email enumeration |
| **xRecon** | Cross-engine username and email lookup |

---

## STIX 2.1 Compliance

Every module result is automatically converted into a STIX 2.1 bundle and ingested into Neo4j, producing a live threat-intelligence graph. Fetch the graph at `GET /api/graph`.

---

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) — Technical architecture and data flow
- [API_DOCS.md](./API_DOCS.md) — REST and WebSocket API reference
- [context.md](./context.md) — Project context and status

---

## License

See repository.
