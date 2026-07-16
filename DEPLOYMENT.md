# Graphyte OSINT Platform - Production Deployment Guide

**Status:** Production-ready with complete error handling, structured logging, and scalable architecture.

## Quick Deployment

### Option 1: Docker Compose (Recommended)
```bash
# Clone and setup
git clone <repo-url>
cd graphyte-osint
cp .env.example .env

# Start all services
docker-compose up -d

# Verify deployment
python validate.py

# Access services
Frontend:  http://localhost:3000
API:       http://localhost:8000
Neo4j:     http://localhost:7474
```

### Option 2: Manual Installation
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install Python dependencies
pip install -r backend/requirements.txt

# 3. Copy environment
cp .env.example .env

# 4. Start services (in separate terminals)

# Terminal 1: Redis
redis-server

# Terminal 2: PostgreSQL
postgres

# Terminal 3: Neo4j (Docker)
docker run -d -p 7687:7687 neo4j:5

# Terminal 4: Backend
python main.py

# Terminal 5: Frontend
cd frontend && pnpm dev

# Terminal 6: Celery Worker (optional)
celery -A backend.celery_app worker --loglevel=info
```

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│      Graphyte OSINT Platform v1.0       │
├─────────────────────────────────────────┤
│                                         │
│  Frontend (Next.js 15 + React)          │
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
│  Celery Workers (26 OSINT Modules)      │
│  ├─ Reconnaissance (DNS, WHOIS, etc.)   │
│  ├─ Intelligence (Shodan, Censys, etc.) │
│  ├─ Analysis (SSL, HTTP, Tech Stack)    │
│  ├─ Scraping (Deep, Social, etc.)       │
│  └─ Advanced (GraySentinel, XRecon)     │
│                                         │
├─────────────────────────────────────────┤
│  Data Layer                             │
├─────────────────────────────────────────┤
│                                         │
│  Redis (Task Queue + Cache)             │
│  PostgreSQL (Persistent Data)           │
│  Neo4j (Entity Relationships)           │
│  Weaviate (Vector Search) - Optional    │
│                                         │
└─────────────────────────────────────────┘
```

---

## Environment Configuration

### Production Environment Variables

```bash
# Core API
API_TITLE=Graphyte OSINT Platform
API_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://yourdomain.com

# Database
DATABASE_URL=postgresql://user:password@db.example.com:5432/graphyte
REDIS_URL=redis://cache.example.com:6379/0
CELERY_BROKER_URL=redis://cache.example.com:6379/0
CELERY_RESULT_BACKEND=redis://cache.example.com:6379/1

# Neo4j
NEO4J_URI=bolt://neo4j.example.com:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=strong_password_here

# Weaviate (Optional)
WEAVIATE_URL=http://weaviate.example.com:8080

# JWT & Security
JWT_SECRET=generate_strong_random_string_here
JWT_EXPIRATION_MINUTES=60
AUTH_REQUIRED=true

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=1000

# Module Configuration
MODULE_TIMEOUT=300
MODULE_RETRIES=2

# API Keys (Optional)
SHODAN_API_KEY=your_key
CENSYS_API_ID=your_id
CENSYS_API_SECRET=your_secret
GITHUB_TOKEN=your_token
```

### Generate Secure JWT Secret
```bash
openssl rand -base64 32
```

---

## Database Setup

### PostgreSQL Initialization

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE USER graphyte WITH PASSWORD 'strong_password';
CREATE DATABASE graphyte OWNER graphyte;

# Exit
\q

# Initialize schema (future: use Alembic migrations)
psql -U graphyte -d graphyte < backend/schemas.sql
```

### Neo4j Initialization

```bash
# Access Neo4j Browser: http://localhost:7474

# Create STIX constraints (in Neo4j browser console)
CREATE CONSTRAINT stix_id IF NOT EXISTS 
  FOR (s:StixObject) REQUIRE s.id IS UNIQUE;

# Create indexes for performance
CREATE INDEX investigation_target IF NOT EXISTS 
  FOR (i:Investigation) ON (i.target);
```

---

## Deployment Options

### Option 1: AWS (Recommended for Production)

**Components:**
- **EC2** for backend and workers
- **RDS** for PostgreSQL
- **ElastiCache** for Redis
- **Neptune** for Neo4j (or managed EC2 instance)
- **ALB** for load balancing
- **S3** for report storage
- **CloudWatch** for monitoring

**Setup:**
```bash
# 1. Create RDS PostgreSQL instance
# 2. Create ElastiCache Redis cluster
# 3. Launch EC2 instance (Ubuntu 22.04, t3.large)
# 4. Clone repo and setup

git clone <repo-url>
cd graphyte-osint
pip install -r backend/requirements.txt
cp .env.production .env

# 5. Start services
python main.py
celery -A backend.celery_app worker

# 6. Configure ALB to forward to :8000
```

### Option 2: Kubernetes (Scalable)

**Components:**
- Deployment for backend
- StatefulSet for Celery workers
- ConfigMap for settings
- Service for networking
- Ingress for HTTP routing

**Setup:**
```bash
# Build container
docker build -t graphyte-backend:1.0 -f Dockerfile.backend .

# Create Kubernetes resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/celery.yaml
kubectl apply -f k8s/ingress.yaml

# Check deployment
kubectl get pods -n graphyte
```

### Option 3: Heroku

**Setup:**
```bash
# Login to Heroku
heroku login

# Create app
heroku create graphyte-osint

