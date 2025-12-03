"""
Processes API - Job Management Endpoints

=== WHAT ARE "PROCESSES"? ===

In this context, a "process" is a background job that processes an organism:
- Fetches genes from KEGG API
- Finds orthologs for each gene
- Stores results in database

The term "process" (verb) comes from the original Rails app's ProcessesController.
It means "to process an organism" (analyze it, find its orthologs).

=== API ENDPOINTS ===

1. **POST /api/processes/{organism_id}/start**
   - Triggers background job to process organism
   - Returns: Job ID and status

2. **GET /api/processes/{organism_id}/progress**
   - Gets real-time progress of job (0-100%)
   - Returns: Progress data from Redis

3. **DELETE /api/processes/{organism_id}/results**
   - Deletes all genes for organism (clears results)
   - Resets organism status to null

4. **GET /api/processes**
   - Lists all organisms with their processing status
   - Useful for dashboard/overview

=== USER WORKFLOW ===

Typical user flow:

```
1. Create organism:
   POST /api/organisms {"code": "eco", "name": "E. coli"}
   → Returns: {"id": 123, "status": null}

2. Start processing:
   POST /api/processes/123/start
   → Returns: {"job_id": "abc-123", "status": "pending"}

3. Monitor progress (poll every 2-3 seconds):
   GET /api/processes/123/progress
   → Returns: {"progress": 45.5, "stage": "finding_orthologs", ...}

4. Query results:
   GET /api/genes?organism_id=123
   → Returns: [list of genes with orthologs]

5. Download CSV:
   GET /api/processes/123/download
   → Returns: CSV file
```

=== ARQ JOB ENQUEUING ===

**How jobs get from API → Worker:**

1. API receives POST /api/processes/123/start
2. API connects to Redis
3. API calls: `await redis.enqueue_job('process_organism_job', 123)`
4. ARQ stores job in Redis queue: "arq:queue"
5. Worker polls Redis every 100ms
6. Worker sees job, dequeues it
7. Worker executes: `await process_organism_job(ctx, 123)`

**Redis Structure:**
```
Queue: arq:queue (list of job IDs)
Job: arq:job:{job_id} (job metadata)
Result: arq:result:{job_id} (job result after completion)
Progress: progress:{job_id} (our custom progress tracking)
```

=== ERROR HANDLING ===

**Idempotent Operations:**
- Starting a job that's already running → Returns existing job ID
- Deleting results that don't exist → Returns 204 (success)
- Getting progress for completed job → Falls back to database status

**Validation:**
- Organism must exist → 404 Not Found
- Invalid status transitions → 400 Bad Request
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from arq import create_pool
from arq.connections import RedisSettings
import redis.asyncio as async_redis

from app.core.exceptions import OrganismNotFoundError
from app.database import get_db
from app.models import Organism, Gene
from app.schemas.organism import Organism as OrganismSchema, OrganismWithProgress
from app.config import get_settings
from app.workers.progress_tracker import ProgressTracker
from app.services.csv_export import export_organism_genes_csv, get_csv_filename

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


# === REDIS CONNECTION POOL ===
#
# WHY A POOL?
# Creating a new Redis connection for every API request is slow (~10-50ms).
# A connection pool reuses connections (< 1ms per request).
#
# ARQ vs Redis Client:
# - ARQ pool: For enqueuing jobs (arq.create_pool)
# - Redis client: For progress queries (redis.asyncio.Redis)
#
# We use ARQ pool for job operations, Redis client for progress tracking.

_arq_pool = None  # Global ARQ pool (initialized on first use)
_redis_client = None  # Global Redis client (initialized on first use)


async def get_arq_pool():
    """
    Get ARQ connection pool for enqueueing jobs.

    This is a dependency injection function for FastAPI.
    FastAPI will call this once and cache the pool.

    SINGLETON PATTERN:
    We create the pool once on first use, then reuse it.
    This avoids creating 100s of connections.

    ASYNC CONTEXT:
    The pool is async, so we use 'await' to create it.
    """
    global _arq_pool

    if _arq_pool is None:
        # Parse Redis URL into connection settings
        # settings.redis_url = "redis://localhost:6379/0"
        redis_settings = RedisSettings.from_dsn(settings.redis_url)

        # IMPORTANT: Specify the queue name to match the worker's queue
        # Without this, the API enqueues to "arq:queue" (default)
        # but the worker listens to "kgene:queue" (from settings)
        #
        # The default_queue_name parameter tells ARQ which queue to use
        # when calling enqueue_job() on this pool
        _arq_pool = await create_pool(
            redis_settings,
            default_queue_name=settings.arq_queue_name
        )
        logger.info(f"Created ARQ connection pool (queue: {settings.arq_queue_name})")

    return _arq_pool


async def get_redis_client():
    """
    Get Redis client for progress tracking queries.

    Separate from ARQ pool because:
    - ARQ pool is for job operations (enqueue, dequeue)
    - Redis client is for data operations (get, set, delete)
    """
    global _redis_client

    if _redis_client is None:
        # Create Redis client from URL
        _redis_client = async_redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True  # Auto-decode bytes to strings
        )
        logger.info("Created Redis client")

    return _redis_client


# === API ENDPOINTS ===


@router.post("/processes/{organism_id}/start")
async def start_processing(
    organism_id: int,
    db: AsyncSession = Depends(get_db),
    arq_pool=Depends(get_arq_pool)
):
    """
    Start background job to process an organism.

    **Args:**
    - organism_id: Database ID of organism to process

    **Returns:**
    - job_id: Unique ID for tracking this job
    - status: "pending" (job is queued but not started yet)
    - message: Human-readable status message

    **Errors:**
    - 404: Organism not found
    - 400: Organism is already being processed

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/processes/123/start
    ```

    Response:
    ```json
    {
        "job_id": "abc123def456",
        "status": "pending",
        "message": "Processing started for E. coli"
    }
    ```

    **BIOINFORMATICS NOTE:**
    This doesn't actually process the organism immediately.
    It adds the job to a queue (Redis), and a worker picks it up.
    Think of it like placing an order at a restaurant - you get a receipt (job_id),
    then wait for the chef (worker) to prepare it.
    """

    # === VALIDATE ORGANISM EXISTS ===

    result = await db.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    organism = result.scalar_one_or_none()

    if not organism:
        raise OrganismNotFoundError(organism_id=organism_id)

    # === CHECK IF ALREADY PROCESSING ===

    # IDEMPOTENT CHECK:
    # If organism is already "pending", don't start another job.
    # This prevents duplicate processing if user clicks button multiple times.
    if organism.status == "pending":
        logger.warning(f"Organism {organism_id} is already being processed (job: {organism.job_id})")
        return {
            "job_id": organism.job_id,
            "status": "pending",
            "message": f"Organism {organism.code} is already being processed"
        }

    # === ENQUEUE JOB ===

    # ARQ enqueue_job syntax:
    # await pool.enqueue_job(
    #     function_name: str,     # Must match function in WorkerSettings.functions
    #     *args,                  # Positional arguments to pass to function
    #     **kwargs                # Keyword arguments (optional)
    # )
    #
    # Returns: Job object with .job_id attribute
    #
    # The job is stored in Redis as: arq:job:{job_id}
    # The worker polls "arq:queue" and finds this job
    job = await arq_pool.enqueue_job(
        "process_organism_job",  # Function name (must match exactly!)
        organism_id              # Argument: organism_id to process
    )

    job_id = job.job_id

    logger.info(f"Enqueued processing job for organism {organism_id} (job: {job_id})")

    # === UPDATE ORGANISM STATUS ===

    # Mark organism as "pending" so UI shows it's processing
    # Store job_id so we can track/cancel if needed
    organism.status = "pending"
    organism.job_id = job_id
    organism.job_error = None  # Clear any previous error
    await db.commit()

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Processing started for {organism.name} ({organism.code})"
    }


@router.get("/processes/{organism_id}/progress")
async def get_progress(
    organism_id: int,
    db: AsyncSession = Depends(get_db),
    redis_client=Depends(get_redis_client)
):
    """
    Get real-time processing progress for an organism.

    **Args:**
    - organism_id: Database ID of organism

    **Returns:**
    Progress data with:
    - status: "not_started", "pending", "in_progress", "complete", "error"
    - progress: Percentage (0-100)
    - stage: Current stage name
    - genes_processed: Number of genes processed
    - total_genes: Total genes to process
    - genes_with_orthologs: Count of genes with orthologs found
    - started_at: ISO timestamp when job started
    - updated_at: ISO timestamp of last update

    **Example:**
    ```bash
    curl http://localhost:8000/api/processes/123/progress
    ```

    Response (in progress):
    ```json
    {
        "status": "in_progress",
        "progress": 67.5,
        "stage": "finding_orthologs",
        "genes_processed": 3100,
        "total_genes": 4600,
        "genes_with_orthologs": 2300,
        "started_at": "2024-11-29T10:30:00Z",
        "updated_at": "2024-11-29T10:45:00Z"
    }
    ```

    Response (complete):
    ```json
    {
        "status": "complete",
        "progress": 100.0,
        "total_genes": 4600,
        "genes_with_orthologs": 3400,
        "coverage_percent": 73.9
    }
    ```

    **POLLING RECOMMENDATION:**
    Poll this endpoint every 2-3 seconds while status is "in_progress".
    Stop polling when status is "complete" or "error".
    """

    # === GET ORGANISM ===

    result = await db.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    organism = result.scalar_one_or_none()

    if not organism:
        raise OrganismNotFoundError(organism_id=organism_id)

    # === CHECK REDIS PROGRESS (Real-time) ===

    if organism.job_id:
        # Try to get real-time progress from Redis
        tracker = ProgressTracker(redis_client, organism.job_id)
        progress_data = await tracker.get_progress()

        if progress_data:
            # Job is running or recently completed
            # Progress data exists in Redis
            return {
                "status": "in_progress" if progress_data["progress"] < 100 else "complete",
                "organism_code": progress_data.get("organism_code"),
                **progress_data  # Include all progress fields
            }

    # === FALLBACK TO DATABASE STATUS ===

    # Progress data not in Redis (job completed >24 hours ago, or never started)
    # Fall back to database status

    if organism.status == "complete":
        # Job completed - get gene counts from database
        result = await db.execute(
            select(
                func.count(Gene.id).label("total"),
                func.count(Gene.ortholog_name).label("with_orthologs")
            ).where(Gene.organism_id == organism_id)
        )
        counts = result.one()

        coverage = (counts.with_orthologs / counts.total * 100) if counts.total > 0 else 0.0

        return {
            "status": "complete",
            "progress": 100.0,
            "total_genes": counts.total,
            "genes_with_orthologs": counts.with_orthologs,
            "coverage_percent": round(coverage, 2),
            "organism_code": organism.code
        }

    elif organism.status == "error":
        return {
            "status": "error",
            "progress": 0.0,
            "error_message": organism.job_error,
            "organism_code": organism.code
        }

    elif organism.status == "pending":
        # Job is queued but not started yet
        return {
            "status": "pending",
            "progress": 0.0,
            "message": "Job is queued, waiting for worker",
            "organism_code": organism.code
        }

    else:
        # Status is null - never processed
        return {
            "status": "not_started",
            "progress": 0.0,
            "organism_code": organism.code
        }


@router.delete("/processes/{organism_id}/results", status_code=status.HTTP_204_NO_CONTENT)
async def delete_results(
    organism_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete all processing results for an organism.

    This removes:
    - All genes for this organism
    - Resets organism status to null
    - Clears job_id and job_error

    Use this to:
    - Clear old results before re-processing
    - Free up database space
    - Reset organism to initial state

    **Args:**
    - organism_id: Database ID of organism

    **Returns:**
    - 204 No Content (success, no body)

    **Example:**
    ```bash
    curl -X DELETE http://localhost:8000/api/processes/123/results
    ```

    **WARNING:** This is destructive! All ortholog data will be lost.
    Consider archiving data before deleting if needed.
    """

    # === VALIDATE ORGANISM EXISTS ===

    result = await db.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    organism = result.scalar_one_or_none()

    if not organism:
        raise OrganismNotFoundError(organism_id=organism_id)

    # === DELETE GENES ===

    # CASCADE DELETE:
    # Deleting genes cascades to related records (if any in future).
    # The Gene model has: ForeignKey(..., ondelete="CASCADE")
    await db.execute(
        delete(Gene).where(Gene.organism_id == organism_id)
    )

    logger.info(f"Deleted all genes for organism {organism_id}")

    # === RESET ORGANISM STATUS ===

    organism.status = None
    organism.job_id = None
    organism.job_error = None
    await db.commit()

    logger.info(f"Reset organism {organism_id} status")

    # Return 204 No Content (success, empty body)
    return None


@router.get("/processes", response_model=List[OrganismWithProgress])
async def list_processes(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all organisms with their processing status.

    **Query Parameters:**
    - status: Filter by status ("pending", "complete", "error", null)

    **Returns:**
    List of organisms with:
    - Basic organism info (id, code, name)
    - Processing status
    - Gene counts (if processed)

    **Example:**
    ```bash
    # Get all organisms
    curl http://localhost:8000/api/processes

    # Get only completed organisms
    curl http://localhost:8000/api/processes?status=complete

    # Get organisms with errors
    curl http://localhost:8000/api/processes?status=error
    ```

    Response:
    ```json
    [
        {
            "id": 123,
            "code": "eco",
            "name": "Escherichia coli",
            "status": "complete",
            "total_genes": 4600,
            "genes_with_orthologs": 3400,
            "coverage_percent": 73.9
        },
        ...
    ]
    ```

    **USE CASE:**
    Display a dashboard of all processed organisms with their status.
    Users can see at a glance which organisms are done, which are processing,
    and which had errors.
    """

    # Build query
    query = select(Organism)

    if status_filter:
        query = query.where(Organism.status == status_filter)

    # Execute query
    result = await db.execute(query.order_by(Organism.updated_at.desc()))
    organisms = result.scalars().all()

    # Enhance with gene counts
    result_list = []
    for organism in organisms:
        # Get gene counts
        counts_result = await db.execute(
            select(
                func.count(Gene.id).label("total"),
                func.count(Gene.ortholog_name).label("with_orthologs")
            ).where(Gene.organism_id == organism.id)
        )
        counts = counts_result.one()

        coverage = (counts.with_orthologs / counts.total * 100) if counts.total > 0 else 0.0

        result_list.append({
            "id": organism.id,
            "code": organism.code,
            "name": organism.name,
            "status": organism.status,
            "job_id": organism.job_id,
            "job_error": organism.job_error,
            "created_at": organism.created_at,
            "updated_at": organism.updated_at,
            "total_genes": counts.total,
            "genes_with_orthologs": counts.with_orthologs,
            "coverage_percent": round(coverage, 2) if counts.total > 0 else None
        })

    return result_list


@router.get("/processes/{organism_id}/download")
async def download_organism_genes(
    organism_id: int,
    include_no_orthologs: bool = Query(
        True,
        description="Include genes without orthologs (orphan genes)"
    ),
    db: AsyncSession = Depends(get_db)
):
    """
    Download all genes for an organism as CSV.

    **What**: Exports gene and ortholog data to CSV format
    **Why**: Researchers need data for analysis in Excel, R, Python, etc.
    **Format**: CSV with gene name, description, ortholog info

    **Query Parameters**:
    - include_no_orthologs: Include genes without orthologs (default: true)

    **CSV Columns**:
    - gene_name: KEGG gene ID (e.g., "eco:b0001")
    - gene_description: Gene function from KEGG
    - ortholog_name: Best ortholog gene ID
    - ortholog_description: Ortholog function
    - ortholog_species: Organism name (e.g., "Homo sapiens")
    - ortholog_length: Sequence length
    - ortholog_sw_score: Smith-Waterman alignment score
    - ortholog_identity: Sequence identity percentage (0-100)

    **Examples**:
    ```bash
    # Download all genes (including those without orthologs)
    curl -O http://localhost:8000/api/processes/1/download

    # Download only genes WITH orthologs found
    curl -O http://localhost:8000/api/processes/1/download?include_no_orthologs=false
    ```

    **Bioinformatics Note**:
    Genes without orthologs (orphan genes) are included by default because:
    - They're scientifically interesting (species-specific genes)
    - Researchers want complete datasets
    - Empty ortholog columns clearly show "no match found"

    **Returns**: CSV file as streaming response
    - Content-Type: text/csv
    - Content-Disposition: attachment (triggers download)
    - Filename: {organism_code}_genes.csv
    """
    # Verify organism exists and get code
    result = await db.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    organism = result.scalar_one_or_none()

    if not organism:
        raise OrganismNotFoundError(organism_id=organism_id)

    # Generate CSV filename
    filename = get_csv_filename(organism.code, include_no_orthologs)

    logger.info(
        f"Exporting genes for organism {organism_id} ({organism.code}) "
        f"to CSV (include_no_orthologs={include_no_orthologs})"
    )

    # Stream CSV response
    # **Why streaming**: Efficient for large datasets (4,600+ genes for E. coli)
    # **Memory usage**: Generates CSV in chunks, never loads all data at once
    return StreamingResponse(
        export_organism_genes_csv(db, organism_id, include_no_orthologs),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# Export router for main.py to include
__all__ = ['router']
