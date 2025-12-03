# KEGG Explore Backend - Quick Start Guide

Get the backend API running in 5 minutes!

## Prerequisites

- **Python 3.11+** installed
- **PostgreSQL 14+** running
- **Redis 7+** running
- **Git** for version control

---

## Option 1: Local Development (Fastest)

### Step 1: Clone & Setup

```bash
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing
```

### Step 2: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your database/Redis URLs
nano .env
```

Minimum required in `.env`:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/kgene
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-this-to-something-secure
```

### Step 3: Setup Database

```bash
# Create database
createdb kgene

# Run migrations
alembic upgrade head
```

### Step 4: Start Services

```bash
# Terminal 1: Start API server
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start background worker
arq app.workers.worker.WorkerSettings
```

### Step 5: Test API

```bash
# Health check
curl http://localhost:8000/health

# API docs (Swagger UI)
open http://localhost:8000/docs

# Create test organism
curl -X POST http://localhost:8000/api/organisms \
  -H "Content-Type: application/json" \
  -d '{"code":"eco","name":"Escherichia coli K-12 MG1655"}'
```

**✅ Done! API running at http://localhost:8000**

---

## Option 2: Docker (Recommended for Production-like Setup)

### Step 1: Install Docker

```bash
# Mac: Install Docker Desktop
brew install --cask docker

# Linux: Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

### Step 2: Create Configuration

```bash
cd backend

# Create .env file
cp .env.example .env

# Edit with production values
nano .env
```

### Step 3: Start All Services

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### Step 4: Run Migrations

```bash
docker-compose exec api alembic upgrade head
```

### Step 5: Test API

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

**✅ Done! Full stack running with Docker**

---

## Option 3: Cloud Deployment (Heroku - Easiest Cloud)

### Step 1: Install Heroku CLI

```bash
# Mac
brew tap heroku/brew && brew install heroku

# Or download from https://devcenter.heroku.com/articles/heroku-cli
```

### Step 2: Create Heroku App

```bash
cd backend

# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:standard-0

# Add Redis
heroku addons:create heroku-redis:premium-0
```

### Step 3: Configure Environment

```bash
# Set secret key
heroku config:set SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Set environment
heroku config:set ENVIRONMENT=production
heroku config:set DEBUG=false

# Set CORS (replace with your domain)
heroku config:set ALLOWED_ORIGINS=https://your-frontend.com
```

### Step 4: Deploy

```bash
# Deploy to Heroku
git push heroku main

# Run migrations
heroku run alembic upgrade head

# Scale workers
heroku ps:scale web=2 worker=1
```

### Step 5: Test Deployment

```bash
# Open app
heroku open

# View logs
heroku logs --tail

# Test API
curl https://your-app-name.herokuapp.com/health
```

**✅ Done! Production API live on Heroku**

---

## Common Commands

### Development

```bash
# Start API server (auto-reload)
uvicorn app.main:app --reload

# Start worker
arq app.workers.worker.WorkerSettings

# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html
```

### Database

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Backup database
pg_dump kgene > backup_$(date +%Y%m%d).sql

# Restore database
psql kgene < backup.sql
```

### Docker

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f api

# Restart service
docker-compose restart api

# Execute command in container
docker-compose exec api bash
```

### Heroku

```bash
# View logs
heroku logs --tail

# Run migrations
heroku run alembic upgrade head

# Access database
heroku pg:psql

# Scale workers
heroku ps:scale web=2 worker=1

# Restart app
heroku restart
```

---

## Verify Installation

Test all endpoints:

```bash
# Health check
curl http://localhost:8000/health

# List organisms
curl http://localhost:8000/api/organisms

# Create organism
curl -X POST http://localhost:8000/api/organisms \
  -H "Content-Type: application/json" \
  -d '{"code":"eco","name":"E. coli"}'

# Start gene processing job
curl -X POST http://localhost:8000/api/processes \
  -H "Content-Type: application/json" \
  -d '{"organism_id":1}'

# Check progress
curl http://localhost:8000/api/processes/1/progress

# Download genes as CSV
curl http://localhost:8000/api/processes/1/download -o genes.csv
```

---

## Troubleshooting

### Issue: Database connection failed

```bash
# Check PostgreSQL is running
pg_isready

# Check connection string
psql postgresql://user:pass@localhost:5432/kgene
```

### Issue: Redis connection failed

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Check Redis URL
redis-cli -u redis://localhost:6379/0 ping
```

### Issue: Import errors

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

### Issue: Port already in use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

---

## Next Steps

1. **Read DEPLOYMENT.md** for production deployment guide
2. **Configure monitoring** (Sentry, metrics)
3. **Set up backups** (automated database backups)
4. **Review security** (SSL, firewall, secrets)
5. **Load test** (ensure performance under load)

---

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Support

- **Full Deployment Guide**: See `DEPLOYMENT.md`
- **API Reference**: http://localhost:8000/docs
- **GitHub Issues**: [Report bugs/issues]
- **Documentation**: [Link to docs if available]

---

## Quick Reference Card

| Task | Command |
|------|---------|
| Start API | `uvicorn app.main:app --reload` |
| Start Worker | `arq app.workers.worker.WorkerSettings` |
| Run Tests | `pytest` |
| Migrations | `alembic upgrade head` |
| Docker Up | `docker-compose up -d` |
| Docker Logs | `docker-compose logs -f api` |
| Health Check | `curl http://localhost:8000/health` |
| API Docs | http://localhost:8000/docs |

---

**Happy coding! 🚀**
