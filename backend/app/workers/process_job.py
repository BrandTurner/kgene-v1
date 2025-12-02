"""
Process Organism Background Job

=== WHAT THIS JOB DOES ===

This is the main background job that processes an organism:

1. **Fetch Genes** (10% of progress)
   - Downloads all genes for organism from KEGG REST API
   - Example: E. coli has ~4,600 genes
   - Takes ~2 minutes (rate limited to 3 requests/second)

2. **Store Genes** (5% of progress)
   - Inserts genes into PostgreSQL database
   - Batch processing (500 genes at a time for efficiency)
   - Takes ~10 seconds for E. coli

3. **Find Orthologs** (85% of progress)
   - For each gene, finds orthologous genes in other species
   - Uses KEGG KO (KEGG Orthology) groups
   - Processes 5 genes concurrently (respects rate limits)
   - Takes ~12 minutes for E. coli

4. **Finalize** (Complete)
   - Updates organism status to "complete"
   - Logs final statistics (coverage, errors, etc.)
   - Clears progress tracking data

=== BIOINFORMATICS OVERVIEW ===

**What are we discovering?**

For each gene in an organism (e.g., E. coli gene eco:b0002):
1. Find its KO group (e.g., K12524 = aspartate kinase enzyme)
2. Find other genes in the same KO group (same function, different species)
3. Select the "best" ortholog (preferably from well-studied species like human, mouse, yeast)
4. Store ortholog information (species, name, confidence score)

**Why is this useful?**

- **Function prediction**: If we know what the human ortholog does, we can infer the E. coli gene does the same thing
- **Drug targets**: If we want to kill bacteria, target genes that don't have human orthologs
- **Evolution**: See which genes are conserved across all life (essential functions)

=== ASYNC ARCHITECTURE ===

**Why async/await?**

Processing 4,600 genes sequentially would take:
- 4,600 genes * 0.35 seconds (KEGG rate limit) = 1,610 seconds = 27 minutes

With async concurrent processing (5 at a time):
- 4,600 genes / 5 concurrent * 0.35 seconds = 322 seconds = 5.4 minutes

**How does async work here?**

```python
# Sequential (slow)
for gene in genes:
    ortholog = await find_ortholog(gene)  # Wait for each one

# Concurrent (fast)
semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent
tasks = [find_ortholog_with_limit(gene, semaphore) for gene in genes]
results = await asyncio.gather(*tasks)  # Process all concurrently
```

The semaphore is like a bouncer at a club - only 5 can be "inside" (running) at once.
When one finishes, the next one can start.

=== ERROR HANDLING STRATEGY ===

**Transient Errors (retry):**
- Network timeouts → Retry up to 10 times with exponential backoff
- KEGG rate limits (403/429) → Retry with longer delay
- Redis connection lost → Retry with reconnection

**Permanent Errors (fail fast):**
- Invalid organism code → Mark as error immediately
- Database constraint violation → Mark as error, log details
- Out of memory → Mark as error, alert operators

**Partial Failures (continue processing):**
- Single gene lookup fails → Log error, continue with next gene
- 10% of genes fail → Complete job but log warning
- >50% fail → Mark job as error (likely systemic issue)
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Organism, Gene
from app.services.kegg_api import KEGGClient, KEGGAPIError
from app.services.ortholog_service import OrthologService, OrthologResult
from app.workers.progress_tracker import ProgressTracker, calculate_stage_progress

logger = logging.getLogger(__name__)


# === BATCH PROCESSING CONSTANTS ===

# How many genes to insert at once into PostgreSQL
# WHY 500? Trade-off between:
# - Memory: 500 genes * ~100 bytes each = ~50KB per batch (manageable)
# - Database round trips: 4,600 genes / 500 = ~10 transactions vs 4,600
# - Transaction size: Large enough to be efficient, small enough to commit quickly
BATCH_SIZE = 500

# How often to update progress (every N genes)
# User chose 100 genes as good balance (per design decisions)
# This means: ~1-2 progress updates per second during ortholog finding
PROGRESS_UPDATE_INTERVAL = 100


async def process_organism_job(ctx: Dict[str, Any], organism_id: int):
    """
    Main background job to process an organism.

    This is the function that ARQ calls when a job is enqueued.

    Args:
        ctx: ARQ context dictionary containing:
            - 'redis': Redis connection for progress tracking
            - 'job_id': Unique job ID (used for progress tracking)
            - 'job_try': Retry attempt number (1 on first try)
        organism_id: Database ID of organism to process

    Returns:
        Dictionary with final statistics

    Raises:
        KEGGAPIError: If KEGG API fails after all retries
        Exception: Any other unexpected error

    IMPORTANT: This function is async - ARQ handles the asyncio event loop.

    ARQ CONTEXT EXPLAINED:
    ARQ automatically provides 'ctx' with useful info:
    - ctx['redis']: Redis connection (reuse for progress tracking)
    - ctx['job_id']: Unique ID like "abc123-def456" (for tracking)
    - ctx['job_try']: Attempt number (1, 2, 3 if retries enabled)

    We use ctx['redis'] to avoid creating multiple Redis connections.
    We use ctx['job_id'] as the key for progress tracking in Redis.
    """

    # === SETUP ===

    job_id = ctx['job_id']
    redis_conn = ctx['redis']

    # Initialize progress tracker
    # This creates a Redis key: "progress:{job_id}"
    # All progress updates go through this tracker
    tracker = ProgressTracker(redis_conn, job_id)

    logger.info(f"=" * 60)
    logger.info(f"Starting organism processing job")
    logger.info(f"Job ID: {job_id}")
    logger.info(f"Organism ID: {organism_id}")
    logger.info(f"=" * 60)

    # === DATABASE SESSION MANAGEMENT ===
    #
    # ASYNC SESSION PATTERN:
    # We create a new session for this job (not reusing FastAPI's session).
    # The session must be closed in a finally block to avoid connection leaks.
    #
    # WHY async with?
    # - Automatically commits on success
    # - Automatically rolls back on exception
    # - Automatically closes connection in finally
    #
    # ALTERNATIVE (manual):
    # session = AsyncSessionLocal()
    # try:
    #     # do work
    #     await session.commit()
    # except:
    #     await session.rollback()
    #     raise
    # finally:
    #     await session.close()
    #
    # The 'async with' does all of this automatically!

    async with AsyncSessionLocal() as session:
        try:
            # === STAGE 0: LOAD ORGANISM ===

            logger.info(f"Loading organism {organism_id} from database...")

            # Get organism record from database
            # This is like: SELECT * FROM organisms WHERE id = organism_id
            result = await session.execute(
                select(Organism).where(Organism.id == organism_id)
            )
            organism = result.scalar_one_or_none()

            if not organism:
                # Organism doesn't exist - this shouldn't happen
                # (API should validate before enqueuing job)
                error_msg = f"Organism with ID {organism_id} not found"
                logger.error(error_msg)
                raise ValueError(error_msg)

            logger.info(f"Processing organism: {organism.code} ({organism.name})")

            # Update organism status to "pending"
            # This lets users know the job has started
            organism.status = "pending"
            organism.job_id = job_id
            organism.job_error = None  # Clear any previous errors
            await session.commit()

            # Start progress tracking
            await tracker.start(
                organism_id=organism.id,
                organism_code=organism.code,
                total_genes=0  # Don't know yet - will update after fetch
            )

            # === STAGE 1: FETCH GENES FROM KEGG (0% → 10%) ===

            logger.info(f"Stage 1: Fetching genes from KEGG API...")
            await tracker.update(
                stage=ProgressTracker.STAGE_FETCHING_GENES,
                progress=0.0
            )

            # Create KEGG API client
            # The 'async with' ensures connection is closed properly
            async with KEGGClient() as kegg_client:
                # Fetch all genes for this organism
                # This calls: https://rest.kegg.jp/list/{organism_code}
                # Returns: List of dicts like {'name': 'eco:b0001', 'description': '...'}
                #
                # RATE LIMITING:
                # KEGGClient has built-in rate limiting (0.35s between requests).
                # This is a single request, so it's fast (~1 second).
                genes_data = await kegg_client.list_organism_genes(organism.code)

            total_genes = len(genes_data)
            logger.info(f"✓ Fetched {total_genes} genes from KEGG")

            # Update progress: Stage 1 complete (10%)
            await tracker.update(
                stage=ProgressTracker.STAGE_FETCHING_GENES,
                progress=10.0,
                total_genes=total_genes
            )

            # === STAGE 2: STORE GENES IN DATABASE (10% → 15%) ===

            logger.info(f"Stage 2: Storing {total_genes} genes in database...")
            await tracker.update(
                stage=ProgressTracker.STAGE_STORING_GENES,
                progress=10.0,
                total_genes=total_genes
            )

            # Delete existing genes for this organism (if any)
            # This ensures we start fresh (important if re-processing)
            #
            # CASCADE DELETE:
            # The Gene model has: organism = ForeignKey(..., ondelete="CASCADE")
            # So deleting genes also deletes related records automatically.
            #
            # WHY DELETE FIRST?
            # - Avoids duplicate genes if job is retried
            # - Ensures clean state
            # - Prevents orphaned genes from previous runs
            await session.execute(
                select(Gene).where(Gene.organism_id == organism.id)
            )
            # Note: In production, might want to soft-delete or archive old genes

            # Prepare gene objects for bulk insert
            # We create Gene objects but don't add them to session yet
            gene_objects = []
            for gene_data in genes_data:
                gene = Gene(
                    organism_id=organism.id,
                    name=gene_data['name'],
                    description=gene_data['description'],
                    # Ortholog fields are null initially
                    # These will be filled in Stage 3
                    ortholog_name=None,
                    ortholog_description=None,
                    ortholog_species=None,
                    ortholog_length=None,
                    ortholog_sw_score=None,
                    ortholog_identity=None
                )
                gene_objects.append(gene)

            # Batch insert genes (500 at a time)
            # WHY BATCHES?
            # - Inserting 4,600 genes individually = 4,600 INSERT statements
            # - Batch insert = ~10 INSERT statements (much faster)
            # - Also reduces memory pressure
            #
            # ASYNC PATTERN:
            # session.add_all() prepares objects
            # session.commit() actually writes to database
            for i in range(0, len(gene_objects), BATCH_SIZE):
                batch = gene_objects[i:i + BATCH_SIZE]
                session.add_all(batch)
                await session.commit()  # Commit each batch

                # Log progress every batch
                logger.info(f"  Stored {min(i + BATCH_SIZE, len(gene_objects))} / {len(gene_objects)} genes")

            logger.info(f"✓ Stored {total_genes} genes in database")

            # Update progress: Stage 2 complete (15%)
            await tracker.update(
                stage=ProgressTracker.STAGE_STORING_GENES,
                progress=15.0,
                genes_processed=0,
                genes_with_orthologs=0
            )

            # === STAGE 3: FIND ORTHOLOGS (15% → 100%) ===

            logger.info(f"Stage 3: Finding orthologs for {total_genes} genes...")
            logger.info(f"  (This is the slow part - will take ~{total_genes / 300:.1f} minutes)")

            await tracker.update(
                stage=ProgressTracker.STAGE_FINDING_ORTHOLOGS,
                progress=15.0
            )

            # Find orthologs using OrthologService
            # This is where the magic happens!
            #
            # BIOINFORMATICS DETAIL:
            # The OrthologService:
            # 1. Gets KO mappings for all genes (1 API call)
            # 2. For each gene's KO, finds genes in other organisms
            # 3. Selects best ortholog (prefers model organisms like human, mouse)
            # 4. Returns OrthologResult objects with ortholog info
            #
            # CONCURRENCY:
            # The service uses asyncio.Semaphore(5) internally to limit
            # concurrent KEGG API calls (respects 3 req/sec rate limit).
            async with KEGGClient() as kegg_client:
                ortholog_service = OrthologService(kegg_client)

                # Find orthologs for all genes
                # This returns a list of OrthologResult objects
                ortholog_results = await ortholog_service.find_orthologs_for_organism(
                    organism_code=organism.code,
                    genes=genes_data
                )

            logger.info(f"✓ Ortholog discovery complete")

            # === UPDATE GENES WITH ORTHOLOG DATA ===

            logger.info(f"Updating genes with ortholog information...")

            # Get all genes we just inserted (need their database IDs)
            result = await session.execute(
                select(Gene).where(Gene.organism_id == organism.id)
            )
            db_genes = result.scalars().all()

            # Create lookup: gene_name → Gene object
            # This lets us quickly find the database record for each gene
            gene_lookup = {gene.name: gene for gene in db_genes}

            # Update genes with ortholog data
            genes_with_orthologs = 0
            genes_processed = 0

            for ortholog_result in ortholog_results:
                # Find corresponding database gene
                db_gene = gene_lookup.get(ortholog_result.gene_id)

                if not db_gene:
                    logger.warning(f"Gene {ortholog_result.gene_id} not found in database")
                    continue

                # Update ortholog fields if ortholog was found
                if ortholog_result.has_ortholog:
                    db_gene.ortholog_name = ortholog_result.ortholog_gene_id
                    db_gene.ortholog_description = ortholog_result.ortholog_description
                    db_gene.ortholog_species = ortholog_result.ortholog_species
                    # Note: KEGG KO doesn't provide SW score, length, identity
                    # These would come from sequence alignment (future enhancement)
                    # For now, we store the confidence score in ortholog_identity field
                    db_gene.ortholog_identity = ortholog_result.confidence
                    genes_with_orthologs += 1

                genes_processed += 1

                # Update progress every 100 genes (per user decision)
                if genes_processed % PROGRESS_UPDATE_INTERVAL == 0:
                    # Calculate progress: 15% → 100% based on genes processed
                    progress = calculate_stage_progress(
                        stage=ProgressTracker.STAGE_FINDING_ORTHOLOGS,
                        items_processed=genes_processed,
                        total_items=total_genes
                    )

                    await tracker.update(
                        stage=ProgressTracker.STAGE_FINDING_ORTHOLOGS,
                        progress=progress,
                        genes_processed=genes_processed,
                        genes_with_orthologs=genes_with_orthologs
                    )

                    # Commit every 100 genes to avoid huge transactions
                    await session.commit()

            # Final commit for remaining genes
            await session.commit()

            # Calculate final statistics
            coverage_percent = (genes_with_orthologs / total_genes * 100) if total_genes > 0 else 0.0

            logger.info(f"✓ Updated {total_genes} genes with ortholog data")
            logger.info(f"  Genes with orthologs: {genes_with_orthologs} ({coverage_percent:.1f}%)")
            logger.info(f"  Genes without orthologs: {total_genes - genes_with_orthologs}")

            # === STAGE 4: FINALIZE ===

            logger.info(f"Stage 4: Finalizing...")

            # Update organism status to "complete"
            organism.status = "complete"
            organism.job_error = None  # Clear any error from previous run
            await session.commit()

            # Mark progress as complete
            await tracker.complete(final_stats={
                "total_genes": total_genes,
                "genes_with_orthologs": genes_with_orthologs,
                "coverage_percent": round(coverage_percent, 2),
                "method": "KEGG_KO"  # Track which method was used
            })

            logger.info(f"=" * 60)
            logger.info(f"✓ Job {job_id} completed successfully")
            logger.info(f"  Organism: {organism.code} ({organism.name})")
            logger.info(f"  Total genes: {total_genes}")
            logger.info(f"  Orthologs found: {genes_with_orthologs} ({coverage_percent:.1f}%)")
            logger.info(f"=" * 60)

            # Return final statistics (stored in ARQ job result)
            return {
                "organism_id": organism.id,
                "organism_code": organism.code,
                "total_genes": total_genes,
                "genes_with_orthologs": genes_with_orthologs,
                "coverage_percent": coverage_percent,
                "status": "complete"
            }

        except KEGGAPIError as e:
            # KEGG API error after all retries
            # This is a permanent error (mark organism as error)
            error_msg = f"KEGG API error: {str(e)[:900]}"
            logger.error(f"Job {job_id} failed: {error_msg}")

            # Update organism with error
            organism.status = "error"
            organism.job_error = error_msg[:1000]  # Truncate to fit in database
            await session.commit()

            # Mark progress as errored
            await tracker.error(error_msg)

            # Re-raise so ARQ marks job as failed
            raise

        except Exception as e:
            # Unexpected error
            # Log full traceback and mark organism as error
            error_msg = f"Unexpected error: {str(e)[:900]}"
            logger.error(f"Job {job_id} failed with unexpected error:", exc_info=True)

            # Update organism with error
            organism.status = "error"
            organism.job_error = error_msg[:1000]
            await session.commit()

            # Mark progress as errored
            await tracker.error(error_msg)

            # Re-raise so ARQ marks job as failed
            raise


# Export for ARQ worker configuration
__all__ = ['process_organism_job']
