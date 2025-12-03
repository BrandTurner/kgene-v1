# KEGG Explore Backend API v2.0.0

**Production-ready FastAPI backend for gene ortholog discovery and analysis.**

[![Tests](https://img.shields.io/badge/tests-90%2F90_passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green)]()
[![Coverage](https://img.shields.io/badge/coverage-88%25-yellowgreen)]()

---

## 🚀 Quick Start

### Option 1: Local Development (2 minutes)

```bash
# Setup
cp .env.example .env
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Database
alembic upgrade head

# Run
uvicorn app.main:app --reload --port 8000
# Worker: arq app.workers.worker.WorkerSettings
```

**API running at:** http://localhost:8000/docs

### Option 2: Docker (5 minutes)

```bash
cp .env.example .env
docker-compose up -d
docker-compose exec api alembic upgrade head
```

**API running at:** http://localhost:8000

---

## 📚 Documentation

| Guide | Description | Link |
|-------|-------------|------|
| **Quick Start** | Get running in 5 minutes | [QUICKSTART.md](QUICKSTART.md) |
| **Deployment** | Production deployment guide | [DEPLOYMENT.md](DEPLOYMENT.md) |
| **API Reference** | Complete API documentation | [API_GUIDE.md](API_GUIDE.md) |
| **Interactive Docs** | Swagger UI | http://localhost:8000/docs |

---

## ✨ Features

### Core Functionality
- ✅ **Organism Management** - CRUD operations for species
- ✅ **Gene Discovery** - Fetch genes from KEGG REST API
- ✅ **Ortholog Finding** - Background job processing with progress tracking
- ✅ **Advanced Filtering** - Bioinformatics-focused queries
- ✅ **CSV Export** - Streaming downloads for large datasets

### Production Features
- ✅ **Error Handling** - Global exception handlers with correlation IDs
- ✅ **Validation** - Pydantic v2 with custom validators (identity 0-100%, etc.)
- ✅ **API Documentation** - Auto-generated OpenAPI/Swagger
- ✅ **Background Jobs** - ARQ async job queue with Redis
- ✅ **Progress Tracking** - Real-time job monitoring
- ✅ **Comprehensive Tests** - 90 tests covering all endpoints

---

## 🧬 API Endpoints

### Organisms
```bash
GET    /api/organisms              # List all organisms (with filtering/sorting)
POST   /api/organisms              # Create organism
GET    /api/organisms/{id}         # Get single organism
PUT    /api/organisms/{id}         # Update organism
DELETE /api/organisms/{id}         # Delete organism
```

### Genes
```bash
GET    /api/genes                  # List genes (bioinformatics filters)
POST   /api/genes                  # Create gene
GET    /api/genes/{id}             # Get gene
PUT    /api/genes/{id}             # Update gene
DELETE /api/genes/{id}             # Delete gene
GET    /api/genes/export           # Export filtered genes to CSV
```

### Processes (Background Jobs)
```bash
POST   /api/processes              # Start gene processing job
GET    /api/processes              # List all processes
GET    /api/processes/{id}/progress # Check job progress
GET    /api/processes/{id}/download # Download genes as CSV
```

---

## 🔬 Bioinformatics Features

### Advanced Gene Filtering

```bash
# Find orphan genes (no orthologs)
GET /api/genes?organism_id=1&has_ortholog=false

# High-confidence orthologs (>90% identity)
GET /api/genes?organism_id=1&min_identity=90.0

# Find human orthologs
GET /api/genes?organism_id=1&ortholog_species=Homo sapiens

# Combined filters
GET /api/genes?organism_id=1&ortholog_species=homo&min_identity=70&sort_by=ortholog_identity&order=desc
```

### CSV Data Export

```bash
# Export all genes
curl "http://localhost:8000/api/processes/1/download" -o genes.csv

# Export only orthologs (exclude orphans)
curl "http://localhost:8000/api/processes/1/download?include_no_orthologs=false" -o orthologs.csv

# Export filtered genes
curl "http://localhost:8000/api/genes/export?organism_id=1&min_identity=80" -o high_conf.csv
```

---

## 🧪 Testing

```bash
# Run all tests (90 tests)
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test suite
pytest tests/test_api_organisms.py -v

# Run fast tests only (skip slow KEGG API calls)
pytest -m "not slow"
```

**Test Results:**
- ✅ 72 API endpoint tests
- ✅ 18 KEGG API client tests
- ✅ 100% pass rate
- ⚡ Fast execution (<15 seconds)

---

## 🏗️ Architecture

```
┌─────────────┐
│   FastAPI   │  ← REST API (async)
│   (Uvicorn) │
└──────┬──────┘
       │
   ┌───┴────┬─────────┐
   │        │         │
┌──▼──┐  ┌──▼──┐  ┌──▼──────┐
│ DB  │  │Redis│  │ Workers │
│(PG) │  │     │  │  (ARQ)  │
└─────┘  └─────┘  └─────────┘
```

### Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Framework** | FastAPI 0.109+ | Async REST API |
| **Database** | PostgreSQL 14+ | Gene & organism data |
| **Cache/Queue** | Redis 7+ | Job queue & caching |
| **Background Jobs** | ARQ | Async job processing |
| **Web Server** | Uvicorn | ASGI server |
| **Validation** | Pydantic v2 | Request/response validation |
| **Testing** | Pytest | Unit & integration tests |

---

## 📊 Database Schema

### Organisms
- `id` - Primary key
- `code` - KEGG organism code (3-4 lowercase letters)
- `name` - Organism name
- `status` - Processing status (pending/complete/error)
- `job_id` - Background job ID

### Genes
- `id` - Primary key
- `organism_id` - Foreign key to organisms
- `name` - KEGG gene ID (e.g., "eco:b0001")
- `description` - Gene function
- `ortholog_name` - Best ortholog match
- `ortholog_description` - Ortholog function
- `ortholog_species` - Ortholog organism
- `ortholog_identity` - Sequence identity % (0-100)
- `ortholog_sw_score` - Smith-Waterman score
- `ortholog_length` - Sequence length

---

## 🔒 Security

- ✅ Input validation (Pydantic v2)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ CORS configuration
- ✅ Rate limiting (configurable)
- ✅ Error correlation IDs (for tracking)
- ✅ Structured error responses

**Production Checklist:** See [DEPLOYMENT.md](DEPLOYMENT.md#security-checklist)

---

## 🚢 Deployment

### Docker (Recommended)

```bash
docker-compose up -d
```

Includes: PostgreSQL + Redis + API + Worker

### Heroku (Easiest Cloud)

```bash
heroku create your-app
heroku addons:create heroku-postgresql:standard-0
heroku addons:create heroku-redis:premium-0
git push heroku main
```

### Other Options
- AWS Elastic Beanstalk
- Google Cloud Run
- Bare metal (systemd services)

**Full guide:** [DEPLOYMENT.md](DEPLOYMENT.md)

---

## 📈 Performance

- **API Response Time:** <50ms (avg)
- **Gene Processing:** ~15-20 min for E. coli (4,600 genes)
- **Concurrent Jobs:** 10 (configurable)
- **CSV Export:** Streaming (handles 100k+ genes)
- **Database Pool:** 20 connections

---

## 🛠️ Development

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup database
createdb kgene
alembic upgrade head

# Run tests
pytest

# Code formatting
black .
ruff check .
```

### Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── organisms.py  # Organism CRUD
│   │   ├── genes.py      # Gene CRUD + filters
│   │   └── processes.py  # Background jobs
│   ├── core/             # Core functionality
│   │   ├── exceptions.py # Custom exceptions
│   │   ├── error_handlers.py # Global error handling
│   │   └── validators.py # Validation utilities
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   │   ├── kegg_api.py   # KEGG API client
│   │   ├── ortholog_service.py # Ortholog discovery
│   │   └── csv_export.py # CSV generation
│   └── workers/          # Background jobs
├── tests/                # Test suite (90 tests)
├── alembic/              # Database migrations
└── docker-compose.yml    # Docker setup
```

---

## 📝 API Examples

### Process an Organism

```python
import requests

# Create organism
response = requests.post("http://localhost:8000/api/organisms", json={
    "code": "eco",
    "name": "Escherichia coli K-12 MG1655"
})
organism = response.json()

# Start processing
job = requests.post("http://localhost:8000/api/processes", json={
    "organism_id": organism["id"]
}).json()

# Monitor progress
progress = requests.get(
    f"http://localhost:8000/api/processes/{organism['id']}/progress"
).json()
print(f"Status: {progress['status']} - {progress['progress']['percentage']}%")

# Download CSV when complete
csv_data = requests.get(
    f"http://localhost:8000/api/processes/{organism['id']}/download"
).text
```

**More examples:** [API_GUIDE.md](API_GUIDE.md#code-examples)

---

## 🐛 Troubleshooting

### Database Connection Failed
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string
echo $DATABASE_URL
```

### Redis Connection Failed
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
```

### Tests Failing
```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Check Python version
python --version  # Must be 3.11+
```

**More help:** [DEPLOYMENT.md#troubleshooting](DEPLOYMENT.md#troubleshooting)

---

## 📊 Project Status

| Phase | Status | Tests | Features |
|-------|--------|-------|----------|
| Phase 1: Database Models | ✅ Complete | ✓ | SQLAlchemy ORM |
| Phase 2: Basic API | ✅ Complete | ✓ | CRUD endpoints |
| Phase 3: Background Jobs | ✅ Complete | 18/18 | ARQ workers |
| Phase 4: Complete API | ✅ Complete | 72/72 | Production-ready |

**Total:** 90/90 tests passing ✅

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

---

## 📄 License

[Your License Here]

---

## 🙏 Acknowledgments

- **KEGG Database** - Gene and pathway data
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **SQLAlchemy** - Database ORM

---

## 📞 Support

- **Documentation**: See guides in this directory
- **API Docs**: http://localhost:8000/docs
- **Issues**: [GitHub Issues]
- **Email**: [Your Email]

---

**Built with ❤️ and Claude Code**

*Ready to discover gene orthologs? Get started with [QUICKSTART.md](QUICKSTART.md)*
