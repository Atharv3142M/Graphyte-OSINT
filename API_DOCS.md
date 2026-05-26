# API Reference

Base URL: `http://localhost:8000` (runtime may use **8001** if port 8000 is occupied — check `main.py` / uvicorn logs).

WebSocket base: replace `http` with `ws` (e.g. `ws://localhost:8001`).

## Headers

All platform endpoints accept:

```http
X-Tenant-ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
Content-Type: application/json
```

Optional authentication (when `AUTH_REQUIRED=true`):

```http
Authorization: Bearer <jwt>
```

Obtain a token via `POST /api/auth/login`.

---

## Platform endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/api/graph` | Neo4j graph elements for Cytoscape |
| `GET` | `/api/tasks/{task_id}` | Poll Celery task status + result envelope |
| `GET` | `/api/playbook/{playbook_id}/plan` | Module plan stored in Redis |
| `POST` | `/api/investigate` | Playbook dispatch (multi-module) |
| `POST` | `/api/agent/investigate` | LangGraph agent investigation |
| `GET` | `/api/reports` | List report types |
| `GET` | `/api/reports/{report_type}` | Generate report export |
| `GET` / `POST` | `/api/settings/env` | Read/write runtime env settings |
| `POST` | `/api/auth/login` | JWT login (optional) |
| `POST` | `/api/semantic-search` | Vector search (Weaviate) |
| `POST` | `/api/ingest` | GraySentinel document ingest |

---

## Playbook dispatch

### `POST /api/investigate`

Starts a correlated multi-module investigation.

**Request:**

```json
{
  "target": "example.com",
  "types": ["domain"],
  "intensity": "standard"
}
```

| Field | Values |
|-------|--------|
| `types` | `ipv4`, `ipv6`, `cidr`, `domain`, `url`, `email`, `username`, `phone`, `asn`, `hash_md5`, `hash_sha1`, `hash_sha256`, `company` |
| `intensity` | `low` (keyless/passive only), `standard`, `aggressive` |

**Response:**

```json
{
  "playbook_id": "pb-abc123",
  "modules": ["tasks.dns_intel", "tasks.whois_lookup", "..."],
  "module_labels": { "tasks.dns_intel": "DNS Intel" },
  "task_ids": ["uuid-1", "uuid-2"],
  "ws_url": "/ws/playbook/pb-abc123",
  "target": "example.com",
  "types": ["domain"]
}
```

Connect to `ws://<host>/ws/playbook/{playbook_id}` for live results.

---

## OSINT module endpoints

Each endpoint enqueues a Celery task and returns:

```json
{
  "task_id": "uuid",
  "status": "queued",
  "stream_url": "/ws/task/{task_id}",
  "result_url": "/api/tasks/{task_id}"
}
```

Stream live output: `ws://<host>/ws/task/{task_id}`

### Network & domain

| Endpoint | Body fields | Notes |
|----------|-------------|-------|
| `POST /api/dns-intel` | `domain`, `brute_subdomains?`, `wordlist?` | Keyless |
| `POST /api/whois` | `domain` | Keyless |
| `POST /api/ssl-analyze` | `host`, `port?`, `timeout?` | Keyless |
| `POST /api/http-security` | `url`, `timeout?` | Keyless |
| `POST /api/tech-stack` | `url`, `timeout?` | Keyless |
| `POST /api/cert-transparency` | `domain`, `use_html_fallback?` | Keyless (crt.sh) |
| `POST /api/robots-sitemap` | `domain`, `max_sitemap_urls?` | Keyless |
| `POST /api/favicon-hash` | `domain` | Keyless (requires `mmh3`) |
| `POST /api/port-scan` | `host`, `ports?`, `max_workers?`, `timeout?` | Keyless |
| `POST /api/ip-geolocation` | `target` | Keyless |
| `POST /api/reverse-ip` | `target` | Keyless |
| `POST /api/bgp-asn` | `target` | Keyless (BGPView) |
| `POST /api/wayback` | `target`, `limit?` | Keyless |

### Identity & social

