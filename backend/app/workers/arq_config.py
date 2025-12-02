"""
ARQ Worker Configuration

=== WHAT IS ARQ? ===
ARQ (Async Redis Queue) is a task queue system for Python's asyncio.
It's like Sidekiq (Rails) or Celery (Python), but designed specifically for async/await.

Think of it like a restaurant:
- API endpoint = Customer placing order
- Redis = Order queue (sticky notes on the wall)
- ARQ Worker = Chef who picks up orders and cooks them
- Background job = The actual cooking process

=== WHY USE ARQ? ===
1. **Async-native**: Works perfectly with our FastAPI async codebase
2. **Simple**: Much lighter weight than Celery
3. **Built-in features**: Retries, timeouts, scheduled jobs all included
4. **Fast**: Redis is in-memory, so job dispatch is <1ms

=== HOW IT WORKS ===
1. API enqueues job → `await redis.enqueue_job('process_organism', organism_id)`
2. Job stored in Redis with unique ID
3. Worker polls Redis for new jobs (100ms interval)
4. Worker executes job function asynchronously
5. Result stored in Redis with expiration

This file configures the ARQ worker behavior.
"""

import logging
from arq.connections import RedisSettings
from app.config import get_settings

# Import job functions that will be registered with ARQ
# These will be available for enqueuing via the API
from app.workers.process_job import process_organism_job

settings = get_settings()
logger = logging.getLogger(__name__)


class WorkerSettings:
    """
    ARQ Worker Configuration

    This class defines how the ARQ worker behaves:
    - Which Redis to connect to
    - Which job functions are available
    - How many jobs can run concurrently
    - How long before jobs timeout
    - How long to keep job results

    IMPORTANT: This is used by the worker process, NOT the FastAPI app.
    The worker is a separate Python process that runs `arq worker`.
    """

    # === REDIS CONNECTION ===
    # Parse Redis URL into connection settings
    # Example: redis://localhost:6379/0 → host=localhost, port=6379, database=0
    #
    # WHY DATABASE 0? Redis has 16 databases (0-15) by default
    # We use database 0 for both the job queue and progress tracking
    # This keeps everything in one place and simplifies deployment
    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    # === AVAILABLE JOB FUNCTIONS ===
    # List of async functions that can be enqueued as jobs
    # When you call `await pool.enqueue_job('process_organism_job', 123)`,
    # ARQ looks for 'process_organism_job' in this list
    #
    # BIOINFORMATICS NOTE: We only have one job type (process organism)
    # In future, could add: validate_organism, export_results, etc.
    functions = [process_organism_job]

    # === CONCURRENCY LIMIT ===
    # Maximum number of jobs that can run at the same time
    #
    # WHY 10? Trade-off between:
    # - Speed: More concurrent jobs = faster processing of multiple organisms
    # - KEGG rate limits: Each job hits KEGG API, 10 jobs * 3 req/sec = 30 req/sec total
    # - Memory: Each job holds ~50-100MB (gene data), so 10 jobs = ~1GB max
    # - Database connections: Each job needs 1 connection, pool size is 20
    #
    # For small research groups (1-5 users), 10 is plenty
    # For large groups, increase this AND the database pool size
    max_jobs = 10

    # === JOB TIMEOUT ===
    # How long (in seconds) before a job is killed as "taking too long"
    # 3600 seconds = 1 hour
    #
    # WHY 1 HOUR? Based on expected processing times:
    # - E. coli (4,600 genes): ~15 minutes
    # - S. cerevisiae (6,700 genes): ~25 minutes
    # - Human (20,000 genes): ~90 minutes (would need longer timeout!)
    #
    # IMPORTANT: If processing large organisms (>20k genes), increase this
    # Timeout kills the job mid-processing, which wastes all progress
    #
    # TRADE-OFF: Longer timeout = hung jobs block worker longer
    # Shorter timeout = risk killing legitimate long-running jobs
    job_timeout = 3600

    # === RESULT RETENTION ===
    # How long (in seconds) to keep job results in Redis
    # 86400 seconds = 24 hours = 1 day
    #
    # Job results include:
    # - Success/failure status
    # - Return value (if any)
    # - Error message (if failed)
    # - Execution time
    #
    # WHY 24 HOURS?
    # - Long enough for debugging (can check yesterday's jobs)
    # - Short enough to avoid Redis memory bloat
    # - After 24 hours, Redis auto-deletes (TTL expiration)
    #
    # NOTE: This is separate from organism.status in PostgreSQL
    # - PostgreSQL stores permanent job outcome (pending/complete/error)
    # - Redis stores temporary job execution metadata
    keep_result = 86400

    # === QUEUE NAME ===
    # Name of the Redis queue to use
    # Default is 'arq:queue', which is fine for single-queue systems
    #
    # ADVANCED: For multi-priority systems, could use:
    # - 'arq:queue:high' for urgent organisms
    # - 'arq:queue:low' for batch processing
    # Then run separate workers for each queue
    #
    # For our MVP, single queue is sufficient
    queue_name = settings.arq_queue_name

    # === HEALTH CHECK ===
    # ARQ automatically provides a health check at /health
    # Useful for Docker health checks and monitoring
    #
    # Example: curl http://worker:8080/health
    # Response: {"queue_name": "arq:queue", "jobs_in_progress": 3}
    health_check_key = "arq:health"

    # === JOB RETRY POLICY ===
    # ARQ has built-in retry support, but we handle retries in the job itself
    # This gives us more control over which errors to retry
    #
    # max_tries = 1 means: Don't retry at ARQ level
    # Instead, our job function uses try/except with exponential backoff
    # to retry KEGG API calls (transient errors only)
    #
    # WHY CUSTOM RETRIES? More granular control:
    # - Retry KEGG API network errors (transient)
    # - Don't retry invalid organism code (permanent error)
    # - Different backoff strategies per error type
    max_tries = 1  # No ARQ-level retries, we handle retries in job

    # === LOGGING ===
    # ARQ logs to Python's logging system
    # Logs include: job start, job complete, job error, worker status
    #
    # Log levels:
    # - DEBUG: Every job state change (noisy but useful for debugging)
    # - INFO: Job start/complete (normal)
    # - WARNING: Job retry, slow job
    # - ERROR: Job failure
    #
    # In production, set to INFO or WARNING
    # In development, set to DEBUG to see everything
    log_results = True  # Log job results (success/failure)


# === ADDITIONAL CONFIGURATION NOTES ===

"""
DEPLOYMENT CONSIDERATIONS:

1. **Redis Memory:**
   - Each job result: ~1KB
   - Progress tracking: ~500 bytes per job
   - 1000 jobs/day * 1KB * 1 day retention = ~1MB
   - Redis memory usage is minimal (<10MB total)

2. **Worker Scaling:**
   - Single worker is sufficient for <50 organisms/day
   - For high throughput, run multiple worker processes:
     docker-compose scale worker=5
   - Workers share the Redis queue (no conflicts)

3. **Failure Recovery:**
   - If worker crashes, Redis keeps queued jobs
   - Restart worker → jobs automatically resume
   - In-progress jobs are retried (idempotent design)

4. **Monitoring:**
   - Check Redis queue length: `redis-cli LLEN arq:queue`
   - Check active jobs: Visit worker health endpoint
   - Check job results: `redis-cli GET arq:result:{job_id}`

5. **Graceful Shutdown:**
   - ARQ waits for in-progress jobs before shutdown (up to 1 minute)
   - Queued jobs remain in Redis, processed when worker restarts
   - Docker stop command triggers graceful shutdown automatically
"""

# Export WorkerSettings for use in run_worker.py
__all__ = ['WorkerSettings']
