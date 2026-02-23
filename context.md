# Unified Enterprise OSINT Platform - Project Context

## Overview

Independent project building a Unified Enterprise OSINT Platform. Original source repos (OSINT-Search, Digital-Footprint-OSINT-Tool, bat-security-toolkit, etc.) are in the root folder and will be deleted once the platform is complete.

## Project Structure

```
├── frontend/          # Next.js 15, React 18, TypeScript
│   ├── src/app/       # App router, layout, page
│   └── ...
├── backend/           # FastAPI
│   ├── main.py        # FastAPI app, CORS, health
│   ├── requirements.txt
│   └── modules/       # Extracted OSINT modules (programmatic API)
│       ├── shodan_recon.py   # Shodan API (from am0nt31r0/OSINT-Search)
│       ├── censys_recon.py   # Censys API (from am0nt31r0/OSINT-Search)
│       ├── scraper.py        # Multi-threaded scraping (from Hamed233/Digital-Footprint-OSINT-Tool)
│       └── port_scanner.py   # TCP port scanner (inspired by Kcisti/bat-security-toolkit)
├── context.md
└── (original repos - to be removed)
```

## Extracted Modules (backend/modules/)

| Module | Source | Methodology | API |
|--------|--------|-------------|-----|
| `shodan_recon` | am0nt31r0/OSINT-Search | Shodan API (host/domain lookup) | `shodan_search(target, api_key=None)` |
| `censys_recon` | am0nt31r0/OSINT-Search | Censys API (IPv4, protocols, certs) | `censys_search(target, api_id=None, api_secret=None)` |
| `scraper` | Hamed233/Digital-Footprint-OSINT-Tool | Multi-threaded scraping (emails, phones) | `scrape_urls(urls, max_workers=5)` |
| `port_scanner` | Kcisti/bat-security-toolkit | TCP connect-based port scan | `scan_ports(host, ports=None, max_workers=20, timeout=2.0)` |

All modules accept arguments programmatically (no CLI parsing) for FastAPI/Celery integration.

## API Keys (Placeholders)

- **Shodan**: `YOUR_SHODAN_API_KEY` (shodan_recon.py)
- **Censys**: `YOUR_CENSYS_API_ID`, `YOUR_CENSYS_API_SECRET` (censys_recon.py)

Replace via env/config in production; never hardcode real keys.

## Status

- [x] Project structure initialized (frontend + backend)
- [x] backend/modules/ created
- [x] Shodan, Censys, scraper, port_scanner extracted and rewritten
- [ ] FastAPI routes to expose modules (planned)
- [ ] Celery/async task integration (planned)
- [ ] Frontend UI (planned)
- [ ] Remove original repo folders (after confirmation)

## Original Repos (Reference Only)

- am0nt31r0/OSINT-Search (OSINT-Search-master)
- Hamed233/Digital-Footprint-OSINT-Tool (Digital-Footprint-OSINT-Tool-main)
- Kcisti/bat-security-toolkit (bat-security-toolkit-main)
- CyberNinja-main, Forensight-main, GraySentinel-main, TraceGraph-main, xRec0n-main
