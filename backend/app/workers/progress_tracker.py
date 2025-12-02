"""
Progress Tracking for Background Jobs

=== WHY TRACK PROGRESS? ===

Processing organisms can take 15-90 minutes depending on size:
- E. coli (4,600 genes): ~15 minutes
- Human (20,000 genes): ~90 minutes

Without progress tracking, users would see:
  Status: "pending" ... *15 minutes later* ... Status: "complete"

With progress tracking, users see:
  0% - Fetching genes from KEGG...
  10% - Storing 4,600 genes in database...
  15% - Finding orthologs... (gene 500 of 4,600)
  50% - Finding orthologs... (gene 2,300 of 4,600)
  100% - Complete! Found 3,400 orthologs (74% coverage)

This gives users confidence the job is working and time estimate.

=== REDIS VS. DATABASE ===

WHY store progress in Redis instead of PostgreSQL?

**Redis (our choice):**
- Fast: <1ms query latency
- Auto-expiration: TTL deletes old data automatically
- Ephemeral: Progress is temporary, doesn't need to be permanent
- No table churn: Updating every 100 genes = 46 DB writes for E. coli

**PostgreSQL (not used for progress):**
- Slow: ~10ms query latency per update
- Manual cleanup: Need cron job to delete old records
- Persistent: Progress stored forever (wasteful)
- Table bloat: 46 updates * 1000 jobs = 46,000 rows to clean up

**Summary:** Redis is perfect for temporary, frequently-updated data

=== DATA MODEL ===

Progress is stored as a JSON object in Redis:
Key: progress:{job_id}
Value: {
    "organism_id": 123,
    "organism_code": "eco",
    "stage": "finding_orthologs",
    "progress": 67.5,             # 0-100 percentage
    "total_genes": 4600,
    "genes_processed": 3100,
    "genes_with_orthologs": 2300,
    "errors": 5,
    "started_at": "2024-11-29T10:30:00Z",
    "updated_at": "2024-11-29T10:45:00Z"
}
TTL: 86400 seconds (24 hours)

After 24 hours, Redis automatically deletes the key (saves memory).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks real-time progress of organism processing jobs.

    USAGE IN JOB:
    ```python
    tracker = ProgressTracker(redis_conn, job_id)

    # Start job
    await tracker.start(organism_id=123, organism_code="eco", total_genes=4600)

    # Update progress periodically (every 100 genes)
    await tracker.update(
        stage="finding_orthologs",
        progress=50.0,
        genes_processed=2300,
        genes_with_orthologs=1700
    )

    # Complete job
    await tracker.complete(final_stats={
        "total_genes": 4600,
        "genes_with_orthologs": 3400,
        "coverage_percent": 74.0
    })
    ```

    USAGE IN API:
    ```python
    tracker = ProgressTracker(redis_conn, job_id)
    progress = await tracker.get_progress()

    if progress:
        return {
            "status": "in_progress",
            "progress": progress["progress"],
            "stage": progress["stage"],
            ...
        }
    ```
    """

    # === STAGE NAMES ===
    # These are the possible stages a job can be in
    # Used for display in UI and progress calculation
    STAGE_FETCHING_GENES = "fetching_genes"
    STAGE_STORING_GENES = "storing_genes"
    STAGE_FINDING_ORTHOLOGS = "finding_orthologs"
    STAGE_COMPLETE = "complete"
    STAGE_ERROR = "error"

    # === PROGRESS WEIGHT INGS ===
    # How much of total progress (0-100%) each stage represents
    #
    # WHY THESE WEIGHTS?
    # - Fetching genes: Fast (10%) - single KEGG API call
    # - Storing genes: Fast (5%) - batch insert to PostgreSQL
    # - Finding orthologs: Slow (85%) - 4,600 individual KEGG API calls
    #
    # This ensures progress bar moves smoothly and accurately reflects time
    STAGE_WEIGHTS = {
        STAGE_FETCHING_GENES: (0, 10),     # 0% → 10%
        STAGE_STORING_GENES: (10, 15),     # 10% → 15%
        STAGE_FINDING_ORTHOLOGS: (15, 100), # 15% → 100%
    }

    # === REDIS KEY TTL ===
    # How long to keep progress data in Redis
    # 86400 seconds = 24 hours = 1 day
    #
    # WHY 24 HOURS?
    # - Long enough to debug recent jobs
    # - Short enough to avoid Redis memory bloat
    # - Matches ARQ job result retention time
    TTL_SECONDS = 86400

    def __init__(self, redis_conn: redis.Redis, job_id: str):
        """
        Initialize progress tracker.

        Args:
            redis_conn: Async Redis connection
            job_id: Unique job ID (from ARQ)

        REDIS CONNECTION NOTE:
        The redis_conn is passed from ARQ's context (ctx['redis']).
        ARQ provides a connection pool automatically, so we don't
        need to create/close connections manually.
        """
        self.redis = redis_conn
        self.job_id = job_id
        self.key = f"progress:{job_id}"

    async def start(
        self,
        organism_id: int,
        organism_code: str,
        total_genes: int = 0
    ):
        """
        Initialize progress tracking when job starts.

        Args:
            organism_id: Database ID of organism being processed
            organism_code: KEGG organism code (e.g., "eco")
            total_genes: Total number of genes (0 if not yet fetched)

        TIMING: Call this at the very beginning of the job, before any work.

        EXAMPLE:
        ```python
        # Job just started
        await tracker.start(organism_id=123, organism_code="eco")
        # Progress is now 0%, stage is "fetching_genes"
        ```
        """
        now = datetime.now(timezone.utc).isoformat()

        data = {
            "organism_id": organism_id,
            "organism_code": organism_code,
            "stage": self.STAGE_FETCHING_GENES,
            "progress": 0.0,
            "total_genes": total_genes,
            "genes_processed": 0,
            "genes_with_orthologs": 0,
            "errors": 0,
            "started_at": now,
            "updated_at": now
        }

        # Store in Redis with TTL
        # SETEX = SET with EXpiration
        # After TTL_SECONDS, Redis auto-deletes this key
        await self.redis.setex(
            self.key,
            self.TTL_SECONDS,
            json.dumps(data)
        )

        logger.info(
            f"Progress tracking started for job {self.job_id} "
            f"(organism: {organism_code})"
        )

    async def update(
        self,
        stage: str,
        progress: float,
        genes_processed: Optional[int] = None,
        genes_with_orthologs: Optional[int] = None,
        errors: Optional[int] = None,
        total_genes: Optional[int] = None
    ):
        """
        Update progress during job execution.

        Args:
            stage: Current stage name (use STAGE_* constants)
            progress: Progress percentage (0-100)
            genes_processed: Number of genes processed so far
            genes_with_orthologs: Number with orthologs found
            errors: Number of errors encountered
            total_genes: Total genes (if changed from start)

        UPDATE FREQUENCY:
        Call this every 100 genes processed (per user decision).
        Too frequent = Redis overhead, too infrequent = choppy progress bar.

        EXAMPLE:
        ```python
        # Processing gene 2,300 out of 4,600
        await tracker.update(
            stage=ProgressTracker.STAGE_FINDING_ORTHOLOGS,
            progress=52.5,  # 15% + (85% * 2300/4600)
            genes_processed=2300,
            genes_with_orthologs=1700
        )
        ```

        PROGRESS CALCULATION:
        The job function calculates progress based on stage weights:
        - Stage: finding_orthologs (15% → 100%)
        - Progress within stage: 2300/4600 = 50%
        - Overall progress: 15% + (85% * 50%) = 57.5%
        """
        # Get current data from Redis
        current_data_str = await self.redis.get(self.key)

        if not current_data_str:
            # Progress key expired or job was never started
            # This can happen if:
            # 1. Job took >24 hours (TTL expired)
            # 2. Redis was restarted
            # 3. start() was never called (bug)
            logger.warning(
                f"Progress key not found for job {self.job_id}. "
                "Creating new progress entry."
            )
            # Create minimal progress entry
            data = {
                "organism_id": 0,
                "organism_code": "unknown",
                "stage": stage,
                "progress": progress,
                "total_genes": total_genes or 0,
                "genes_processed": genes_processed or 0,
                "genes_with_orthologs": genes_with_orthologs or 0,
                "errors": errors or 0,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Parse existing data
            data = json.loads(current_data_str)

            # Update fields (only if provided)
            data["stage"] = stage
            data["progress"] = round(progress, 2)  # Round to 2 decimal places
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            if genes_processed is not None:
                data["genes_processed"] = genes_processed
            if genes_with_orthologs is not None:
                data["genes_with_orthologs"] = genes_with_orthologs
            if errors is not None:
                data["errors"] = errors
            if total_genes is not None:
                data["total_genes"] = total_genes

        # Write back to Redis with refreshed TTL
        # WHY REFRESH TTL?
        # Each update resets the 24-hour clock.
        # This ensures progress data exists for 24 hours AFTER job completes.
        await self.redis.setex(
            self.key,
            self.TTL_SECONDS,
            json.dumps(data)
        )

        # Log every 10% milestone for visibility
        if int(progress) % 10 == 0:
            logger.info(
                f"Job {self.job_id} progress: {progress:.1f}% "
                f"(stage: {stage}, genes: {genes_processed}/{data.get('total_genes', '?')})"
            )

    async def complete(self, final_stats: Optional[Dict[str, Any]] = None):
        """
        Mark job as complete with final statistics.

        Args:
            final_stats: Dictionary of final statistics to store

        TIMING: Call this at the very end of the job, after all work is done.

        EXAMPLE:
        ```python
        await tracker.complete(final_stats={
            "total_genes": 4600,
            "genes_with_orthologs": 3400,
            "coverage_percent": 73.9,
            "processing_time_minutes": 15.2
        })
        ```

        NOTE: Progress is set to 100%, stage to "complete".
        The Redis key remains for 24 hours for debugging/auditing.
        """
        current_data_str = await self.redis.get(self.key)

        if current_data_str:
            data = json.loads(current_data_str)

            # Update to completion state
            data["stage"] = self.STAGE_COMPLETE
            data["progress"] = 100.0
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Add final stats if provided
            if final_stats:
                data["final_stats"] = final_stats

            # Store with TTL
            await self.redis.setex(
                self.key,
                self.TTL_SECONDS,
                json.dumps(data)
            )

        logger.info(f"Job {self.job_id} marked as complete")

    async def error(self, error_message: str):
        """
        Mark job as errored.

        Args:
            error_message: Description of error that occurred

        TIMING: Call this in the exception handler when job fails.

        EXAMPLE:
        ```python
        try:
            # Job logic
        except Exception as e:
            await tracker.error(str(e))
            raise  # Re-raise to let ARQ know job failed
        ```
        """
        current_data_str = await self.redis.get(self.key)

        if current_data_str:
            data = json.loads(current_data_str)

            # Update to error state
            data["stage"] = self.STAGE_ERROR
            data["error_message"] = error_message[:1000]  # Truncate long errors
            data["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Store with TTL
            await self.redis.setex(
                self.key,
                self.TTL_SECONDS,
                json.dumps(data)
            )

        logger.error(f"Job {self.job_id} errored: {error_message}")

    async def get_progress(self) -> Optional[Dict[str, Any]]:
        """
        Get current progress data.

        Returns:
            Dictionary with progress data, or None if not found

        USAGE IN API:
        ```python
        progress = await tracker.get_progress()
        if progress:
            return {
                "status": "in_progress" if progress["progress"] < 100 else "complete",
                "progress": progress["progress"],
                "stage": progress["stage"],
                "genes_processed": progress["genes_processed"],
                "total_genes": progress["total_genes"]
            }
        else:
            # Job completed >24 hours ago or never started
            return {"status": "unknown"}
        ```

        CACHING NOTE:
        The API can cache this value for ~1 second client-side.
        No need to query Redis on every HTTP request.
        """
        data_str = await self.redis.get(self.key)

        if not data_str:
            return None

        return json.loads(data_str)

    async def delete(self):
        """
        Delete progress data immediately.

        Use this to clean up progress data when:
        - Job is cancelled by user
        - Need to clear Redis for testing
        - Job failed during startup (no useful progress data)

        EXAMPLE:
        ```python
        # User cancelled job
        await tracker.delete()
        ```

        NOTE: This is rarely needed since Redis TTL auto-deletes after 24 hours.
        """
        await self.redis.delete(self.key)
        logger.info(f"Progress data deleted for job {self.job_id}")


# === HELPER FUNCTIONS ===

def calculate_stage_progress(
    stage: str,
    items_processed: int,
    total_items: int
) -> float:
    """
    Calculate overall progress percentage based on current stage.

    This is a helper function for the job to calculate progress values.

    Args:
        stage: Current stage name (ProgressTracker.STAGE_*)
        items_processed: Number of items completed in this stage
        total_items: Total items in this stage

    Returns:
        Progress percentage (0-100)

    EXAMPLE:
    ```python
    # Finding orthologs: processed 2,300 out of 4,600 genes
    progress = calculate_stage_progress(
        stage=ProgressTracker.STAGE_FINDING_ORTHOLOGS,
        items_processed=2300,
        total_items=4600
    )
    # Returns: 15 + (85 * 2300/4600) = 15 + 42.5 = 57.5%
    ```

    BIOINFORMATICS NOTE:
    Most time is spent in ortholog finding stage (85% of total).
    This ensures progress bar moves slowly during the long stage,
    not jumping from 15% → 100% instantly.
    """
    if total_items == 0:
        # Avoid division by zero
        # Return start of stage range
        return ProgressTracker.STAGE_WEIGHTS.get(stage, (0, 0))[0]

    # Get stage's progress range
    start_pct, end_pct = ProgressTracker.STAGE_WEIGHTS.get(stage, (0, 100))

    # Calculate progress within stage
    stage_progress = items_processed / total_items

    # Map to overall progress
    overall_progress = start_pct + ((end_pct - start_pct) * stage_progress)

    return overall_progress


# Export public interface
__all__ = ['ProgressTracker', 'calculate_stage_progress']
