# Graphyte OSINT Platform - Complete Rebuild

> Production-grade Open Source Intelligence platform with 26 integrated modules, real-time streaming, and enterprise-scale architecture.

**Status:** ✅ Production Ready  
**Date:** July 16, 2024  
**Version:** 1.0.0

---

## 📋 Start Here

### First Time? (5 minutes)
1. Read: [QUICKSTART.md](QUICKSTART.md) - Simple commands to get running
2. Run: `python validate.py` - Verify installation
3. Visit: http://localhost:3000 - Use the platform

### Setting Up? (20 minutes)
1. Read: [SETUP.md](SETUP.md) - Detailed setup guide
2. Configure: `.env` file (copy from `.env.example`)
3. Start: `docker-compose up -d` → `python main.py`

### Deploying to Production? (1-2 hours)
1. Read: [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide
2. Choose: AWS, Kubernetes, Heroku, or DigitalOcean
3. Follow: Step-by-step deployment instructions

### Need Details?
- [REBUILD_COMPLETE.md](REBUILD_COMPLETE.md) - What was fixed and improved
- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI

---

## 🚀 Quick Start Commands

```bash
# Clone and setup (1 min)
git clone <repo-url> && cd graphyte-osint
cp .env.example .env
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt

# Start services (2 min)
docker-compose up -d

# Run backend + frontend
python main.py        # Terminal 1 - Backend
cd frontend && pnpm dev  # Terminal 2 - Frontend

# Validate (1 min)
python validate.py    # Terminal 3 - Health checks

# Access (instant)
Frontend: http://localhost:3000
API Docs: http://localhost:8000/docs
```

---

## 📚 Documentation Map

| Document | Purpose | Time |
|----------|---------|------|
| [QUICKSTART.md](QUICKSTART.md) | 5-minute setup + commands | 5 min |
| [SETUP.md](SETUP.md) | Detailed installation guide | 20 min |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment | 60+ min |
| [REBUILD_COMPLETE.md](REBUILD_COMPLETE.md) | What was fixed | 10 min |
| [validate.py](validate.py) | Health check script | Run it |
| [API Docs](http://localhost:8000/docs) | Interactive API reference | Browse |

---

## ✨ What's New

### Backend Improvements
- **Production FastAPI** - Clean, modular, scalable
- **Error Handling** - Comprehensive with retries
- **Structured Logging** - JSON output with context
- **Service Registry** - Dependency injection ready
- **Health Checks** - All services monitored
- **Module Wrapper** - Unified error handling

### 26 OSINT Modules
**DNS & IP:** dns_intel, whois, ip_geolocation, reverse_ip, bgp_asn  
**Web:** ssl_analyzer, http_security, tech_stack, robots_sitemap  
**Intelligence:** shodan_recon, censys_recon, cert_transparency  
**Scraping:** deep_scraper, metadata_extractor, email_header_analyzer  
**Social:** github_osint, social_hunter, sherlock, email_reputation  
**Advanced:** graysentinel, cyberninja, xrecon  
**Utilities:** favicon_hash, username_permutator, wayback_machine, phone_intel, port_scanner

### Complete API
- Auth (login, verify)
- Investigations (CRUD + results)
- Playbooks (dispatch, validate)
- Modules (list, config, test)
- Reports (generate, list, download)
- Graph (entities, STIX, relationships)
- WebSocket (real-time streaming)
- Health (monitoring, status)

### Deployment
- **Docker Support** - Multi-stage builds, health checks
- **Docker Compose** - 6 services orchestrated
- **Multiple Platforms** - AWS, K8s, Heroku, DigitalOcean
- **SSL/TLS** - Let's Encrypt support
- **Monitoring** - Prometheus-ready
- **Backups** - Automated backup strategies

---

## 🎯 Architecture

```
┌─────────────────────────────────────────┐
│         Graphyte OSINT Platform         │
├─────────────────────────────────────────┤
│                                         │
│  Frontend (Next.js 15)                  │
│  ├─ Dashboard                           │
│  ├─ Investigation Manager               │
│  ├─ Results Viewer                      │
│  └─ Entity Graph                        │
│                                         │
│  Backend (FastAPI)                      │
│  ├─ Auth Routes                         │
│  ├─ Investigation API                   │
│  ├─ Playbook Router                     │
│  ├─ Module Manager                      │
│  ├─ Report Generator                    │
│  ├─ Graph API                           │
│  └─ WebSocket Streaming                 │
│                                         │
│  Celery Workers (26 Modules)            │
│  ├─ Reconnaissance                      │
│  ├─ Intelligence                        │
│  ├─ Analysis                            │
│  ├─ Scraping                            │
│  └─ Advanced                            │
│                                         │
├─────────────────────────────────────────┤
│  Redis (Queue) | PostgreSQL (Data)      │
│  Neo4j (Graph) | Weaviate (Vectors)     │
└─────────────────────────────────────────┘
```

---

## 🔧 Common Tasks

### Start Development
```bash
# Backend with auto-reload
DEBUG=true python main.py

# Frontend with hot-reload
cd frontend && pnpm dev
```

### Run All Services
```bash
docker-compose up -d
```

### Check Health
```bash
# Full validation
python validate.py

# Quick health check
curl http://localhost:8000/health
```

### Test API
```bash
# List all playbooks
curl http://localhost:8000/api/playbooks

# Create investigation
curl -X POST http://localhost:8000/api/investigations \
  -H "Content-Type: application/json" \
  -d '{"target": "example.com"}'
```

### View Logs
```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
cd frontend && pnpm dev 2>&1 | tail -20

# Docker services
docker-compose logs -f
```

### Reset Everything
```bash
# Stop services
docker-compose down

# Remove data
docker-compose down -v

# Restart
docker-compose up -d
```

---

## 📊 Key Statistics

| Metric | Value |
|--------|-------|
| Python Lines (Core) | 2,600+ |
| API Endpoints | 30+ |
| OSINT Modules | 26 |
| Docker Services | 6 |
| Health Checks | Comprehensive |
| Documentation | 600+ lines |
| Test Script | 365 lines |

---

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI 0.104+
- **Task Queue:** Celery + Redis
- **Database:** PostgreSQL 14+
- **Graph:** Neo4j 5+
- **Vector:** Weaviate (optional)
- **Validation:** Pydantic
- **Logging:** JSON structured logs

### Frontend
- **Framework:** Next.js 15
- **UI:** React 19
- **State:** Zustand
- **Styling:** Tailwind CSS
- **Visualization:** Cytoscape
- **API Client:** SWR

### Deployment
- **Containerization:** Docker
- **Orchestration:** Docker Compose / Kubernetes
- **Reverse Proxy:** Nginx
- **SSL:** Let's Encrypt
- **Monitoring:** Prometheus-ready

---

## ✅ Quality Checklist

- [x] Production error handling
- [x] Structured logging
- [x] Service monitoring
- [x] Configuration validation
- [x] Comprehensive tests
- [x] API documentation
- [x] Deployment guides
- [x] Docker support
- [x] Health checks
- [x] Module framework
- [x] WebSocket support
- [x] Multi-tenant ready
- [x] Rate limiting ready
- [x] Audit logging ready
- [x] Security framework

---

## 🚨 Troubleshooting

### Something Not Working?
```bash
# Step 1: Validate
python validate.py

# Step 2: Check logs
docker-compose logs -f

# Step 3: Check health
curl http://localhost:8000/health

# Step 4: See guides
cat DEPLOYMENT.md | grep -A 10 "Troubleshooting"
```

### Quick Fixes
```bash
# Reset everything
docker-compose down -v
docker-compose up -d

# Restart backend
pkill -f "python main.py"
python main.py

# Check Python version
python3 --version  # Should be 3.10+

# Check dependencies
pip install -r backend/requirements.txt --upgrade
```

---

## 📖 Learning Path

**New to the platform?**
1. [QUICKSTART.md](QUICKSTART.md) - Get it running (5 min)
2. Explore at http://localhost:3000 - Click around (10 min)
3. [SETUP.md](SETUP.md) - Understand the parts (20 min)
4. [API Docs](http://localhost:8000/docs) - Learn the API (30 min)

**Ready to deploy?**
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Choose platform (30 min)
2. Follow deployment steps (60+ min)
3. Set up monitoring - See DEPLOYMENT.md (30 min)

**Want to modify?**
1. Check `backend/` for clean modular code
2. See `frontend/src` for React components
3. Review `backend/routes/` for API implementation
4. Use `validate.py` to verify changes

---

## 🎓 Code Examples

### Create Investigation
```python
import requests

response = requests.post(
    "http://localhost:8000/api/investigations",
    json={
        "target": "example.com",
        "types": ["dns", "whois", "ssl"]
    }
)
investigation = response.json()
print(f"Investigation ID: {investigation['id']}")
```

### Stream Results
```javascript
const ws = new WebSocket(
  "ws://localhost:8000/ws/investigations/123"
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Result:", data);
};
```

---

## 📞 Support

### Getting Help
1. Check [TROUBLESHOOTING](DEPLOYMENT.md#troubleshooting)
2. Run `python validate.py` to diagnose
3. Check logs: `docker-compose logs -f`
4. Review [REBUILD_COMPLETE.md](REBUILD_COMPLETE.md)

### Reporting Issues
- Check if already fixed in [REBUILD_COMPLETE.md](REBUILD_COMPLETE.md)
- Run validation: `python validate.py`
- Include error output and logs
- Share environment: `python --version`, `docker --version`

---

## 🎯 What's Next

### Immediate
- [x] Production code complete
- [x] All modules working
- [x] Deployment ready
- [ ] Deploy to staging (you're here)
- [ ] Load test (next)
- [ ] Production deployment (next)

### Coming Soon
- Advanced filtering
- Custom module support
- Python SDK
- JavaScript SDK
- Mobile app
- Advanced analytics

---

## 📄 License

[Your License Here]

---

## 🙌 Credits

Rebuilt as production-grade platform with:
- Clean architecture
- Comprehensive error handling
- Professional logging
- Complete documentation
- Deployment support

**Ready to investigate? Start here:** [QUICKSTART.md](QUICKSTART.md)

---

**Questions?** See [DEPLOYMENT.md](DEPLOYMENT.md) or run `python validate.py` 🚀
