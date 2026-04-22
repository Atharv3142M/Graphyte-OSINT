# Architecture

## High-level system

The platform consists of:

- **Frontend:** Next.js application for investigations, graph exploration, module execution, and reporting.
- **API layer:** FastAPI service for routing, validation, and task dispatch.
- **Task layer:** Celery workers executing module workloads in subprocess isolation.
- **Streaming layer:** Redis pub/sub for task and playbook WebSocket events.
- **Persistence layer:** Neo4j graph store, Weaviate vector store, PostgreSQL relational store.

## Core data flow

1. User starts a playbook or module run from the frontend.
2. FastAPI validates input and enqueues Celery tasks.
3. Worker executes module logic and streams events via Redis channels.
4. Results are normalized into a consistent envelope (`ok`, `summary`, `artifacts`, `tables`, `raw`, `errors`).
5. Frontend consumes streams and renders normalized results.
6. STIX bundles are generated and ingested into Neo4j for graph visualization.

## Backend responsibilities

- `backend/api.py` — API surface and dispatch.
- `backend/tasks.py` — task orchestration and streaming lifecycle.
- `backend/run_module.py` — isolated module runner.
- `backend/normalize.py` — normalized UI result envelope generation.
- `backend/stix_pipeline.py` — STIX object mapping.
- `backend/neo4j_client.py` — graph persistence and query bridge.

## Frontend responsibilities

- `frontend/src/lib/api.ts` — typed API client and stream helpers.
- `frontend/src/store/useInvestigationStore.ts` — global investigation state.
- `frontend/src/components/ResultPanel.tsx` — normalized result rendering.
- `frontend/src/components/GraphCanvas.tsx` — graph visualization surface.

## Reliability and runtime behavior

- Module execution uses subprocess isolation to protect the API worker process.
- Result envelopes are emitted for both success and failure paths.
- Playbook completion is terminal-state based (`done` events), not socket-close based.
- Frontend request/stream logic includes API endpoint fallback for local port conflicts.

## Deployment model

- Local development and production-like startup are available from root scripts:
  - `npm run dev`
  - `npm run prod`
  - `npm run up`
