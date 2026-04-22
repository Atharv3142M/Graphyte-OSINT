# Graphyte OSINT

An open-source OSINT investigation platform with a FastAPI/Celery backend, Next.js frontend, real-time streaming, and STIX-compatible graph workflows.

## Key capabilities

- Unified investigation workflow for domains, IPs, emails, usernames, and URLs.
- Parallel module execution with live task and playbook streaming.
- Normalized module result envelopes for consistent frontend rendering.
- Graph exploration backed by Neo4j and STIX object transformation.
- Export-ready outputs for technical and operational reporting.

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

`npm run dev` performs dependency bootstrap, starts infrastructure, and launches the application stack.

Open `http://localhost:3000`.

### Other startup commands

- `npm run up` — start Docker infrastructure only.
- `npm run prod` — run a production-like local stack.

## Service topology

- Redis (`6379`) — Celery broker and pub/sub streaming.
- RabbitMQ (`5672`, `15672`) — event bus service.
- Neo4j (`7474`, `7687`) — graph persistence.
- Weaviate (`8080`) — vector/semantic workloads.
- PostgreSQL (`5432`) — relational persistence.

## Optional API keys

- `VAULT_SHODAN_API_KEY`
- `VAULT_CENSYS_API_ID`
- `VAULT_CENSYS_API_SECRET`

## Development workflow

- `npm run dev` for daily development.
- `make lint` and `make test` before creating a PR.
- See `CONTRIBUTING.md` for coding and contribution standards.

## Security highlights

- Multi-tenant request isolation through `X-Tenant-ID`.
- Optional JWT auth flow (`/api/auth/login`).
- Rate limiting with `slowapi`.
- SSRF safeguards for outbound target validation.

## Documentation

- `SETUP.md` — environment and local setup.
- `API_DOCS.md` — REST and WebSocket API specification.
- `ARCHITECTURE.md` — system architecture and data flow.
- `SECURITY.md` — vulnerability disclosure and security policy.

## License

Apache License 2.0.