| Endpoint | Body fields | Notes |
|----------|-------------|-------|
| `POST /api/social-hunter` | `username`, `max_concurrent?` | Keyless |
| `POST /api/sherlock` | `username`, `timeout?`, `max_connections?` | Keyless |
| `POST /api/cyberninja` | `usernames[]`, `timeout?`, `site_list?` | Keyless |
| `POST /api/xrecon` | `query`, `query_type?` (`auto`, `domain`, `username`, `email`, `ip`) | Keyless |
| `POST /api/username-permutator` | `seed`, `max_results?` | Keyless |
| `POST /api/github-osint` | `target`, `lookup_type?`, `api_token?`, `max_repos?` | Keyless; token optional |
| `POST /api/phone-intel` | `number`, `default_region?` | Keyless |
| `POST /api/email-reputation` | `email` | Keyless |
| `POST /api/email-header` | `raw_headers` | Keyless |

### Content & keyed recon

| Endpoint | Body fields | Notes |
|----------|-------------|-------|
| `POST /api/deep-scraper` | `url`, `max_depth?`, `max_pages?`, `max_concurrent?` | Keyless |
| `POST /api/scrape` | `urls[]`, `max_workers?` | Keyless |
| `POST /api/metadata-extract` | `file_path` | Local file path on worker host |
| `POST /api/shodan` | `target`, `api_key?` | Requires Shodan API key |
| `POST /api/censys` | `target` (IPv4), `api_id?`, `api_secret?` | Requires Censys credentials |
| `POST /api/ingest` | `urls[]`, `strategies?` | GraySentinel pipeline |

---

## Normalized result envelope

All module tasks return this shape via Celery (and `GET /api/tasks/{id}` when complete):

```json
{
  "ok": true,
  "module": "dns_intel",
  "summary": {
    "title": "DNS Intel: example.com",
    "stats": [{ "label": "Grade", "value": "A" }],
    "badges": []
  },
  "artifacts": {
    "ips": ["93.184.216.34"],
    "domains": ["example.com"],
    "urls": [],
    "emails": [],
    "usernames": [],
    "asns": []
  },
  "tables": [
    {
      "name": "records",
      "columns": ["type", "value"],
      "rows": [["A", "93.184.216.34"]]
    }
  ],
  "raw": { "success": true, "domain": "example.com" },
  "errors": []
}
```

On failure, `ok` is `false` and `errors` contains structured entries:

```json
{
  "errors": [
    {
      "code": "missing_api_key",
      "message": "Invalid API key",
      "hint": "Set the required API key(s) in Settings or environment variables.",
      "retryable": false
    }
  ]
}
```

Error codes include: `module_error`, `missing_api_key`, `ssrf_blocked`, `timeout`.

---

## WebSocket streams

### Task stream — `ws://<host>/ws/task/{task_id}`

Messages include:

| Type | Shape |
|------|--------|
| stdout/stderr | `{ "stream": "stdout"\|"stderr", "data": "<line>" }` |
| result | `{ "type": "result", "data": <envelope> }` |
| done | `{ "type": "done", "error": bool, "error_msg": string\|null }` |

**Important:** Wait for the `done` event — do not treat socket close as completion.

### Playbook stream — `ws://<host>/ws/playbook/{playbook_id}`

| Type | Shape |
|------|--------|
| result | `{ "type": "result", "module": "tasks.dns_intel", "data": <envelope> }` |
| stdout/stderr | `{ "type": "stdout"\|"stderr", "module": "tasks.dns_intel", "data": "<line>" }` |
| done | `{ "type": "done", "module": "tasks.dns_intel", "status": "success"\|"failure", "error": null\|string }` |

---

## Polling fallback

If WebSocket connection fails, the frontend polls `GET /api/tasks/{task_id}` until `status` is `SUCCESS` or `FAILURE`, then reads `result` (the normalized envelope).

---

## Rate limits

Investigation endpoints use `slowapi` rate limiting (e.g. `POST /api/investigate` — 30/minute per IP). Adjust in `backend/api.py` if needed.
