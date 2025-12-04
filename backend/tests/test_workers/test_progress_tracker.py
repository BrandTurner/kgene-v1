"""
Tests for Progress Tracker (Phase 3)

WHAT WE'RE TESTING:
The ProgressTracker class manages real-time progress updates for background jobs.
It uses Redis to store progress data that can be queried via the API.

WHY REDIS FOR PROGRESS?
- Fast: In-memory storage, <1ms reads
- Expiration: Auto-delete after 24 hours (TTL)
- Concurrent: Multiple workers can update simultaneously
- Decoupled: API reads progress without querying database

PROGRESS STAGES:
1. fetching_genes (0% → 10%): Downloading gene list from KEGG
2. storing_genes (10% → 15%): Batch inserting genes to database
3. finding_orthologs (15% → 100%): Finding orthologs for all genes
4. complete (100%): Job finished

TESTING STRATEGY:
- Use fakeredis (in-memory simulation, no Docker)
- Test all stage transitions
- Test progress calculations
- Test error handling
- Test TTL expiration
"""

import pytest
import json
from datetime import datetime, timezone

from app.workers.progress_tracker import (
    ProgressTracker,
    calculate_stage_progress,
)


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_progress_tracker_initialization(fake_redis):
    """
    Test ProgressTracker initialization and start() method.

    WHAT HAPPENS ON START:
    - Creates Redis key: progress:<job_id>
    - Sets TTL: 24 hours (86400 seconds)
    - Stores initial progress JSON with metadata

    EXPECTED FIELDS:
    - status: "in_progress"
    - organism_code, organism_id, total_genes
    - stage: "fetching_genes"
    - progress: 0.0
    - started_at timestamp
    """
    tracker = ProgressTracker(fake_redis, job_id="test_job_123")

    await tracker.start(
        organism_id=1,
        organism_code="eco",
        total_genes=100
    )

    # Verify Redis key created
    key = "progress:test_job_123"
    data_json = await fake_redis.get(key)
    assert data_json is not None

    # Verify data structure
    data = json.loads(data_json)
    assert data["status"] == "in_progress"
    assert data["organism_id"] == 1
    assert data["organism_code"] == "eco"
    assert data["total_genes"] == 100
    assert data["stage"] == "fetching_genes"
    assert data["progress"] == 0.0
    assert "started_at" in data


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ttl_set_on_start(fake_redis):
    """
    Test that TTL (time-to-live) is set correctly.

    WHY TTL?
    Progress data is temporary - only needed while job is running
    and for ~24 hours after completion for debugging.

    After 24 hours, Redis auto-deletes to prevent memory bloat.

    EXPECTED:
    TTL = 86400 seconds (24 hours)
    """
    tracker = ProgressTracker(fake_redis, job_id="ttl_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    # Check TTL
    key = "progress:ttl_test"
    ttl = await fake_redis.ttl(key)

    # TTL should be close to 86400 (within 10 seconds of creation)
    assert 86390 <= ttl <= 86400


# =============================================================================
# STAGE TRANSITION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stage_transition_fetching_to_storing(fake_redis):
    """
    Test transition from fetching_genes to storing_genes.

    STAGE 1 → STAGE 2:
    - fetching_genes (0-10%) → storing_genes (10-15%)
    - Progress updates to 10% at transition
    - Stage name changes
    """
    tracker = ProgressTracker(fake_redis, job_id="stage_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    # Transition to storing stage
    await tracker.update(
        stage="storing_genes",
        progress=0,  # Stage-relative progress (0% of storing stage)
        genes_processed=0,
    )

    # Verify stage and progress
    data = await tracker.get_progress()
    assert data["stage"] == "storing_genes"
    assert data["progress"] == 10.0  # Base of storing stage


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stage_transition_storing_to_orthologs(fake_redis):
    """
    Test transition from storing_genes to finding_orthologs.

    STAGE 2 → STAGE 3:
    - storing_genes (10-15%) → finding_orthologs (15-100%)
    - This is the longest stage (~85% of total time)
    """
    tracker = ProgressTracker(fake_redis, job_id="ortho_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    # Move through stages
    await tracker.update(stage="storing_genes", progress=100)
    await tracker.update(stage="finding_orthologs", progress=0)

    data = await tracker.get_progress()
    assert data["stage"] == "finding_orthologs"
    assert data["progress"] == 15.0  # Base of ortholog stage


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_stage(fake_redis):
    """
    Test marking job as complete.

    FINAL STAGE:
    - Stage: "complete"
    - Progress: 100%
    - Status: "complete"
    - Final statistics added
    """
    tracker = ProgressTracker(fake_redis, job_id="complete_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    # Mark complete with final stats
    final_stats = {
        "total_genes": 100,
        "genes_with_orthologs": 73,
        "coverage_percent": 73.0,
        "method": "KEGG_KO"
    }
    await tracker.complete(final_stats)

    data = await tracker.get_progress()
    assert data["status"] == "complete"
    assert data["stage"] == "complete"
    assert data["progress"] == 100.0
    assert data["final_stats"]["coverage_percent"] == 73.0


# =============================================================================
# PROGRESS CALCULATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_progress_calculation_within_stage(fake_redis):
    """
    Test progress calculation within a stage.

    EXAMPLE: finding_orthologs stage (15% → 100%)
    - Process 50 of 100 genes = 50% through stage
    - Stage span: 85% (15 to 100)
    - 50% of 85% = 42.5%
    - Total progress: 15% + 42.5% = 57.5%
    """
    tracker = ProgressTracker(fake_redis, job_id="calc_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    # Move to ortholog stage
    await tracker.update(stage="finding_orthologs", progress=0)

    # Update progress: 50 genes processed out of 100
    await tracker.update(
        stage="finding_orthologs",
        progress=50,  # 50% through stage
        genes_processed=50,
        genes_with_orthologs=37
    )

    data = await tracker.get_progress()

    # 15% (base) + 50% of 85% (span) = 15 + 42.5 = 57.5%
    expected_progress = 15 + (50 * 0.85)
    assert abs(data["progress"] - expected_progress) < 0.1


@pytest.mark.unit
def test_calculate_stage_progress_helper():
    """
    Test the calculate_stage_progress helper function.

    FUNCTION SIGNATURE:
    calculate_stage_progress(stage, stage_progress) -> float

    EXAMPLES:
    - fetching_genes at 50%: 0 + (0.5 * 10) = 5%
    - storing_genes at 100%: 10 + (1.0 * 5) = 15%
    - finding_orthologs at 20%: 15 + (0.2 * 85) = 32%
    """
    # Stage 1: fetching_genes (0-10%)
    assert calculate_stage_progress("fetching_genes", 0) == 0.0
    assert calculate_stage_progress("fetching_genes", 50) == 5.0
    assert calculate_stage_progress("fetching_genes", 100) == 10.0

    # Stage 2: storing_genes (10-15%)
    assert calculate_stage_progress("storing_genes", 0) == 10.0
    assert calculate_stage_progress("storing_genes", 100) == 15.0

    # Stage 3: finding_orthologs (15-100%)
    assert calculate_stage_progress("finding_orthologs", 0) == 15.0
    assert calculate_stage_progress("finding_orthologs", 50) == 57.5
    assert calculate_stage_progress("finding_orthologs", 100) == 100.0


# =============================================================================
# COUNTER TRACKING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_genes_processed_counter(fake_redis):
    """
    Test tracking of genes_processed counter.

    WHY TRACK THIS?
    Shows user how many genes have been analyzed so far.
    Example: "Processing: 1,234 / 4,639 genes"
    """
    tracker = ProgressTracker(fake_redis, job_id="counter_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=500)

    # Update with 100 genes processed
    await tracker.update(
        stage="finding_orthologs",
        progress=20,
        genes_processed=100,
        genes_with_orthologs=73
    )

    data = await tracker.get_progress()
    assert data["genes_processed"] == 100
    assert data["genes_with_orthologs"] == 73
    assert data["total_genes"] == 500


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_counter(fake_redis):
    """
    Test tracking of errors during processing.

    WHY TRACK ERRORS?
    - Monitor job health
    - Alert if error rate too high
    - Debug failed jobs

    Example: "73% complete, 12 errors encountered"
    """
    tracker = ProgressTracker(fake_redis, job_id="error_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    # Update with some errors
    await tracker.update(
        stage="finding_orthologs",
        progress=50,
        genes_processed=50,
        genes_with_orthologs=35,
        errors=3  # 3 genes failed to process
    )

    data = await tracker.get_progress()
    assert data["errors"] == 3


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mark_as_error(fake_redis):
    """
    Test marking job as failed.

    SCENARIO:
    Job crashes due to KEGG API error, database failure, etc.

    EXPECTED:
    - Status: "error"
    - Error message stored
    - Progress preserved (shows where it failed)
    """
    tracker = ProgressTracker(fake_redis, job_id="fail_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    # Simulate job progressing then failing
    await tracker.update(stage="finding_orthologs", progress=30)
    await tracker.error("KEGG API connection timeout")

    data = await tracker.get_progress()
    assert data["status"] == "error"
    assert "KEGG API" in data.get("error_message", "")
    assert data["progress"] == pytest.approx(15 + (30 * 0.85), rel=0.1)


# =============================================================================
# TIMESTAMP TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_timestamps_tracked(fake_redis):
    """
    Test that started_at and updated_at timestamps are tracked.

    WHY TIMESTAMPS?
    - Calculate job duration
    - Detect stalled jobs (updated_at not changing)
    - Estimate time remaining

    EXPECTED FORMAT:
    ISO 8601 with timezone: "2025-12-02T00:15:55.676561+00:00"
    """
    tracker = ProgressTracker(fake_redis, job_id="time_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    data1 = await tracker.get_progress()
    started = data1["started_at"]

    # Verify timestamp format (ISO 8601)
    assert "T" in started
    assert "+" in started or "Z" in started

    # Update and verify updated_at changes
    await tracker.update(stage="fetching_genes", progress=50)
    data2 = await tracker.get_progress()

    assert data2["updated_at"] != started  # Updated timestamp changed
    assert data2["started_at"] == started  # Start timestamp unchanged


# =============================================================================
# GET PROGRESS TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_progress_returns_all_fields(fake_redis):
    """
    Test that get_progress() returns complete progress data.

    REQUIRED FIELDS:
    - status, organism_code, organism_id
    - stage, progress, total_genes
    - genes_processed, genes_with_orthologs, errors
    - started_at, updated_at
    """
    tracker = ProgressTracker(fake_redis, job_id="fields_test")
    await tracker.start(organism_id=42, organism_code="eco", total_genes=1000)

    await tracker.update(
        stage="finding_orthologs",
        progress=25,
        genes_processed=250,
        genes_with_orthologs=180,
        errors=2
    )

    data = await tracker.get_progress()

    # Verify all required fields present
    required_fields = [
        "status", "organism_code", "organism_id",
        "stage", "progress", "total_genes",
        "genes_processed", "genes_with_orthologs", "errors",
        "started_at", "updated_at"
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_progress_nonexistent_job(fake_redis):
    """
    Test getting progress for job that doesn't exist.

    SCENARIO:
    - Job completed >24 hours ago (TTL expired, Redis auto-deleted)
    - Invalid job_id
    - Redis connection issues

    EXPECTED:
    Return None or empty dict (let caller handle fallback to database)
    """
    tracker = ProgressTracker(fake_redis, job_id="nonexistent_job")
    data = await tracker.get_progress()

    # Should return None when job doesn't exist
    assert data is None


# =============================================================================
# REDIS KEY MANAGEMENT TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_key_format(fake_redis):
    """
    Test Redis key naming convention.

    KEY FORMAT:
    progress:<job_id>

    WHY THIS FORMAT?
    - Namespacing: All progress keys start with "progress:"
    - Easy cleanup: KEYS progress:* finds all progress data
    - Job isolation: Each job has unique key
    """
    job_id = "abc123-def456-ghi789"
    tracker = ProgressTracker(fake_redis, job_id=job_id)
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    expected_key = f"progress:{job_id}"
    assert await fake_redis.exists(expected_key) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multiple_jobs_isolated(fake_redis):
    """
    Test that multiple jobs have isolated progress tracking.

    SCENARIO:
    Two jobs running simultaneously.

    EXPECTED:
    Each job has separate Redis key, updates don't interfere.
    """
    tracker1 = ProgressTracker(fake_redis, job_id="job1")
    tracker2 = ProgressTracker(fake_redis, job_id="job2")

    await tracker1.start(organism_id=1, organism_code="eco", total_genes=100)
    await tracker2.start(organism_id=2, organism_code="hsa", total_genes=200)

    # Update job1
    await tracker1.update(stage="fetching_genes", progress=50)

    # Verify job2 unaffected
    data1 = await tracker1.get_progress()
    data2 = await tracker2.get_progress()

    assert data1["progress"] == 5.0  # 50% of fetching stage
    assert data2["progress"] == 0.0  # Still at start
    assert data1["organism_code"] == "eco"
    assert data2["organism_code"] == "hsa"


# =============================================================================
# JSON SERIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_json_serialization_round_trip(fake_redis):
    """
    Test that all data types serialize/deserialize correctly.

    DATA TYPES IN PROGRESS:
    - Strings: organism_code, stage, status
    - Integers: organism_id, total_genes, genes_processed
    - Floats: progress, coverage_percent
    - Datetime: started_at, updated_at
    - Nested objects: final_stats

    CHALLENGE:
    Redis stores strings, so we serialize to JSON.
    Must ensure datetime → string → datetime works correctly.
    """
    tracker = ProgressTracker(fake_redis, job_id="json_test")
    await tracker.start(organism_id=999, organism_code="test", total_genes=5000)

    await tracker.update(
        stage="finding_orthologs",
        progress=75.5,  # Float
        genes_processed=3775,  # Int
        genes_with_orthologs=2800,
        errors=12
    )

    data = await tracker.get_progress()

    # Verify types preserved
    assert isinstance(data["organism_id"], int)
    assert isinstance(data["progress"], float)
    assert isinstance(data["genes_processed"], int)
    assert isinstance(data["started_at"], str)  # ISO format string


# =============================================================================
# EDGE CASES
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_zero_genes_organism(fake_redis):
    """
    Test edge case: organism with 0 genes.

    SCENARIO:
    Invalid organism code or data error leads to 0 genes fetched.

    EXPECTED:
    Handle gracefully, don't divide by zero in progress calculations.
    """
    tracker = ProgressTracker(fake_redis, job_id="zero_test")
    await tracker.start(organism_id=1, organism_code="invalid", total_genes=0)

    # Should handle without crashing
    await tracker.update(stage="fetching_genes", progress=100)
    data = await tracker.get_progress()

    assert data["total_genes"] == 0
    assert data["progress"] >= 0  # No crash


@pytest.mark.unit
@pytest.mark.asyncio
async def test_progress_never_exceeds_100(fake_redis):
    """
    Test that progress is capped at 100%.

    SCENARIO:
    Bug in calculation might push progress > 100%.

    EXPECTED:
    Progress always clamped to 0-100 range.
    """
    tracker = ProgressTracker(fake_redis, job_id="cap_test")
    await tracker.start(organism_id=1, organism_code="eco", total_genes=100)

    # Try to set progress beyond 100
    await tracker.update(stage="finding_orthologs", progress=150)

    data = await tracker.get_progress()
    assert data["progress"] <= 100.0


# =============================================================================
# RUN TESTS
# =============================================================================

"""
TO RUN THESE TESTS:

    # All progress tracker tests
    pytest tests/test_workers/test_progress_tracker.py -v

    # Only unit tests
    pytest tests/test_workers/test_progress_tracker.py -m unit -v

    # Specific test
    pytest tests/test_workers/test_progress_tracker.py::test_progress_calculation_within_stage -v

    # With coverage
    pytest tests/test_workers/test_progress_tracker.py --cov=app.workers.progress_tracker

EXPECTED RESULTS:
- All tests pass
- No real Redis (fakeredis in-memory simulation)
- Tests complete in <3 seconds
- Coverage >90% for progress_tracker.py

KEY TAKEAWAYS:
- Progress accurately calculated across stages
- TTL prevents Redis memory bloat
- Error states handled gracefully
- Concurrent jobs isolated
- Timestamps tracked for duration calculation
"""
