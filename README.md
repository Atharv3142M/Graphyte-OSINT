# Graphyte OSINT

An open-source OSINT investigation platform with a FastAPI/Celery backend, Next.js 15 frontend, real-time Redis streaming, and STIX-compatible graph workflows.

## Key capabilities

- **Beginner-first dashboard** — single Omnibar to investigate IPs, domains, emails, usernames, and URLs; results render as human-readable summaries and tables.
- **Advanced workspace** — Cytoscape graph, live terminal, and slide-over result panel for power users.
- **26 OSINT modules** — subprocess-isolated, keyless-first, with optional API keys where applicable.
- **Playbook orchestration** — auto-routes targets to relevant modules by detected type and intensity.
- **Normalized envelopes** — every module returns `{ ok, summary, artifacts, tables, raw, errors }` for consistent UI rendering.
- **STIX → Neo4j** — successful module output is mapped to STIX 2.1 bundles for graph exploration.

## Quick start

### Prerequisites

- Python `3.10+`
- Node.js `18+`
- Docker with Compose

### Run the full stack

```bash
git clone <repo-url>
cd Graphyte-OSINT
npm run dev
```

`npm run dev` bootstraps dependencies, starts Docker infrastructure, and launches FastAPI + Celery + Next.js.

| Surface | URL |
|---------|-----|
| **Dashboard (default)** | http://localhost:3000/dashboard |
| Frontend root | http://localhost:3000 (redirects to dashboard) |
| API health | http://localhost:8000/health (or **8001** if 8000 is busy — check terminal logs) |

### Other startup commands

- `npm run up` — Docker infrastructure only
- `npm run prod` — production-like local stack
- `python main.py` — same stack as `npm run dev` (after manual setup)

## UI overview

| Route | Purpose |
|-------|---------|
| `/dashboard` | **Search** — Omnibar + inline investigation results (default for new users) |
| `/tools` | **Module Runner** — run any single module with custom parameters |
| `/workspace` | **Advanced** — graph canvas, global terminal, result side panel |
| `/reports` | Export investigation reports |
| `/settings` | API keys and environment configuration |

## OSINT modules (26)

### Keyless (no API key required)

| Module | Focus |
|--------|--------|
| DNS Intel | A/AAAA/MX/NS/TXT/SOA, SPF/DMARC, optional subdomain brute-force |
| WHOIS | Domain registration metadata |
| SSL Analyzer | Certificate chain, protocols, grades |
| HTTP Security | Security headers audit (A–F grade) |
| Tech Stack | Web technologies fingerprinting |
| Cert Transparency | Subdomains via crt.sh |
| Robots & Sitemap | `robots.txt` rules + `sitemap.xml` URL ingestion |
| Favicon Hash | Shodan-style MurmurHash3 favicon fingerprint |
| Deep Scraper | Recursive page crawl (emails, links, profiles) |
| Reverse IP | Co-hosted domains |
| IP Geolocation | Geo, ASN, ISP metadata |
| BGP / ASN | BGPView enrichment |
| Wayback Machine | Historical snapshots (CDX) |
| Email Header | RFC822 header parsing |
| Social Hunter | Username presence across 50+ platforms |
| Sherlock | Deep username enumeration |
| CyberNinja | Passive username checks |
| xRecon | Keyless domain/username/email recon |
| Username Permutator | Generate username candidates from a seed |
| GitHub OSINT | Public profile + repos (60 req/hr unauthenticated) |
| Phone Intel | libphonenumber parse/validate/carrier/geo |
| Email Reputation | Disposable domain + MX validation |
| Port Scan | TCP port probe |
| Scraper | Multi-URL fetch |

### Optional API keys

| Module | Environment variables |
|--------|----------------------|
| Shodan | `VAULT_SHODAN_API_KEY` or `SHODAN_API_KEY` |
| Censys | `VAULT_CENSYS_API_ID`, `VAULT_CENSYS_API_SECRET` |
| GitHub OSINT (higher limits) | `GITHUB_TOKEN` or `VAULT_GITHUB_TOKEN` |

The platform runs fully without keys; keyed modules degrade gracefully.

## Service topology (Docker)

- **Redis** `6379` — Celery broker + pub/sub task streaming
- **RabbitMQ** `5672` / `15672` — audit/event bus
- **Neo4j** `7474` / `7687` — STIX graph persistence
- **Weaviate** `8080` — vector / semantic search
- **PostgreSQL** `5432` — tenants, configs, audit logs

## Development workflow

```bash
make lint          # backend compile + frontend ESLint
make test          # backend compile + frontend production build
python test_all.py # subprocess module smoke (no API server required)
```

See `CONTRIBUTING.md` for module authoring and PR standards.

## Security highlights

- Multi-tenant isolation via `X-Tenant-ID`
- Optional JWT auth (`POST /api/auth/login`)
- Rate limiting (`slowapi`)
- SSRF safeguards on outbound targets

## Documentation

| File | Contents |
|------|----------|
| [SETUP.md](SETUP.md) | Environment setup and validation |
| [API_DOCS.md](API_DOCS.md) | REST + WebSocket API reference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and data flow |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution and module workflow |
| [SECURITY.md](SECURITY.md) | Vulnerability disclosure |
| [knowledge.md](knowledge.md) | Agent-oriented project reference |

## License

Apache License 2.0.
