"""
Test Configuration and Fixtures for KEGG Explore Backend

=== WHAT ARE FIXTURES? ===
Fixtures are reusable test setup functions provided by pytest.
Think of them as "test ingredients" - pieces of data or configuration
that multiple tests need. Pytest automatically injects them into test functions.

Example:
    def test_create_organism(db_session):  # pytest auto-injects db_session
        organism = Organism(code="eco", name="E. coli")
        db_session.add(organism)
        await db_session.commit()
        assert organism.id is not None

=== WHY FIXTURES? ===
Without fixtures, every test would need to:
1. Set up database connection
2. Create tables
3. Insert test data
4. Run the test
5. Clean up database

Fixtures handle steps 1-3 and 5 automatically, so tests focus on step 4.

=== FIXTURE SCOPES ===
- function (default): New instance for every test (isolated, slow)
- module: Shared across all tests in one file (faster, less isolated)
- session: Shared across entire test run (fastest, least isolated)

We use 'function' scope for database to ensure test isolation.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

# SQLAlchemy async imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# FastAPI testing
from httpx import AsyncClient
from app.main import app

# Database models
from app.database import Base
from app.models.organism import Organism
from app.models.gene import Gene

# Services
from app.services.kegg_api import KEGGClient
from app.services.ortholog_service import OrthologResult

# Fakeredis for Redis mocking
import fakeredis.aioredis


# =============================================================================
# DATABASE FIXTURES - SQLite In-Memory for Fast Testing
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """
    Create an in-memory SQLite database engine for testing.

    WHY SQLITE IN-MEMORY?
    - Fast: No disk I/O, runs in RAM
    - Isolated: Each test gets fresh database
    - No Docker: Works without external dependencies
    - SQLAlchemy compatible: Uses same ORM as PostgreSQL

    WHY StaticPool?
    In-memory SQLite databases exist only for one connection.
    StaticPool ensures all sessions share the same connection,
    so the database persists across queries within the test.

    CLEANUP:
    After test finishes, engine.dispose() closes connection and
    the in-memory database disappears automatically.
    """
    # Create in-memory SQLite engine
    # check_same_thread=False allows async usage
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Critical for in-memory databases
    )

    # Create all tables (organisms, genes)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: Close all connections
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for tests.

    WHAT IS A SESSION?
    A session is like a "shopping cart" for database operations:
    - Add items (models) to cart: session.add(organism)
    - Checkout (commit): session.commit() saves to database
    - Abandon cart (rollback): session.rollback() discards changes

    WHY ASYNC SESSION?
    Our entire backend uses async/await for non-blocking I/O.
    AsyncSession allows database queries without blocking the event loop.

    CLEANUP:
    After each test, we rollback any uncommitted changes and close the session.
    This ensures tests don't interfere with each other.
    """
    # Create async session factory
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects accessible after commit
    )

    async with async_session_maker() as session:
        yield session
        # Cleanup: Rollback any uncommitted changes
        await session.rollback()


# =============================================================================
# MODEL FIXTURES - Sample Database Objects
# =============================================================================


@pytest_asyncio.fixture
async def sample_organism(db_session: AsyncSession) -> Organism:
    """
    Create a sample organism in the test database.

    BIOINFORMATICS CONTEXT:
    This represents E. coli K-12 MG1655, a widely-used model organism.
    It's small (~4,600 genes) making it perfect for testing without
    waiting 30+ minutes for larger genomes.

    USAGE:
        async def test_fetch_genes(sample_organism, db_session):
            genes = await fetch_genes_for_organism(sample_organism.id)
            assert len(genes) > 0
    """
    organism = Organism(
        code="eco",
        name="Escherichia coli K-12 MG1655",
        status=None,  # Not yet processed
    )
    db_session.add(organism)
    await db_session.commit()
    await db_session.refresh(organism)  # Get auto-generated ID
    return organism


