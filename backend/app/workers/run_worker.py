"""
ARQ Worker Startup Script

=== WHAT THIS SCRIPT DOES ===
This script starts the ARQ worker process that processes background jobs.

Think of it as the "chef" who continuously checks the order queue (Redis)
and processes any new orders (organism processing jobs) that come in.

=== HOW TO RUN ===

1. **In Development (local machine):**
   ```bash
   cd backend
   python -m app.workers.run_worker
   ```

   This runs in your terminal - you'll see log output of jobs being processed.
   Press Ctrl+C to stop.

2. **In Docker (production):**
   ```bash
   docker-compose up worker
   ```

   Docker runs this script automatically using the command in docker-compose.yml.
   The worker runs in the background as a service.

3. **Multiple Workers (high load):**
   ```bash
   docker-compose up --scale worker=3
   ```

   Runs 3 worker processes simultaneously.
   They share the Redis queue (no conflicts, ARQ handles coordination).

=== WHAT HAPPENS WHEN IT STARTS ===

1. **Connect to Redis**
   - Uses redis_settings from WorkerSettings
   - Tests connection (fails fast if Redis is down)
   - Logs: "Connected to Redis at redis://localhost:6379/0"

2. **Register Job Functions**
   - Loads all functions from WorkerSettings.functions
   - Makes them available for enqueuing
   - Logs: "Registered 1 job function(s): process_organism_job"

3. **Start Polling Loop**
   - Every 100ms, checks Redis for new jobs
   - If job found, executes it asynchronously
   - Logs: "Job started: process_organism_job(123)"
   - Logs: "Job complete: process_organism_job(123) in 15m 23s"

4. **Health Check Server (Optional)**
   - ARQ can start an HTTP server for health checks
   - Useful for Docker/Kubernetes health probes
   - Endpoint: http://worker:8080/health

=== GRACEFUL SHUTDOWN ===

When you stop the worker (Ctrl+C or docker stop):

1. **Stop Accepting New Jobs**
   - No new jobs are pulled from Redis
   - Existing jobs continue processing

2. **Wait for In-Progress Jobs**
   - Waits up to 60 seconds for jobs to complete
   - If job finishes in time: status = complete
   - If job exceeds 60s: status = interrupted (will retry on restart)

3. **Close Connections**
   - Closes Redis connection
   - Releases database connections
   - Logs: "Worker shutdown complete"

This ensures no data loss or partial processing.
"""

import asyncio
import logging
import sys

# ARQ's worker runner - this is the main worker loop
from arq import run_worker

# Our worker configuration
from app.workers.arq_config import WorkerSettings

# Set up logging to see what the worker is doing
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log to stdout (Docker captures this)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """
    Start the ARQ worker.

    This is the entry point when you run:
        python -m app.workers.run_worker

    TECHNICAL DETAILS:
    - run_worker() is a blocking call - it runs until interrupted
    - It creates an asyncio event loop internally
    - Returns exit code: 0 = clean shutdown, 1 = error

    ERROR HANDLING:
    - If Redis is down: Worker exits immediately with error
    - If job function errors: Job is marked as failed, worker continues
    - If worker crashes: Docker restarts it automatically (restart: unless-stopped)
    """
    logger.info("=" * 60)
    logger.info("Starting KEGG Explore ARQ Worker")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Worker Configuration:")
    logger.info(f"  Redis URL: {WorkerSettings.redis_settings.host}:{WorkerSettings.redis_settings.port}")
    logger.info(f"  Database: {WorkerSettings.redis_settings.database}")
    logger.info(f"  Queue Name: {WorkerSettings.queue_name}")
    logger.info(f"  Max Concurrent Jobs: {WorkerSettings.max_jobs}")
    logger.info(f"  Job Timeout: {WorkerSettings.job_timeout}s ({WorkerSettings.job_timeout // 60} minutes)")
    logger.info(f"  Result Retention: {WorkerSettings.keep_result}s ({WorkerSettings.keep_result // 3600} hours)")
    logger.info("")
    logger.info("Registered Job Functions:")
    for func in WorkerSettings.functions:
        logger.info(f"  - {func.__name__}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("Worker is ready and waiting for jobs...")
    logger.info("Press Ctrl+C to stop gracefully")
    logger.info("=" * 60)
    logger.info("")

    try:
        # Start the ARQ worker
        # This blocks until the worker is stopped (Ctrl+C or error)
        #
        # ASYNC EXECUTION:
        # run_worker() internally uses asyncio.run() to:
        # 1. Create event loop
        # 2. Connect to Redis
        # 3. Start polling loop
        # 4. Execute jobs concurrently
        # 5. Handle signals (SIGINT, SIGTERM)
        #
        # RETURN VALUE:
        # - None = clean shutdown (Ctrl+C, SIGTERM)
        # - Exception = error during startup or execution
        run_worker(WorkerSettings)

        logger.info("")
        logger.info("=" * 60)
        logger.info("Worker shut down cleanly")
        logger.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        # User pressed Ctrl+C
        logger.info("")
        logger.info("=" * 60)
        logger.info("Received shutdown signal (Ctrl+C)")
        logger.info("Waiting for in-progress jobs to complete...")
        logger.info("=" * 60)
        return 0

    except Exception as e:
        # Worker crashed (e.g., Redis connection failed)
        logger.error("")
        logger.error("=" * 60)
        logger.error(f"Worker error: {e}")
        logger.error("=" * 60)
        logger.error("", exc_info=True)  # Print full stack trace
        return 1


if __name__ == "__main__":
    """
    Entry point when running as a script.

    Usage:
        python -m app.workers.run_worker

    DOCKER NOTE:
    In docker-compose.yml, this is run with:
        command: python -m app.workers.run_worker

    The -m flag tells Python to run a module (not a file).
    This ensures imports work correctly regardless of working directory.
    """
    exit_code = main()
    sys.exit(exit_code)
