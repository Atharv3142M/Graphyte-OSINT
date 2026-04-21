# OSINT Digital Footprint Visualizer

Open-source OSINT investigation platform with FastAPI + Celery backend, Next.js frontend, live graph visualization, and STIX 2.1 transformation pipeline.

## Why this project

- Investigate domains, IPs, emails, usernames, and URLs from one workspace.
- Run multiple OSINT modules in parallel and stream results.
- Build and explore a graph view backed by STIX objects.
- Generate investigation outputs and reusable intelligence artifacts.

## Current status

This repository is actively evolving toward production readiness. Core functionality works, but some roadmap items are still in progress.

- Recommended for local labs, demos, and contributor development.
- Not yet hardening-complete for internet-exposed production deployment.
- See `osint_full_roadmap.html` and `smart_search_implementation_plan.html` for implementation priorities.

## Quick start

### 1) Prerequisites

- Python `3.10+`
- Node.js `18+`
- Docker + Docker Compose

### 2) Clone and start infrastructure

```bash
git clone <repo-url>
cd OSINT-Digital-Footprint-Visualizer
docker compose up -d
```

### 3) Install dependencies

```bash
pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

### 4) Run the platform

```bash
python main.py
```

Open `http://localhost:3000`.

## Core services

`docker-compose.yml` starts:

- Redis (`6379`) for Celery broker and pub/sub
- RabbitMQ (`5672`, `15672`) for event messaging
- Neo4j (`7474`, `7687`) for graph storage
- Weaviate (`8080`) for vector/semantic layer
- PostgreSQL (`5432`) for config/audit persistence

## Modules

The platform currently includes DNS, WHOIS, SSL, HTTP security, tech stack, port scan, social hunting, certificate transparency, deep scraping, metadata extraction, and enrichment modules such as Shodan/Censys.

Most modules are keyless. Optional API keys improve depth for specific sources.

## Optional API keys

- `VAULT_SHODAN_API_KEY`
- `VAULT_CENSYS_API_ID`
- `VAULT_CENSYS_API_SECRET`

## Development workflow

- Use `make dev` to start local orchestration.
- Use `make lint` and `make test` before opening a PR.
- See `CONTRIBUTING.md` for module contribution guidelines.
- Use `python main.py --lite` for local API + frontend without Celery worker.

## Security and auth

- JWT login endpoint: `POST /api/auth/login`
- Enable required auth by setting `AUTH_REQUIRED=true`
- API rate limiting is enabled with `slowapi`
- SSRF safeguards block localhost, metadata IP, and private ranges on investigation targets

## New intelligence modules

- `IP Geolocation` (`/api/ip-geolocation`)
- `Reverse IP` (`/api/reverse-ip`)
- `BGP / ASN` (`/api/bgp-asn`)
- `Wayback Machine` (`/api/wayback`)
- `Email Header Analyzer` (`/api/email-header`)
- `Sherlock` (`/api/sherlock`)

## Documentation

- `ARCHITECTURE.md` - architecture and data flow
- `API_DOCS.md` - REST/WebSocket API reference
- `SETUP.md` - setup details
- `context.md` - project context

## Open-source project standards

- Contribution guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- License: `LICENSE`

## License

Licensed under the Apache License 2.0.
