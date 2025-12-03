# KEGG Explore Backend - Deployment Guide

Complete guide for deploying the KEGG Explore backend API to different environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Deployment Options](#deployment-options)
   - [Docker Deployment (Recommended)](#docker-deployment-recommended)
   - [Bare Metal Deployment](#bare-metal-deployment)
   - [Cloud Platform Deployment](#cloud-platform-deployment)
4. [Database Setup](#database-setup)
5. [Background Workers](#background-workers)
6. [Monitoring & Logging](#monitoring--logging)
7. [Security Checklist](#security-checklist)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Services

| Service | Version | Purpose |
|---------|---------|---------|
| Python | 3.11+ | Application runtime |
| PostgreSQL | 14+ | Primary database |
| Redis | 7+ | Background job queue & caching |

### Hardware Recommendations

**Development/Testing**:
- 2 CPU cores
- 4 GB RAM
- 10 GB disk

**Production (Small - <10 concurrent users)**:
- 4 CPU cores
- 8 GB RAM
- 50 GB disk (grows with gene data)

**Production (Medium - 10-50 concurrent users)**:
- 8 CPU cores
- 16 GB RAM
- 100 GB disk

---

## Environment Configuration

### 1. Create `.env` File

Create a `.env` file in the `backend/` directory:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kegg_explore
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4  # Number of uvicorn workers

# Environment
ENVIRONMENT=production  # development | staging | production

# Security
SECRET_KEY=your-secret-key-here-change-this-in-production
ALLOWED_ORIGINS=https://your-frontend-domain.com,https://another-domain.com
CORS_ALLOW_CREDENTIALS=true

# KEGG API Configuration
KEGG_BASE_URL=https://rest.kegg.jp
KEGG_RATE_LIMIT=3  # Requests per second (KEGG limit)

# Logging
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=json  # json | text

# Background Jobs
ARQ_MAX_JOBS=10  # Max concurrent background jobs
ARQ_JOB_TIMEOUT=3600  # Job timeout in seconds (1 hour)

# Optional: Sentry Error Tracking
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### 2. Generate Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output to `SECRET_KEY` in your `.env` file.

---

## Deployment Options

### Docker Deployment (Recommended)

#### Step 1: Create `Dockerfile`

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Step 2: Create `docker-compose.yml`

Create `backend/docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: kegg_postgres
    environment:
      POSTGRES_USER: kegg_user
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
      POSTGRES_DB: kegg_explore
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kegg_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache & Queue
  redis:
    image: redis:7-alpine
    container_name: kegg_redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Application
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: kegg_api
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://kegg_user:${DB_PASSWORD:-changeme}@postgres:5432/kegg_explore
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: production
      SECRET_KEY: ${SECRET_KEY}
      ALLOWED_ORIGINS: ${ALLOWED_ORIGINS}
    ports:
      - "8000:8000"
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    command: >
      sh -c "
        alembic upgrade head &&
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
      "

  # ARQ Background Worker
  worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: kegg_worker
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://kegg_user:${DB_PASSWORD:-changeme}@postgres:5432/kegg_explore
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: production
    restart: unless-stopped
    command: arq app.workers.worker.WorkerSettings

volumes:
  postgres_data:
  redis_data:
```

#### Step 3: Deploy with Docker

```bash
# Create .env file with production values
nano .env

# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check service status
docker-compose ps

# Run database migrations
docker-compose exec api alembic upgrade head

# Stop services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

---

### Bare Metal Deployment

#### Step 1: Install Python Dependencies

```bash
# Install Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Install & Configure PostgreSQL

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE USER kegg_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE kegg_explore OWNER kegg_user;
GRANT ALL PRIVILEGES ON DATABASE kegg_explore TO kegg_user;
\q
EOF

# Update PostgreSQL to allow connections (if remote)
sudo nano /etc/postgresql/15/main/postgresql.conf
# Set: listen_addresses = '*'

sudo nano /etc/postgresql/15/main/pg_hba.conf
# Add: host all all 0.0.0.0/0 md5

sudo systemctl restart postgresql
```

#### Step 3: Install & Configure Redis

```bash
# Install Redis
sudo apt install redis-server

# Configure Redis for production
sudo nano /etc/redis/redis.conf
# Set:
# maxmemory 1gb
# maxmemory-policy allkeys-lru
# appendonly yes

sudo systemctl enable redis-server
sudo systemctl restart redis-server
```

#### Step 4: Run Database Migrations

```bash
# Set DATABASE_URL in .env first
source venv/bin/activate
alembic upgrade head
```

#### Step 5: Create Systemd Service

Create `/etc/systemd/system/kegg-api.service`:

```ini
[Unit]
Description=KEGG Explore FastAPI Application
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/kegg-explore/backend
Environment="PATH=/var/www/kegg-explore/backend/venv/bin"
EnvironmentFile=/var/www/kegg-explore/backend/.env
ExecStart=/var/www/kegg-explore/backend/venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/kegg-worker.service`:

```ini
[Unit]
Description=KEGG Explore ARQ Background Worker
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/kegg-explore/backend
Environment="PATH=/var/www/kegg-explore/backend/venv/bin"
EnvironmentFile=/var/www/kegg-explore/backend/.env
ExecStart=/var/www/kegg-explore/backend/venv/bin/arq app.workers.worker.WorkerSettings
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kegg-api kegg-worker
sudo systemctl start kegg-api kegg-worker

# Check status
sudo systemctl status kegg-api
sudo systemctl status kegg-worker

# View logs
sudo journalctl -u kegg-api -f
sudo journalctl -u kegg-worker -f
```

#### Step 6: Configure Nginx Reverse Proxy

Create `/etc/nginx/sites-available/kegg-api`:

```nginx
upstream kegg_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.kegg-explore.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.kegg-explore.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.kegg-explore.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.kegg-explore.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # API proxy
    location / {
        proxy_pass http://kegg_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if adding WebSockets later)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;  # 5 minutes for gene processing
    }

    # Health check endpoint
    location /health {
        proxy_pass http://kegg_api/health;
        access_log off;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/kegg-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### Cloud Platform Deployment

#### AWS Elastic Beanstalk

Create `.ebextensions/01_packages.config`:

```yaml
packages:
  yum:
    postgresql-devel: []

option_settings:
  aws:elasticbeanstalk:application:environment:
    DATABASE_URL: "postgresql+asyncpg://user:pass@db.xxx.rds.amazonaws.com:5432/kegg"
    REDIS_URL: "redis://cache.xxx.cache.amazonaws.com:6379/0"
  aws:elasticbeanstalk:container:python:
    WSGIPath: app.main:app
```

Deploy:

```bash
eb init -p python-3.11 kegg-explore
eb create production
eb deploy
```

#### Google Cloud Run

Create `cloudbuild.yaml`:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/kegg-api', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/kegg-api']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'kegg-api'
      - '--image=gcr.io/$PROJECT_ID/kegg-api'
      - '--platform=managed'
      - '--region=us-central1'
      - '--allow-unauthenticated'
```

Deploy:

```bash
gcloud builds submit --config cloudbuild.yaml
```

#### Heroku

Create `Procfile`:

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: arq app.workers.worker.WorkerSettings
```

Deploy:

```bash
heroku create kegg-explore-api
heroku addons:create heroku-postgresql:standard-0
heroku addons:create heroku-redis:premium-0
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
git push heroku main
heroku ps:scale web=2 worker=1
```

---

## Database Setup

### Run Migrations

```bash
# Check current version
alembic current

# View migration history
alembic history

# Upgrade to latest
alembic upgrade head

# Rollback one version
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "Description"
```

### Database Backup & Restore

**Backup**:

```bash
# Full backup
pg_dump -h localhost -U kegg_user kegg_explore > backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
pg_dump -h localhost -U kegg_user kegg_explore | gzip > backup_$(date +%Y%m%d).sql.gz

# Backup with Docker
docker-compose exec postgres pg_dump -U kegg_user kegg_explore > backup.sql
```

**Restore**:

```bash
# Restore from SQL
psql -h localhost -U kegg_user kegg_explore < backup.sql

# Restore compressed
gunzip -c backup.sql.gz | psql -h localhost -U kegg_user kegg_explore

# Restore with Docker
docker-compose exec -T postgres psql -U kegg_user kegg_explore < backup.sql
```

### Automated Backups

Create `/etc/cron.daily/kegg-backup`:

```bash
#!/bin/bash
BACKUP_DIR=/var/backups/kegg-explore
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
pg_dump -h localhost -U kegg_user kegg_explore | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

# Upload to S3 (optional)
aws s3 cp $BACKUP_DIR/backup_$DATE.sql.gz s3://your-bucket/backups/
```

```bash
sudo chmod +x /etc/cron.daily/kegg-backup
```

---

## Background Workers

### ARQ Worker Management

**Start Worker**:

```bash
# Development
arq app.workers.worker.WorkerSettings

# Production (with systemd)
sudo systemctl start kegg-worker
```

**Monitor Worker**:

```python
# In Python shell
from app.workers.worker import get_worker_info
import asyncio

async def check_workers():
    info = await get_worker_info()
    print(f"Active jobs: {info['jobs_in_progress']}")
    print(f"Queued jobs: {info['jobs_queued']}")

asyncio.run(check_workers())
```

**View Redis Queue**:

```bash
redis-cli

# List all keys
KEYS *

# View ARQ queue
LRANGE arq:queue 0 -1

# View job results
GET arq:result:job_id_here

# Clear all jobs (⚠️ use with caution)
FLUSHDB
```

---

## Monitoring & Logging

### Application Logs

**View Logs**:

```bash
# Docker
docker-compose logs -f api

# Systemd
sudo journalctl -u kegg-api -f

# Log files (if configured)
tail -f /var/log/kegg-explore/api.log
```

### Health Check Endpoint

```bash
# Basic health check
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2025-12-02T12:00:00Z"
}
```

### Monitoring with Prometheus

Add metrics endpoint to `app/main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

### Error Tracking with Sentry

Already configured in `app/main.py`. Just set `SENTRY_DSN` in `.env`:

```bash
SENTRY_DSN=https://your-key@sentry.io/project-id
```

### Performance Monitoring

Use built-in correlation IDs from error responses to track requests:

```bash
# All errors include correlation_id for tracing
curl http://localhost:8000/api/organisms/99999
# Response includes: "correlation_id": "uuid-here"

# Search logs by correlation ID
journalctl -u kegg-api | grep "correlation-id-here"
```

---

## Security Checklist

### Pre-Deployment Security

- [ ] Change `SECRET_KEY` from default value
- [ ] Use strong database passwords (16+ characters)
- [ ] Set `ALLOWED_ORIGINS` to specific domains (not `*`)
- [ ] Enable HTTPS/TLS for all connections
- [ ] Set up firewall rules (only ports 80/443 exposed)
- [ ] Disable database remote access (if not needed)
- [ ] Set Redis password: `requirepass yourpassword`
- [ ] Use environment variables (never commit `.env` to git)
- [ ] Enable PostgreSQL SSL: `sslmode=require` in DATABASE_URL
- [ ] Set secure cookie settings (if using sessions)
- [ ] Configure rate limiting (already in Nginx example)

### Post-Deployment Security

- [ ] Monitor Sentry for security errors
- [ ] Review logs regularly for suspicious activity
- [ ] Keep dependencies updated: `pip install --upgrade -r requirements.txt`
- [ ] Run security audits: `pip-audit`
- [ ] Set up automated backups
- [ ] Configure log rotation
- [ ] Enable fail2ban for brute force protection
- [ ] Set up SSL certificate auto-renewal (Let's Encrypt)

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql postgresql://user:pass@localhost:5432/kegg_explore

# Check DATABASE_URL in .env
echo $DATABASE_URL
```

#### 2. Redis Connection Failed

```bash
# Check Redis is running
sudo systemctl status redis

# Test connection
redis-cli ping
# Should return: PONG

# Check REDIS_URL
redis-cli -u $REDIS_URL ping
```

#### 3. Import Errors

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

#### 4. Migration Errors

```bash
# Check current version
alembic current

# Downgrade and retry
alembic downgrade -1
alembic upgrade head

# Nuclear option (⚠️ deletes data)
alembic downgrade base
alembic upgrade head
```

#### 5. Background Jobs Not Running

```bash
# Check worker is running
sudo systemctl status kegg-worker

# Check Redis queue
redis-cli LLEN arq:queue

# Restart worker
sudo systemctl restart kegg-worker
```

#### 6. High Memory Usage

```bash
# Check PostgreSQL connection pool
# Reduce DATABASE_POOL_SIZE in .env

# Check ARQ max jobs
# Reduce ARQ_MAX_JOBS in .env

# Check running processes
ps aux | grep python
```

### Performance Tuning

**Database**:

```sql
-- Add indexes for common queries
CREATE INDEX idx_genes_organism_id ON genes(organism_id);
CREATE INDEX idx_genes_ortholog_name ON genes(ortholog_name);
CREATE INDEX idx_organisms_code ON organisms(code);
CREATE INDEX idx_organisms_status ON organisms(status);
```

**API Workers**:

```bash
# Increase workers for higher traffic
uvicorn app.main:app --workers 8

# Formula: (2 x CPU cores) + 1
```

**Redis Memory**:

```bash
# Check memory usage
redis-cli INFO memory

# Set max memory in redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

---

## Scaling Considerations

### Vertical Scaling (Single Server)

- Increase server resources (CPU, RAM)
- Optimize database queries (use indexes)
- Increase worker count
- Use Redis for caching

### Horizontal Scaling (Multiple Servers)

- Load balancer (Nginx, HAProxy, AWS ALB)
- Shared PostgreSQL database (RDS, managed DB)
- Shared Redis (ElastiCache, managed Redis)
- Multiple API servers
- Multiple worker servers

### Example Load Balanced Setup

```
                    ┌───────────────┐
                    │ Load Balancer │
                    └───────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
        ┌───▼───┐       ┌───▼───┐       ┌───▼───┐
        │ API 1 │       │ API 2 │       │ API 3 │
        └───┬───┘       └───┬───┘       └───┬───┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
          ┌─────▼─────┐          ┌─────▼─────┐
          │ PostgreSQL│          │   Redis   │
          │    (RDS)  │          │ (Managed) │
          └───────────┘          └───────────┘
                                       │
                                ┌──────┴──────┐
                                │             │
                           ┌────▼────┐  ┌────▼────┐
                           │Worker 1 │  │Worker 2 │
                           └─────────┘  └─────────┘
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/your-org/kegg-explore/issues
- Documentation: https://docs.kegg-explore.com
- Email: support@kegg-explore.com

---

## License

See LICENSE file in repository root.
