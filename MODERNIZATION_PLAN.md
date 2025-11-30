# KEGG Explore Modernization Plan

## Executive Summary

This plan outlines the modernization of the KEGG Explore bioinformatics application from Ruby on Rails 4.2.4 (2015) to a modern Python stack. The application fetches gene data from KEGG REST API and discovers orthologous genes across organisms.

### Key Decisions Summary

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Backend Framework** | FastAPI | Async/await support, modern, high performance, auto API docs |
| **Frontend Framework** | React + TypeScript | Modern SPA, best UX, component reusability |
| **Database** | PostgreSQL (prod) / SQLite (dev) | Scalable, reliable, good for bioinformatics |
| **ORM** | SQLAlchemy 2.0 | Mature, async support, flexible |
| **Background Jobs** | ARQ (Async Redis Queue) | Async-native, lightweight, Redis-backed |
| **HTTP Client** | httpx | Async, modern, rate limiting friendly |
| **Authentication** | None | Removed per requirements - simpler deployment |
| **Deployment** | Docker Compose | Single-server, suitable for academic use |
| **Ortholog Strategy** | API-first | Research KEGG KO, eggNOG, OMA alternatives before scraping |

### Timeline: 9 weeks
- Weeks 1-3: Backend foundation + KEGG integration
- Week 4: Background jobs
- Week 5: Complete backend API
- Weeks 6-7: React frontend
- Week 8: Integration & deployment
- Week 9: Documentation & migration

## Current Architecture Analysis

### What the App Does
1. Users trigger processing for an organism by code
2. Background job fetches all genes for that organism from KEGG REST API
3. For each gene, scrapes KEGG SSDB web pages to find best non-self ortholog
4. Stores ortholog relationships with metrics (identity, SW score, length)
5. Provides UI to explore results and export to CSV

### Current Tech Stack (2015)
- Rails 4.2.4 + Ruby 2.2.0
- Oracle database (dev/prod) / SQLite (test)
- Sidekiq + Redis for background jobs
- Parallel gem (10 threads)
- RestClient + Nokogiri for web scraping
- Devise for authentication

### Key Challenges
1. **KEGG API Rate Limits**: 3 requests/second (academic use only)
2. **SSDB Scraping**: Best-best ortholog data NOT available via REST API
3. **Data Volume**: Organisms can have thousands of genes (e.g., human ~20,000)
4. **Long-Running Jobs**: Processing can take hours for large organisms

## Proposed Modern Stack

### Core Framework: **FastAPI**
**Rationale:**
- Modern async/await support (critical for I/O-bound KEGG API calls)
- Automatic OpenAPI documentation
- Type hints for better code quality
- High performance (comparable to Node.js/Go)
- Growing rapidly in bioinformatics/ML communities
- Lighter weight than Django for this use case