@pytest_asyncio.fixture
async def sample_genes(db_session: AsyncSession, sample_organism: Organism) -> list[Gene]:
    """
    Create sample genes for testing.

    BIOINFORMATICS CONTEXT:
    These are actual E. coli genes from KEGG:
    - b0001: thrL (threonine operon leader peptide)
    - b0002: thrA (aspartokinase/homoserine dehydrogenase)
    - b0003: thrB (homoserine kinase)
    - b0004: thrC (threonine synthase)

    WHY THESE GENES?
    - First genes in E. coli genome (easy to remember)
    - Well-characterized (known orthologs in other organisms)
    - Diverse functional roles (good for testing ortholog discovery)
    """
    genes_data = [
        {
            "name": "eco:b0001",
            "description": "CDS\t190..255\tthrL; thr operon leader peptide",
            "organism_id": sample_organism.id,
        },
        {
            "name": "eco:b0002",
            "description": "CDS\t337..2799\tthrA; aspartokinase",
            "organism_id": sample_organism.id,
        },
        {
            "name": "eco:b0003",
            "description": "CDS\t2801..3733\tthrB; homoserine kinase",
            "organism_id": sample_organism.id,
        },
        {
            "name": "eco:b0004",
            "description": "CDS\t3734..5020\tthrC; threonine synthase",
            "organism_id": sample_organism.id,
        },
    ]

    genes = [Gene(**data) for data in genes_data]
    db_session.add_all(genes)
    await db_session.commit()

    # Refresh to get auto-generated IDs
    for gene in genes:
        await db_session.refresh(gene)

    return genes


@pytest_asyncio.fixture
async def organism_with_genes(sample_organism: Organism, sample_genes: list[Gene]) -> Organism:
    """
    Convenience fixture: organism already populated with genes.

    USAGE:
        async def test_count_genes(organism_with_genes, db_session):
            count = await db_session.query(Gene).filter_by(
                organism_id=organism_with_genes.id
            ).count()
            assert count == 4
    """
    return sample_organism


# =============================================================================
# MOCK FIXTURES - Fake External Dependencies
# =============================================================================


@pytest.fixture
def mock_kegg_client():
    """
    Mock KEGG API client to avoid real API calls during tests.

    WHY MOCK THE KEGG API?
    - Speed: Real API calls take seconds, mock calls take microseconds
    - Determinism: Real API changes over time, mocks return predictable data
    - No rate limits: KEGG limits to 3 req/sec, mocks are unlimited
    - Works offline: No internet connection needed for tests

    HOW TO USE:
        def test_fetch_genes(mock_kegg_client):
            client = mock_kegg_client
            client.list_organism_genes.return_value = [
                {"name": "eco:b0001", "description": "test gene"}
            ]

            result = await client.list_organism_genes("eco")
            assert len(result) == 1

    CUSTOMIZING RESPONSES:
    Each test can override return values:
        mock_kegg_client.list_organism_genes.return_value = custom_data
    """
    mock = AsyncMock(spec=KEGGClient)

    # Default responses for common operations
    mock.list_organism_genes.return_value = [
        {"name": "eco:b0001", "description": "CDS\t190..255\tthrL"},
        {"name": "eco:b0002", "description": "CDS\t337..2799\tthrA"},
    ]

    mock.link_genes_to_ko.return_value = {
        "eco:b0001": ["K01234"],
        "eco:b0002": ["K05678"],
    }

    mock.get_organisms_by_ko.return_value = [
        "eco:b0001",
        "hsa:12345",  # Human ortholog
        "mmu:67890",  # Mouse ortholog
    ]

    return mock


@pytest_asyncio.fixture
async def fake_redis():
    """
    In-memory Redis simulation using fakeredis.

    WHY FAKEREDIS?
    - No Docker: No need to run actual Redis server
    - Fast: Pure Python implementation in RAM
    - Compatible: Same API as real redis-py
    - Isolated: Each test gets fresh Redis instance

    WHAT DOES IT SUPPORT?
    - All basic Redis commands: GET, SET, SETEX, DEL, KEYS, etc.
    - Expiration (TTL): SETEX automatically expires keys
    - Async operations: Works with async/await

    LIMITATIONS:
    - Not 100% compatible with Redis (some advanced features missing)
    - No persistence (data lost when test ends)
    - Single-threaded (no concurrency testing)

    USAGE:
        async def test_progress_tracking(fake_redis):
            await fake_redis.setex("progress:job123", 3600, '{"progress": 50}')
            data = await fake_redis.get("progress:job123")
            assert '"progress": 50' in data
    """
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.close()


