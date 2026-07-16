# Graphyte OSINT Platform - Quick Reference

## ⚡ 5-Minute Setup

```bash
# 1. Clone & prepare
git clone <repo-url>
cd graphyte-osint
cp .env.example .env

# 2. Create virtualenv
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install Python deps
pip install -r backend/requirements.txt

# 4. Start services (Docker)
docker-compose up -d

# 5. Start backend
python main.py

# 6. Start frontend (NEW TERMINAL)
cd frontend && pnpm dev

# ✅ Done! Visit http://localhost:3000
```

## 🔍 Validate Installation

```bash
python validate.py
```

Should show: `Passed: 9, Failed: 0` ✅

## 📍 Service Endpoints

| Service | URL | Port |
|---------|-----|------|
| Frontend | http://localhost:3000 | 3000 |
| Backend API | http://localhost:8000 | 8000 |
| API Docs | http://localhost:8000/docs | 8000 |
| Health | http://localhost:8000/health | 8000 |
| Neo4j Browser | http://localhost:7474 | 7474 |
| Redis | localhost:6379 | 6379 |
| PostgreSQL | localhost:5432 | 5432 |

## 🔧 Common Commands

### Backend
```bash
# Start
python main.py

# With debug logging
DEBUG=true python main.py

# Run Celery worker (optional)
celery -A backend.celery_app worker --loglevel=info
```

### Frontend
```bash
cd frontend

# Development
pnpm dev

# Build for production
pnpm build

# Test
pnpm test
```

### Database
```bash
# PostgreSQL CLI
psql -U osint -d osint_platform

# Neo4j Browser
open http://localhost:7474

# Redis CLI
redis-cli
```

### Docker
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f backend
docker-compose logs -f postgres

# Rebuild containers
docker-compose up -d --build
```

## 🧪 Test API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### List Playbooks
```bash
curl http://localhost:8000/api/playbooks
```

### List Modules
```bash
curl http://localhost:8000/api/modules
```

### Create Investigation
```bash
curl -X POST http://localhost:8000/api/investigations \
  -H "Content-Type: application/json" \
  -d '{
    "target": "example.com",
    "types": ["dns", "whois", "ssl"]
  }'
```

### Get Investigation Results
```bash
curl http://localhost:8000/api/investigations/{id}/results
```

## 📊 Available Playbooks

| Playbook | Modules | Speed |
|----------|---------|-------|
| Light | DNS, WHOIS, IP Geolocation | Fast |
| Standard | DNS, WHOIS, SSL, HTTP, Tech Stack | Medium |
| Aggressive | All 26 modules | Slow |
| Custom | User-defined | Variable |

## 🔐 Environment Variables

Key variables in `.env`:

```bash
# Core
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://osint:dev_postgres_secret@localhost/osint_platform
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687

# API Keys (Optional)
SHODAN_API_KEY=
CENSYS_API_ID=
CENSYS_API_SECRET=
GITHUB_TOKEN=

# Security
JWT_SECRET=your-secret-here
AUTH_REQUIRED=false
```

## 🚨 Troubleshooting

### Backend won't start
```bash
# Check services
redis-cli ping
psql -U osint -d osint_platform -c "SELECT 1"

# Check logs
python main.py 2>&1 | tail -20
```

### Frontend not loading
```bash
# Check backend is running
curl http://localhost:8000/health

# Check frontend logs
cd frontend && pnpm dev 2>&1 | tail -20
```

### Modules not executing
```bash
# Check Celery worker
celery -A backend.celery_app inspect active

# Check Redis
redis-cli DBSIZE

# View logs
tail -f /var/log/graphyte/celery.log
```

### Cannot connect to database
```bash
# Check PostgreSQL
psql -U osint -d osint_platform

# Reset connection
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

## 📈 26 OSINT Modules

**DNS & IP:** dns_intel, whois, ip_geolocation, reverse_ip, bgp_asn

**Web:** ssl_analyzer, http_security, tech_stack, robots_sitemap

**Intelligence:** shodan_recon, censys_recon, cert_transparency

**Scraping:** deep_scraper, metadata_extractor, email_header_analyzer

**Social:** github_osint, social_hunter, sherlock, email_reputation

**Advanced:** graysentinel, cyberninja, xrecon

**Utilities:** favicon_hash, username_permutator, wayback_machine, phone_intel, port_scanner

## 📚 Documentation

- **Setup:** [SETUP.md](SETUP.md)
- **Deployment:** [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Docs:** http://localhost:8000/docs
- **Rebuild Info:** [REBUILD_COMPLETE.md](REBUILD_COMPLETE.md)

## 🚀 Next Steps

1. **Validate:** `python validate.py`
2. **Explore:** Open http://localhost:3000
3. **Test:** Create a test investigation
4. **Deploy:** Follow [DEPLOYMENT.md](DEPLOYMENT.md) for production

## 💡 Pro Tips

- Use `DEBUG=true` for development
- Check logs: `docker-compose logs -f`
- Monitor performance: `http://localhost:8000/health`
- Test API: `http://localhost:8000/docs` (Swagger UI)
- Save investigations for replay

## 🆘 Need Help?

1. Run validation: `python validate.py`
2. Check logs: `docker-compose logs -f backend`
3. Review [TROUBLESHOOTING](DEPLOYMENT.md#troubleshooting)
4. Check [REBUILD_COMPLETE.md](REBUILD_COMPLETE.md)

---

**Everything working?** You're ready to investigate! 🎯
