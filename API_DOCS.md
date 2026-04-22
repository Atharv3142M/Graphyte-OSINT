# API Reference

Base URL: `http://localhost:8000` (runtime may use a fallback port if `8000` is occupied).

## Headers

All platform endpoints accept:

```http
X-Tenant-ID: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
Content-Type: application/json
```

## Health and platform endpoints

- `GET /health`
- `GET /api/graph`
- `GET /api/tasks/{task_id}`
- `GET /api/playbook/{playbook_id}/plan`
- `POST /api/investigate` (playbook dispatch)
- `POST /api/agent/investigate` (agent-driven flow)

## OSINT module endpoints

The following enqueue Celery-backed tasks and return a task envelope:

- `POST /api/dns-intel`
- `POST /api/whois`
- `POST /api/ssl-analyze`
- `POST /api/http-security`
- `POST /api/tech-stack`
- `POST /api/metadata-extract`
- `POST /api/port-scan`
- `POST /api/social-hunter`
- `POST /api/cert-transparency`
- `POST /api/deep-scraper`
- `POST /api/ip-geolocation`
- `POST /api/reverse-ip`
- `POST /api/bgp-asn`
- `POST /api/wayback`
- `POST /api/email-header`
- `POST /api/sherlock`
- `POST /api/shodan`
- `POST /api/censys`
- `POST /api/cyberninja`
- `POST /api/xrecon`

### Standard task enqueue response

```json
{
  "task_id": "uuid",
  "status": "queued",
  "stream_url": "/ws/task/{task_id}",
  "result_url": "/api/tasks/{task_id}"
}
```

## Normalized result envelope

Module results are standardized before frontend rendering:

```json
{
  "ok": true,
  "module": "dns_intel",
  "summary": { "title": "DNS Intel: example.com", "stats": [], "badges": [] },
  "artifacts": { "ips": [], "domains": [], "urls": [], "emails": [], "usernames": [], "asns": [] },
  "tables": [],
  "raw": {},
  "errors": []
}
```

## WebSocket streams

### Task stream

`ws://<api-host>/ws/task/{task_id}`

### Playbook stream

`ws://<api-host>/ws/playbook/{playbook_id}`

### Playbook message types

- `result`: `{ "type": "result", "module": "tasks.dns_intel", "data": <envelope> }`
- `done`: `{ "type": "done", "module": "tasks.dns_intel", "status": "success|failure", "error": null|string }`