@pytest.fixture
def mock_arq_pool():
    """
    Mock ARQ connection pool for testing job enqueueing.

    WHAT IS ARQ?
    ARQ (Async Redis Queue) is our background job system.
    Jobs are enqueued via an ARQ pool, then workers pick them up.

    WHY MOCK ARQ?
    - Tests shouldn't actually enqueue jobs to Redis
    - We want to test job enqueueing logic, not ARQ itself
    - Faster tests (no Redis connection overhead)

    USAGE:
        async def test_start_processing(mock_arq_pool):
            job = await mock_arq_pool.enqueue_job(
                "process_organism_job",
                organism_id=123
            )
            assert job.job_id is not None
            mock_arq_pool.enqueue_job.assert_called_once_with(
                "process_organism_job",
                organism_id=123
            )
    """
    mock = AsyncMock()

    # Mock job object returned by enqueue_job
    mock_job = MagicMock()
    mock_job.job_id = "test_job_123"
    mock.enqueue_job.return_value = mock_job

    return mock


# =============================================================================
# SAMPLE DATA FIXTURES - KEGG API Response Examples
# =============================================================================


@pytest.fixture
def kegg_gene_list_response() -> str:
    """
    Sample TSV response from KEGG /list endpoint.

    KEGG API FORMAT:
    Each line: <gene_id>\t<description>

    BIOINFORMATICS CONTEXT:
    This is actual data from KEGG for E. coli genes.
    The format is:
    - eco:b0001: Organism code + gene locus tag
    - CDS\t190..255: Gene location in genome
    - thrL: Gene symbol
    - Description: Protein function
    """
    return """eco:b0001\tCDS\t190..255\tthrL; thr operon leader peptide
eco:b0002\tCDS\t337..2799\tthrA; aspartokinase I/homoserine dehydrogenase I
eco:b0003\tCDS\t2801..3733\tthrB; homoserine kinase
eco:b0004\tCDS\t3734..5020\tthrC; threonine synthase"""


@pytest.fixture
def kegg_ko_mapping_response() -> str:
    """
    Sample TSV response from KEGG /link/ko endpoint.

    KEGG API FORMAT:
    Each line: <gene_id>\t<ko_id>

    BIOINFORMATICS CONTEXT:
    KO (KEGG Orthology) groups are collections of genes with the same function.
    Example: K00001 = alcohol dehydrogenase across all organisms

    This mapping links specific genes to their KO groups.
    """
    return """eco:b0001\tko:K01234
eco:b0002\tko:K00928
eco:b0003\tko:K00872
eco:b0004\tko:K01733"""


@pytest.fixture
def kegg_organisms_in_ko_response() -> str:
    """
    Sample TSV response from KEGG /link/genes/<ko_id> endpoint.

    KEGG API FORMAT:
    Each line: <ko_id>\t<gene_id>

    BIOINFORMATICS CONTEXT:
    For a given KO group, this returns all genes across all organisms.
    These genes are potential orthologs (same function, different species).

    EXAMPLE:
    K00928 (aspartokinase) exists in:
    - eco:b0002 (E. coli)
    - hsa:5236 (human THRSP gene)
    - mmu:21881 (mouse Thrsp gene)
    - ath:AT3G51000 (Arabidopsis gene)
    """
    return """ko:K00928\teco:b0002
ko:K00928\thsa:5236
ko:K00928\tmmu:21881
ko:K00928\tath:AT3G51000
ko:K00928\tsce:YHR161C"""


# =============================================================================
# API FIXTURES - FastAPI Test Client
# =============================================================================


