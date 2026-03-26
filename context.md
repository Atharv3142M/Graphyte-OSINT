# OSINT Digital Footprint Visualizer - Project Context

**Last Updated:** 2026-03-26
**Status:** Phase 3 Complete - UI Components Ready for Preview

---

## 1. Architecture Overview

### Isolation-and-Wrapper Methodology

The platform enforces strict isolation between HTTP and OSINT execution:

1. **FastAPI** - Command dispatcher only
2. **Celery** - Consumes tasks, spawns subprocesses
3. **run_module.py** - Subprocess CLI entry point
4. **Subprocess isolation** - OSINT runs separately, SIGKILL on timeout
5. **Config injection** - Ephemeral temp files for credentials

### Data Flow

Next.js -> FastAPI POST /api/* -> Celery task -> Redis queue -> Worker spawns subprocess -> run_module.py -> modules/* -> stdout/stderr -> Redis pub/sub -> WebSocket -> Frontend

### Polyglot Persistence

| Store | Purpose | Port |
|-------|---------|------|
| Redis | Celery broker + task stream | 6379 |
| RabbitMQ | Enterprise event bus | 5672 |
| Neo4j | STIX 2.1 graph | 7687 |
| Weaviate | Vector DB | 8080 |
| PostgreSQL | Multi-tenant configs | 5432 |

---

## 2. LangGraph Multi-Agent Orchestration

START -> orchestrator -> (searcher | analyzer | pentester) -> orchestrator -> END

- **Orchestrator**: Routes to sub-agents, synthesizes results
- **Searcher**: Tools: shodan_search, censys_search, scrape_urls, xrecon_search
- **Analyzer**: Tools: semantic_search, graysentinel_ingest, score_threat
- **Pentester**: Tools: port_scan, cyberninja_passive

---

## 3. Module Inventory

| Module | Function | Keyless |
|--------|----------|---------|
| shodan_recon | shodan_search | No |
| censys_recon | censys_search | No |
| scraper | scrape_urls | Yes |
| port_scanner | scan_ports | Yes |
| cyberninja_passive | username enum | Yes |
| graysentinel_pipeline | scrape->chunk->embed | Yes |
| xrecon | xrecon_search | Yes |
| dnsintel | DNS enumeration | Yes |

---

## 4. Frontend Structure

| Path | Purpose |
|------|---------|
| app/ | Next.js 15 dashboard |
| components/ | Sidebar, Omnibar, GraphCanvas, NodeDetailPanel, ResizableTerminal |
| lib/ | utils, mock-data |
| styles/ | ansi.css, globals.css |

**Tech:** Next.js 15, React 18, TypeScript, Tailwind, Radix UI, Cytoscape.js, Lucide

---

## 5. Design System

**Colors:**
- background: #020617 (slate-950)
- card: #1e293b (slate-800)
- cyan-500: #06b6d4
- green-500: #22c55e
- purple-500: #8b5cf6
- amber-500: #f59e0b
- red-500: #ef4444

---

## 6. STIX 2.1 Data Model

Node types: ipv4-addr, domain-name, network-traffic, note

Example:
```json
{
  "type": "ipv4-addr",
  "id": "ipv4-addr--uuid",
  "value": "8.8.8.8",
  "x_shodan_ports": [53, 443],
  "x_shodan_org": "Google LLC"
}
```

---

## 7. API Endpoints

| Endpoint | Description |
|----------|-------------|
| POST /api/shodan | Shodan recon |
| POST /api/port-scan | Port scan |
| POST /api/cyberninja | Passive username enum |
| POST /api/xrecon | Cross-platform recon |
| POST /api/ingest | GraySentinel pipeline |
| POST /api/agent/investigate | LangGraph multi-agent |
| GET /api/graph | Cytoscape elements |
| WS /ws/task/{id} | Real-time stream |

---

## 8. Environment

**Backend (.env):**
```
CELERY_BROKER_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
WEAVIATE_HTTP_URI=http://localhost:8080
DATABASE_URL=postgresql://postgres:password@localhost:5432/osint
```

**Frontend (.env.local):**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK_DATA=true
```

---

## 9. Mock Data System

Providers in frontend/src/lib/mock-data.ts:
- MOCK_GRAPH_ELEMENTS: 10 nodes, 8 edges
- MOCK_TERMINAL_STREAMS: shodan, port_scan, dns_intel, agent
- MOCK_NODE_DETAILS: Entity panels
- MOCK_TIMELINE_EVENTS: Investigation history

---

## 10. Key Files

| File | Purpose |
|------|---------|
| backend/api.py | FastAPI dispatcher |
| backend/tasks.py | Celery + subprocess |
| backend/run_module.py | Module CLI |
| frontend/src/app/page.tsx | Dashboard |
| frontend/src/components/GraphCanvas.tsx | Cytoscape |
| frontend/src/lib/mock-data.ts | Mock providers |

---

## 11. Troubleshooting

**Celery not consuming:**
```bash
redis-cli ping
celery -A backend.celery_app inspect ping
```

**Graph not loading:**
1. Check NEXT_PUBLIC_API_URL
2. curl http://localhost:8000/api/graph
3. Enable mock data

**CORS errors:**
Add CORSMiddleware to backend/api.py with allow_origins=["http://localhost:3000"]

---

## 12. Decision Log

| Decision | Why |
|----------|-----|
| Absolute imports | Prevents ModuleNotFoundError |
| Keyless-by-default | Works without API keys |
| Cytoscape.js | Better graph performance |
| Mock data | Offline development |
| Glass morphism | Modern cyber aesthetic |
| Subprocess isolation | Crash containment |

---

## 13. Quick Start

```bash
cp .env.example .env
docker compose up -d
cd backend && pip install -r requirements.txt
python verify.py
python main.py
cd frontend && npm run dev
```

Open http://localhost:3000

---

## 14. Phase Status

| Phase | Status |
|-------|--------|
| Phase 1 | Complete - Analysis |
| Phase 2 | Complete - Backend |
| Phase 3 | Complete - UI/UX |
| Phase 4 | Pending - Integration |
| Phase 5 | Pending - Testing |