**Sources:** [FastAPI vs Django comparison](https://betterstack.com/community/guides/scaling-nodejs/fastapi-vs-django-vs-flask/)

### Database: **PostgreSQL** (primary) with **SQLite** (development/testing)
**Rationale:**
- PostgreSQL for production:
  - Better scalability for large gene datasets
  - Advanced indexing for complex queries
  - JSON support for flexible data storage
  - Battle-tested in bioinformatics
- SQLite for development:
  - Zero configuration
  - Single-file portability
  - Fast for small datasets

**Migration path:** Both supported by same ORM, easy to switch via config

**Sources:** [PostgreSQL vs SQLite comparison](https://www.datacamp.com/blog/sqlite-vs-postgresql-detailed-comparison)

### ORM: **SQLAlchemy 2.0** (with async support)
**Rationale:**
- Async support in 2.0+ (critical for FastAPI)
- Most mature and flexible Python ORM
- Supports both PostgreSQL and SQLite
- Excellent migration tools (Alembic)
- Alternative considered: Tortoise ORM (async-first, but less mature)

**Sources:** [ORM comparison 2024](https://betterstack.com/community/guides/scaling-python/tortoiseorm-vs-sqlalchemy/)

### Background Jobs: **ARQ** (Async Redis Queue)
**Rationale:**
- Built for asyncio (perfect fit with FastAPI)
- Redis-backed (simple deployment)
- Lightweight vs Celery
- Retry logic and job scheduling built-in
- Native async/await syntax

**Alternative considered:** Celery (too heavy, not async-native)

**Sources:** [Python task queue comparison](https://judoscale.com/blog/choose-python-task-queue)

### HTTP Client: **httpx** (async)
**Rationale:**
- Async/await support (parallel API calls)
- Drop-in replacement for requests
- HTTP/2 support
- Excellent for rate-limited APIs

**Sources:** [HTTPX web scraping guide](https://brightdata.com/blog/web-data/web-scraping-with-httpx)

### HTML Parsing: **BeautifulSoup4** + **lxml**
**Rationale:**
- BeautifulSoup for KEGG SSDB page scraping (replacing Nokogiri)
- lxml parser for speed
- Proven, stable, well-documented

### Additional Libraries
- **Pydantic**: Data validation and settings (built into FastAPI)
- **Alembic**: Database migrations
- **pytest** + **pytest-asyncio**: Testing framework
- **uvicorn**: ASGI server (production: uvicorn + gunicorn)

## Data Model Changes

### Organisms Table
```python
id: int (PK)
code: str (unique, indexed)  # e.g., "hsa", "eco"
name: str                     # e.g., "Homo sapiens"
status: str                   # null, "pending", "complete", "error"
job_error: str (nullable)
job_id: str (nullable)        # ARQ job ID
created_at: datetime
updated_at: datetime
```

### Genes Table
```python
id: int (PK)
organism_id: int (FK)
name: str (indexed)                    # e.g., "hsa:10458"
description: str
ortholog_name: str (nullable)
ortholog_description: str (nullable)
ortholog_species: str (nullable)
ortholog_length: int (nullable)
ortholog_sw_score: int (nullable)
ortholog_identity: float (nullable)    # 0.0-100.0
created_at: datetime
updated_at: datetime

# Composite index on (organism_id, ortholog_name) for queries
```

**Note:** No Users table needed - authentication removed per requirements

## Architecture Design

### Project Structure
```
kgene-v2/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app entry
│   │   ├── config.py           # Settings (Pydantic)
│   │   ├── database.py         # DB session management
│   │   ├── models/             # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── organism.py
│   │   │   └── gene.py
│   │   ├── schemas/            # Pydantic schemas (API)
│   │   │   ├── __init__.py
│   │   │   ├── organism.py
│   │   │   ├── gene.py
│   │   │   └── process.py
│   │   ├── api/                # API routes
│   │   │   ├── __init__.py
│   │   │   ├── organisms.py
│   │   │   ├── genes.py
│   │   │   └── processes.py
│   │   ├── services/           # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── kegg_api.py     # KEGG REST API client
│   │   │   └── ortholog_service.py  # Ortholog fetching
│   │   ├── workers/            # ARQ background jobs
│   │   │   ├── __init__.py
│   │   │   └── process_job.py
│   │   └── core/               # Utilities
│   │       ├── __init__.py
│   │       └── deps.py         # FastAPI dependencies
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_api/
│   │   ├── test_services/
│   │   └── test_workers/
│   ├── alembic/                # DB migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                   # React frontend
│   ├── public/
│   ├── src/
│   │   ├── api/                # API client functions
│   │   │   ├── organisms.ts
│   │   │   ├── genes.ts
│   │   │   └── processes.ts
│   │   ├── components/         # React components
│   │   │   ├── organisms/
│   │   │   ├── genes/
│   │   │   ├── processes/
│   │   │   └── shared/
│   │   ├── hooks/              # Custom React hooks
│   │   │   └── usePolling.ts
│   │   ├── pages/              # Page components
│   │   │   ├── Home.tsx
│   │   │   ├── Organisms.tsx
│   │   │   ├── ProcessManager.tsx
│   │   │   └── GeneExplorer.tsx
│   │   ├── types/              # TypeScript types
│   │   │   └── api.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── Dockerfile
│   └── .env.example
│
├── docker-compose.yml          # Multi-service orchestration
├── docker-compose.dev.yml      # Development overrides
├── nginx.conf                  # Nginx configuration
└── README.md
```

### API Endpoints (FastAPI)

#### Organisms
- `GET /api/organisms` - List all organisms
- `POST /api/organisms` - Create organism
- `GET /api/organisms/{id}` - Get organism details
- `PUT /api/organisms/{id}` - Update organism
- `DELETE /api/organisms/{id}` - Delete organism

#### Processes
- `GET /api/processes` - List processed organisms with status
- `POST /api/processes/{organism_id}/start` - Trigger processing
- `DELETE /api/processes/{organism_id}/results` - Remove results
- `GET /api/processes/{organism_id}/progress` - Get progress %
- `GET /api/processes/{organism_id}/orthologs` - Get genes with orthologs
- `GET /api/processes/{organism_id}/no-orthologs` - Get genes without
- `GET /api/processes/{organism_id}/download` - Download CSV

#### Genes
- `GET /api/genes?organism_id={id}` - List genes for organism

#### Health & Monitoring
- `GET /api/health` - Health check endpoint
- `GET /api/stats` - System statistics (jobs completed, organisms processed, etc.)

### KEGG API Client (`services/kegg_api.py`)

**Key Methods:**
```python
async def list_organism_genes(organism_code: str) -> list[dict]:
    """
    Fetch all genes for organism from KEGG REST API.
    URL: https://rest.kegg.jp/list/{organism_code}
    Returns: List of {name, description}
    Rate limit: 3 req/sec (use asyncio.sleep(0.35))
    """

async def get_gene_info(gene_id: str) -> dict:
    """
    Get detailed gene info including KO assignment.
    URL: https://rest.kegg.jp/get/{gene_id}
    May use for future enhancements
    """
```

**Implementation Notes:**
- Use `httpx.AsyncClient` with connection pooling
- Implement rate limiting (0.35s between calls)
- Retry logic for network errors
- Parse TSV response format

### KEGG SSDB Scraper (`services/kegg_scraper.py`)

**Key Methods:**
```python
async def get_best_ortholog(
    gene_name: str,
    exclude_organism: str
) -> dict | None:
    """
    Scrape KEGG SSDB for best non-self ortholog.
    URL: https://www.kegg.jp/ssdb-bin/ssdb_best_best?org_gene={gene_name}
    Returns: {name, description, species, length, sw_score, identity}
    """
```

**Implementation Notes:**
- Use `httpx` for async HTTP requests
- Parse HTML with BeautifulSoup4 + lxml
- Extract data from `<pre>` table format
- Handle cases where no ortholog found
- Respect rate limits

**⚠️ CRITICAL ISSUE:** SSDB web interface may have changed since 2015. Need to verify:
1. Does the URL pattern still work?
2. Is the HTML structure the same?
3. Is there a better API endpoint now?

### Background Job (`workers/process_job.py`)

**Job Flow:**
```python
async def process_organism(ctx: dict, organism_id: int):
    """
    ARQ job to process organism:
    1. Update status to 'pending'
    2. Fetch all genes from KEGG API
    3. Store genes in database
    4. For each gene, fetch ortholog (with concurrency control)
    5. Update status to 'complete' or 'error'
    """
```

**Concurrency Strategy:**
- Use `asyncio.Semaphore(10)` to limit concurrent SSDB scrapes
- Use `asyncio.gather()` for parallel execution
- Respect KEGG rate limit across all tasks
- Batch database inserts (e.g., 100 genes at a time)

**Error Handling:**
- Catch exceptions per gene (don't fail whole job)
- Store error in organism.job_error
- Retry transient errors (network issues)
- Log errors for debugging

## Implementation Phases

### Phase 1: Foundation (Week 1)
1. Set up Python project structure
2. Configure FastAPI + SQLAlchemy + PostgreSQL
3. Create database models (Organisms, Genes, Users)
4. Set up Alembic migrations
5. Basic CRUD API endpoints for organisms
6. Docker setup (FastAPI, PostgreSQL, Redis)

**Deliverable:** Basic API running with database

### Phase 2: KEGG Integration Research & Implementation (Week 2-3)
**Part A: Research (Week 2)**
1. **Implement basic KEGG REST API client** (`kegg_api.py`)
   - Test `/list/{organism}` endpoint
   - Verify rate limiting works
   - Parse gene lists successfully
2. **Research ortholog alternatives:**
   - Test KEGG KO API (`/link`, `/get` operations)
   - Investigate eggNOG API for ortholog data
   - Test OMA Browser API
   - Check OrthoDB availability
   - Document findings and recommendation
3. **Decision point:** Choose best ortholog data source

**Part B: Implementation (Week 3)**
1. Implement chosen ortholog fetching method
2. Handle rate limiting and retries
3. Unit tests for all services
4. Integration test with real organism (e.g., "eco" - E. coli, ~4300 genes)

**Deliverable:** Working KEGG data fetching with reliable ortholog source

### Phase 3: Background Jobs (Week 4)
1. Set up ARQ with Redis
2. Implement `process_organism` job
3. Create job management API endpoints
4. Implement progress tracking
5. Test with small organism (eco - E. coli)
6. Test with larger organism (hsa - Human, ~20k genes)

**Deliverable:** End-to-end organism processing

### Phase 4: Complete Backend API (Week 5)
1. Complete all API endpoints:
   - Processes with filtering/sorting
   - CSV download functionality
   - Progress monitoring
   - Error reporting
2. WebSocket support for real-time job updates (optional but recommended)
3. Error handling and validation
4. API documentation (auto-generated by FastAPI)
5. Comprehensive API test suite

**Deliverable:** Production-ready FastAPI backend

### Phase 5: React Frontend (Week 6-7)
1. **Project Setup:**
   - Create React + TypeScript + Vite project
   - Configure React Query for API calls
   - Set up routing (React Router)
   - Choose UI library (shadcn/ui recommended)

2. **Core Pages:**
   - Home/Dashboard
   - Organism list (create/edit organisms)
   - Process management (trigger jobs, view status)
   - Gene explorer (view orthologs, filter results)
   - CSV download

3. **Real-time Features:**
   - Progress bars for running jobs
   - Live updates (WebSocket or polling)
   - Error notifications

4. **Polish:**
   - Responsive design
   - Loading states
   - Error boundaries
   - Toast notifications

**Deliverable:** Complete modern SPA frontend

### Phase 6: Integration & Deployment (Week 8)
1. **Docker Compose Configuration:**
   - FastAPI service
   - PostgreSQL service
   - Redis service
   - Nginx service (serves React + proxies API)
   - Development vs production configs
2. **Build pipeline:**
   - Multi-stage Dockerfile for React build
   - Optimized production images
3. **Environment configuration:**
   - `.env.example` template
   - Docker secrets for production
4. **Deployment testing:**
   - Full stack deployment test
   - Performance testing
   - Load testing with multiple concurrent jobs

**Deliverable:** Production-ready deployment

### Phase 7: Documentation & Migration (Week 9)
1. **Documentation:**
   - API documentation (auto-generated + examples)
   - Deployment guide
   - Developer setup guide
   - Architecture diagrams
   - User guide
2. **Data migration (if needed):**
   - Export existing Oracle data
   - Import to PostgreSQL
   - Verify data integrity
3. **Final testing:**
   - End-to-end user acceptance testing
   - Performance benchmarks
   - Bug fixes

**Deliverable:** Fully documented, production-ready system

## Migration Strategy

### Data Migration
If migrating existing data from Oracle:
1. Export organisms and genes to CSV
2. Create migration script
3. Bulk insert to PostgreSQL
4. Verify data integrity

### Coexistence Strategy (if needed)
Run both systems in parallel:
1. Deploy Python app alongside Rails app
2. Migrate users gradually
3. Eventually retire Rails app

## Technical Decisions (FINALIZED)

### ✅ Frontend Approach: Modern SPA (React/Vue + TypeScript)
**Decision:** Build a modern single-page application
- **Framework:** React with TypeScript (or Vue 3 if preferred)
- **State Management:** React Query for server state, Zustand for client state
- **UI Library:** shadcn/ui or Ant Design (component library)
- **Build Tool:** Vite
- **Deployment:** Nginx serving static files, proxying API requests to FastAPI

**Architecture:**
```
Browser → Nginx → /api/* → FastAPI Backend
                → /* → React SPA
```

### ✅ Authentication: None Required
**Decision:** Remove authentication entirely
- No user registration/login
- Open access to all features
- Simpler deployment and maintenance
- Can add later if needed

**Impact:**
- Remove Users table/model
- No auth endpoints
- No Sidekiq web UI authentication (or make it read-only public)
- Simpler frontend (no login forms)

### ✅ Deployment Target: Docker Compose
**Decision:** Docker Compose for deployment
- **Services:** FastAPI, PostgreSQL, Redis, Nginx, React (built static files)
- **Development:** Same stack with hot reload
- **Production:** Production-optimized builds
- Single-server deployment suitable for academic use

### ✅ KEGG Strategy: Explore API Alternatives
**Decision:** Research KEGG API alternatives before implementing scraping

**Research Tasks (Phase 2):**
1. **Investigate KEGG KO API** for ortholog relationships
   - Can we get ortholog data via `/link` and `/get` operations?
   - Test with real examples
2. **Alternative databases:**
   - eggNOG (http://eggnog5.embl.de/) - has REST API
   - OMA Browser (https://omabrowser.org/api/) - ortholog database API
   - OrthoDB (https://www.orthodb.org/) - hierarchical orthologs
3. **Biopython integration** - May have helper functions
4. **Fall back:** If no good API exists, implement modern scraping

**Benefits:**
- More reliable than web scraping
- Potentially better ortholog detection
- Official APIs with support
- Less likely to break

## Risk Assessment

### High Risk
1. **KEGG SSDB scraping may not work** - URL/HTML may have changed
   - Mitigation: Test immediately, have backup plan

2. **KEGG rate limits** - 3 req/sec may be enforced differently
   - Mitigation: Implement conservative rate limiting, retry logic

### Medium Risk
1. **Data volume** - Large organisms take hours to process
   - Mitigation: Progress tracking, job resumption

2. **Web scraping fragility** - KEGG may change pages
   - Mitigation: Robust parsing, good error handling

### Low Risk
1. **Technology stack** - All components proven and mature
2. **Database migration** - Standard tools available

## Resources & References

### KEGG API
- [KEGG REST API Manual](https://www.kegg.jp/kegg/rest/keggapi.html)
- [KEGG API Documentation](https://www.kegg.jp/kegg/rest/)
- [KEGG GENES Database](https://www.genome.jp/kegg/genes.html)

### Framework Comparisons
- [FastAPI vs Django vs Flask](https://betterstack.com/community/guides/scaling-nodejs/fastapi-vs-django-vs-flask/)
- [Python ORM Comparison](https://betterstack.com/community/guides/scaling-python/tortoiseorm-vs-sqlalchemy/)
- [Task Queue Comparison](https://judoscale.com/blog/choose-python-task-queue)

### Database
- [PostgreSQL vs SQLite](https://www.datacamp.com/blog/sqlite-vs-postgresql-detailed-comparison)

### Web Scraping
- [HTTPX Guide](https://brightdata.com/blog/web-data/web-scraping-with-httpx)
- [Async Scraping](https://boadziedaniel.medium.com/fast-web-scraping-with-bs4-and-httpx-ec14f38dba7a)

## Next Steps

1. **Review and approve this plan**
2. **Answer clarifying questions** (frontend approach, auth requirements, deployment target)
3. **Verify KEGG SSDB access** - Test current scraping approach
4. **Set up development environment**
5. **Begin Phase 1 implementation**

## Success Criteria

- [ ] All current features replicated in Python
- [ ] Performance: Process organisms at least as fast as Rails app
- [ ] Reliability: <1% job failure rate (excluding KEGG downtime)
- [ ] Code quality: 80%+ test coverage
- [ ] Documentation: Complete API docs + deployment guide
- [ ] Modern tech stack: Python 3.11+, FastAPI, PostgreSQL
- [ ] Async throughout: All I/O operations use async/await