@pytest_asyncio.fixture
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI test client for testing API endpoints.

    WHAT IS AsyncClient?
    httpx.AsyncClient is like requests.get() but async-compatible.
    It sends HTTP requests to our FastAPI app without starting a real server.

    HOW IT WORKS:
    1. FastAPI's TestClient wraps the app
    2. Requests go through full middleware stack
    3. Database queries use our test db_session
    4. Responses returned as if from real HTTP server

    USAGE:
        async def test_create_organism(test_client):
            response = await test_client.post(
                "/api/organisms",
                json={"code": "eco", "name": "E. coli"}
            )
            assert response.status_code == 201
            data = response.json()
            assert data["code"] == "eco"

    DATABASE OVERRIDE:
    We override app's database dependency to use our test database.
    This ensures API tests use the same in-memory SQLite as unit tests.
    """
    # Override database dependency to use test database
    from app.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Cleanup: Remove override
    app.dependency_overrides.clear()


# =============================================================================
# SAMPLE ORTHOLOG RESULTS - For Testing Ortholog Service
# =============================================================================


@pytest.fixture
def sample_ortholog_results() -> list[OrthologResult]:
    """
    Sample ortholog discovery results for testing.

    BIOINFORMATICS CONTEXT:
    OrthologResult represents the output of ortholog discovery:
    - gene_id: Source gene (eco:b0002)
    - ortholog_gene_id: Best matching gene in different organism (hsa:5236)
    - ortholog_species: Target organism code (hsa = Homo sapiens)
    - ko_id: Shared KO group (K00928)
    - confidence: Score 0-100 (based on evolutionary distance)
    - method: How ortholog was found (KEGG_KO, MANUAL, etc.)

    EXAMPLE INTERPRETATION:
    E. coli gene b0002 (aspartokinase) has an ortholog in humans (hsa:5236).
    Both genes belong to KO group K00928 (aspartokinase family).
    Confidence is 85/100 (high confidence match).
    """
    return [
        OrthologResult(
            gene_id="eco:b0002",
            ortholog_gene_id="hsa:5236",
            ortholog_species="hsa",
            ko_id="K00928",
            confidence=85.0,
            method="KEGG_KO",
        ),
        OrthologResult(
            gene_id="eco:b0003",
            ortholog_gene_id="mmu:21881",
            ortholog_species="mmu",
            ko_id="K00872",
            confidence=90.0,
            method="KEGG_KO",
        ),
        # Gene with no ortholog found
        OrthologResult(
            gene_id="eco:b0001",
            ko_id=None,
            method="NO_KO_ASSIGNMENT",
        ),
    ]


# =============================================================================
# EVENT LOOP FIXTURE - For Async Tests
# =============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.

    WHY THIS FIXTURE?
    pytest-asyncio creates a new event loop for each test by default.
    For session-scoped fixtures (like database), we need a session-scoped loop.

    WHAT IS AN EVENT LOOP?
    The event loop is the core of asyncio. It:
    1. Schedules async tasks
    2. Manages I/O operations
    3. Coordinates coroutines

    This ensures all async fixtures and tests share the same loop.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

"""
EXAMPLE TEST USING FIXTURES:

    @pytest.mark.unit
    async def test_create_and_query_organism(db_session):
        # Arrange: Create test data
        organism = Organism(code="eco", name="E. coli")
        db_session.add(organism)
        await db_session.commit()

        # Act: Query the database
        result = await db_session.get(Organism, organism.id)

        # Assert: Verify results
        assert result.code == "eco"
        assert result.name == "E. coli"


    @pytest.mark.integration
    async def test_api_create_organism(test_client):
        # Act: Make API request
        response = await test_client.post(
            "/api/organisms",
            json={"code": "eco", "name": "E. coli"}
        )

        # Assert: Check response
        assert response.status_code == 201
        data = response.json()
        assert data["code"] == "eco"


    @pytest.mark.unit
    async def test_kegg_client_mock(mock_kegg_client):
        # Arrange: Configure mock response
        mock_kegg_client.list_organism_genes.return_value = [
            {"name": "eco:b0001", "description": "test"}
        ]

        # Act: Call mocked method
        result = await mock_kegg_client.list_organism_genes("eco")

        # Assert: Verify mock was called correctly
        assert len(result) == 1
        mock_kegg_client.list_organism_genes.assert_called_once_with("eco")
"""
