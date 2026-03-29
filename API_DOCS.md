# Unified Enterprise OSINT Platform – API Reference

**Version:** 0.1.0 (Phase 8 - Keyless Backend + Multi-Route Dashboard)
**Last Updated:** 2026-03-29

Base URL: `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_URL` in frontend)

## Authentication

All API endpoints require the `X-Tenant-ID` header for multi-tenant isolation:

```
X-Tenant-ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
```

Default tenant UUID is seeded automatically by `verify.py` or `seed_db.py`.

## REST Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

**Response:** `{"status": "ok"}`

---

### Task-Based Endpoints (Celery + WebSocket)

These endpoints enqueue a Celery task and return a `task_id`. Use the WebSocket to stream stdout/stderr, or poll `GET /api/tasks/{task_id}` for the final result.

| Method | Endpoint | Request Body | Description |
|--------|----------|--------------|-------------|
| POST | `/api/shodan` | `{ "target": string, "api_key"?: string }` | Shodan host/domain recon |
| POST | `/api/censys` | `{ "target": string, "api_id"?: string, "api_secret"?: string }` | Censys host recon |
| POST | `/api/scrape` | `{ "urls": string[], "max_workers"?: number }` | Scrape URLs for emails/phones |
| POST | `/api/port-scan` | `{ "host": string, "ports"?: number[], "max_workers"?: number, "timeout"?: number }` | TCP port scan |
| POST | `/api/dns-intel` | `{ "domain": string, "brute_subdomains"?: boolean, "wordlist"?: string[] }` | DNS reconnaissance (A, AAAA, MX, NS, TXT, SPF/DMARC parsing, subdomain discovery) |
| POST | `/api/whois` | `{ "domain": string }` | WHOIS domain lookup |
| POST | `/api/ssl-analyze` | `{ "host": string, "port"?: number, "timeout"?: number }` | SSL/TLS certificate analysis |
| POST | `/api/http-security` | `{ "url": string, "timeout"?: number }` | HTTP security headers audit |
| POST | `/api/tech-stack` | `{ "url": string, "timeout"?: number }` | Technology stack detection |
| POST | `/api/cyberninja` | `{ "usernames": string[], "timeout"?: number, "site_list"?: string[] }` | Username enumeration across platforms |
| POST | `/api/xrecon` | `{ "query": string, "query_type"?: "username"|"email"|"domain" }` | Cross-platform reconnaissance |
| POST | `/api/social-hunter` | `{ "username": string, "max_concurrent"?: number }` | Social media presence check (50+ platforms) |
| POST | `/api/cert-transparency` | `{ "domain": string, "use_html_fallback"?: boolean }` | Subdomain discovery via CT logs |
| POST | `/api/deep-scraper` | `{ "url": string, "max_depth"?: number, "max_pages"?: number }` | Recursive deep web scraping |

**Response (all task endpoints):**
```json
{
  "task_id": "uuid",
  "status": "queued",
  "stream_url": "/ws/task/{task_id}",
  "result_url": "/api/tasks/{task_id}"
}
```

---

### Synchronous Endpoints

| Method | Endpoint | Request Body | Description |
|--------|----------|--------------|-------------|
| POST | `/api/ingest` | `{ "urls": string[], "strategies"?: string[] }` | GraySentinel pipeline: scrape, chunk, NER, embed, store in Weaviate |
| POST | `/api/semantic-search` | `{ "query": string, "limit"?: number }` | Natural-language semantic search (cosine similarity) |
| POST | `/api/agent/investigate` | `{ "goal": string, "thread_id"?: string }` | LangGraph multi-agent investigation |

**POST /api/ingest Response:**
```json
{
  "success": true,
  "ingested": 42,
  "urls": ["https://..."]
}
```

**POST /api/semantic-search Response:**
```json
{
  "success": true,
  "results": [
    {
      "content": "...",
      "source_url": "...",
      "chunk_strategy": "context_aware",
      "named_entities": ["..."],
      "distance": 0.23
    }
  ]
}
```

**POST /api/agent/investigate Response:**
```json
{
  "success": true,
  "thread_id": "inv-abc123",
  "summary": { "goal": "...", "discovered_ips": [...], "threat_score": 0.65, ... },
  "threat_score": 0.65,
  "stix_bundle": { "type": "bundle", "objects": [...] },
  "investigation_context": [...]
}
```

---

### Graph & Task Polling

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/graph` | Cytoscape-compatible elements (nodes/edges) from Neo4j |
| GET | `/api/tasks/{task_id}` | Poll task status and result |

**GET /api/graph Response:**
```json
{
  "elements": {
    "nodes": [{ "data": { "id": "...", "label": "...", "type": "..." } }],
    "edges": [{ "data": { "source": "...", "target": "..." } }]
  }
}
```

**GET /api/tasks/{task_id} Response (ready):**
```json
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "result": { ... }
}
```

---

## WebSocket

### Connection

```
ws://localhost:8000/ws/task/{task_id}
```

Connect after receiving `task_id` from a task-based POST endpoint.

### Message Format

Messages are JSON strings. Types:

| Type | Payload | Description |
|------|---------|-------------|
| `stream` | `{ "stream": "stdout"|"stderr", "data": string }` | Live log line |
| `result` | `{ "type": "result", "data": object }` | Final task result |
| `done` | `{ "type": "done", "killed"?: boolean }` | Stream ended |

### Client Behavior

1. Connect after enqueueing a task.
2. Receive `stream` messages for real-time logs (preserve ANSI for colorization).
3. Optionally receive `result` before `done`.
4. On `done`, close the connection.