# Set environment variables
heroku config:set REDIS_URL=<heroku-redis-url> -a graphyte-osint
heroku config:set DATABASE_URL=<heroku-postgres-url> -a graphyte-osint
heroku config:set JWT_SECRET=<generated-secret> -a graphyte-osint

# Deploy
git push heroku main

# Scale dynos
heroku ps:scale web=1 worker=2 -a graphyte-osint

# Monitor
heroku logs --tail -a graphyte-osint
```

### Option 4: DigitalOcean App Platform

**Setup:**
```bash
# Create app.yaml
cat > app.yaml << 'EOF'
name: graphyte
services:
- name: api
  github:
    repo: your-org/graphyte
    branch: main
  build_command: pip install -r backend/requirements.txt
  run_command: python main.py
  http_port: 8000
  envs:
  - key: DATABASE_URL
    scope: RUN_AND_BUILD_TIME
  - key: REDIS_URL
    scope: RUN_AND_BUILD_TIME
- name: worker
  github:
    repo: your-org/graphyte
    branch: main
  build_command: pip install -r backend/requirements.txt
  run_command: celery -A backend.celery_app worker
databases:
- name: postgres
  engine: PG
  version: "15"
- name: redis
  engine: REDIS
  version: "7"
EOF

# Deploy to DigitalOcean
doctl apps create --spec app.yaml
```

---

## SSL/TLS Configuration

### Let's Encrypt (with Nginx Reverse Proxy)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Configure Nginx
cat > /etc/nginx/sites-available/graphyte << 'EOF'
upstream backend {
    server localhost:8000;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
EOF

# Enable and start
sudo ln -s /etc/nginx/sites-available/graphyte /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## Monitoring & Logging

### Application Monitoring

```bash
# Backend logs
tail -f /var/log/graphyte/backend.log

# Celery logs
tail -f /var/log/graphyte/celery.log

# Database connections
psql -U graphyte -d graphyte -c "SELECT count(*) FROM pg_stat_activity;"
```

### Prometheus Metrics (Future Implementation)

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'graphyte-backend'
    static_configs:
      - targets: ['localhost:8000']
```

### Health Checks

```bash
# Application health
curl https://yourdomain.com/health

# Readiness probe
curl https://yourdomain.com/ready

# Individual services
redis-cli PING
psql -c "SELECT 1"
cypher-shell -u neo4j -p password "RETURN 1"
```

---

## Backup & Recovery

### Database Backups

```bash
# PostgreSQL daily backup
0 2 * * * pg_dump -U graphyte graphyte > /backups/graphyte_$(date +\%Y\%m\%d).sql

# Neo4j backup (Docker)
docker exec graphyte-neo4j bin/neo4j-admin database backup --to-path=/backups neo4j

# Redis backup
0 3 * * * redis-cli --rdb /backups/dump_$(date +\%Y\%m\%d).rdb
```

### Disaster Recovery

```bash
# Restore PostgreSQL
psql -U graphyte -d graphyte < /backups/graphyte_20240716.sql

# Restore Neo4j
docker exec graphyte-neo4j bin/neo4j-admin database restore --from-path=/backups neo4j

# Restore Redis
docker exec graphyte-redis redis-cli --rdb /backups/dump_20240716.rdb
```

---

## Performance Tuning

### Database Optimization

```sql
-- PostgreSQL
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '10MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
SELECT pg_reload_conf();

-- Create indexes
CREATE INDEX idx_investigations_status ON investigations(status);
CREATE INDEX idx_investigations_created ON investigations(created_at);
```

### Redis Optimization

```bash
# Set maxmemory policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET maxmemory 4gb
```

### Application Scaling

```bash
# Scale Celery workers
celery -A backend.celery_app worker -c 16 --loglevel=info

# Use worker pools
celery -A backend.celery_app worker -P gevent -c 1000
```

---

## Security Hardening

### Production Checklist

- [ ] Change all default passwords
- [ ] Enable JWT authentication (AUTH_REQUIRED=true)
- [ ] Configure SSL/TLS with valid certificate
- [ ] Set strong CORS origins
- [ ] Enable database SSL connections
- [ ] Configure firewall rules
- [ ] Enable rate limiting
- [ ] Set up audit logging
- [ ] Regular security updates
- [ ] Configure backup retention
- [ ] Set up monitoring alerts
- [ ] Document runbooks

### Security Settings

```bash
# .env.production
DEBUG=false
AUTH_REQUIRED=true
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=1000
JWT_SECRET=$(openssl rand -base64 32)
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

---

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
python main.py 2>&1 | head -50

# Verify Redis
redis-cli ping

# Verify PostgreSQL
psql -U graphyte -d graphyte -c "SELECT 1"

# Verify Neo4j
curl http://localhost:7474/db/data/
```

### Slow Performance

```bash
# Check database
psql -d graphyte -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check Redis
redis-cli INFO stats

# Check Celery queue
celery -A backend.celery_app inspect active
```

### Module Failures

```bash
# View module logs
tail -f /var/log/graphyte/celery.log | grep "module_name"

# Retry failed tasks
celery -A backend.celery_app purge

# Check module registry
python -c "from backend.modules.registry import module_registry; print(module_registry.list_modules())"
```

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor error rates
- Check disk space
- Verify backups

**Weekly:**
- Review performance metrics
- Check security logs
- Update dependencies

**Monthly:**
- Full system backup
- Security audit
- Capacity planning

**Quarterly:**
- Major version updates
- Performance optimization
- Disaster recovery drill

---

## Support & Documentation

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Logs:** `docker-compose logs -f backend`
- **Issues:** GitHub Issues
- **Status:** http://status.yourdomain.com

---

## License

[Your License Here]
