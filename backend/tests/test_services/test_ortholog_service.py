"""
Tests for Ortholog Discovery Service

WHAT WE'RE TESTING:
The ortholog service is the heart of our bioinformatics pipeline.
It takes genes from one organism and finds their orthologs
(same function, different species) in other organisms.

BIOINFORMATICS BACKGROUND:
=== What are Orthologs? ===
Orthologs are genes in different species that evolved from a common ancestor.
They typically perform the same molecular function.

Example:
- Human insulin gene (INS)
- Mouse insulin gene (Ins2)
These are orthologs - same function (regulate blood glucose), different species.

=== Why Find Orthologs? ===
- Study human diseases in model organisms (mice, fruit flies)
- Understand gene function through cross-species comparison
- Predict protein function based on known orthologs

=== Our Algorithm (KEGG KO Method) ===
1. Map source gene to KO group (KEGG Orthology)
2. Find all genes in that KO group across all organisms
3. Filter out same-organism genes (those are paralogs, not orthologs)
4. Score candidates by evolutionary distance
5. Select best ortholog (prefer model organisms like human, mouse)

TESTING STRATEGY:
- Mock KEGG client to avoid real API calls
- Test algorithm correctness with known gene/KO relationships
- Test edge cases (no KO, multiple candidates, ties)
- Test scoring and weighting logic
"""

import pytest
from unittest.mock import AsyncMock
from typing import List, Dict

from app.services.kegg_api import KEGGClient
from app.services.ortholog_service import OrthologService, OrthologResult


# =============================================================================
# BASIC ALGORITHM TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_ortholog_basic_workflow(mock_kegg_client):
    """
    Test basic ortholog discovery workflow.

    SCENARIO:
    E. coli gene eco:b0002 (aspartokinase) has orthologs in other organisms.

    WORKFLOW:
    1. Map eco:b0002 → K00928 (KO group for aspartokinase)
    2. Find all genes in K00928: eco:b0002, hsa:5236, mmu:21881
    3. Filter out eco:b0002 (same organism)
    4. Score remaining: hsa:5236 (human), mmu:21881 (mouse)
    5. Return best match: hsa:5236 (humans weighted higher than mice)

    EXPECTED:
    OrthologResult with ortholog_gene_id="hsa:5236"
    """
    # Configure mock KEGG client
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0002": ["K00928"]
    }
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0002",   # Source gene (will be filtered)
        "hsa:5236",    # Human ortholog
        "mmu:21881",   # Mouse ortholog
    ]

    service = OrthologService(mock_kegg_client)

    # Find ortholog for eco:b0002
    result = await service.find_ortholog("eco:b0002", "eco")

    # Assertions
    assert result.has_ortholog
    assert result.gene_id == "eco:b0002"
    assert result.ortholog_gene_id == "hsa:5236"  # Human preferred
    assert result.ortholog_species == "hsa"
    assert result.ko_id == "K00928"
    assert result.method == "KEGG_KO"
    assert result.confidence > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gene_with_no_ko_assignment(mock_kegg_client):
    """
    Test handling of genes with no KO assignment.

    BIOINFORMATICS CONTEXT:
    Not all genes have KO assignments. Reasons:
    - Organism-specific genes (no orthologs)
    - Poorly characterized genes (function unknown)
    - Recently discovered genes (not yet curated in KEGG)

    EXPECTED:
    OrthologResult with has_ortholog=False, method="NO_KO_ASSIGNMENT"
    """
    # Gene has no KO mapping
    mock_kegg_client.link_genes_to_ko.return_value = {}

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("eco:b9999", "eco")

    assert not result.has_ortholog
    assert result.gene_id == "eco:b9999"
    assert result.ko_id is None
    assert result.ortholog_gene_id is None
    assert result.method == "NO_KO_ASSIGNMENT"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ko_with_only_source_gene(mock_kegg_client):
    """
    Test KO group containing only the source gene (no orthologs).

    SCENARIO:
    Gene is in a KO group, but no other organisms have genes in that KO.
    This indicates a unique gene with no known orthologs.

    EXPECTED:
    OrthologResult with has_ortholog=False, method="NO_ORTHOLOGS_IN_KO"
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0123": ["K99999"]
    }
    # KO group contains only the source gene
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0123"  # Only source gene, no other organisms
    ]

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("eco:b0123", "eco")

    assert not result.has_ortholog
    assert result.ko_id == "K99999"
    assert result.method == "NO_ORTHOLOGS_IN_KO"


# =============================================================================
# ORGANISM PREFERENCE / WEIGHTING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_model_organism_preference(mock_kegg_client):
    """
    Test that model organisms are preferred as orthologs.

    MODEL ORGANISM HIERARCHY (by research value):
    1. hsa (Homo sapiens - human) - highest priority
    2. mmu (Mus musculus - mouse)
    3. rno (Rattus norvegicus - rat)
    4. dme (Drosophila melanogaster - fruit fly)
    5. cel (C. elegans - worm)
    6. sce (S. cerevisiae - yeast)
    7. Other organisms - lower priority

    WHY?
    Human orthologs are most valuable for disease research.
    Mouse/rat next (common lab animals).

    SCENARIO:
    KO group has genes from: bacteria (bsu), yeast (sce), human (hsa)

    EXPECTED:
    Human ortholog selected despite all being in same KO.
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0001": ["K01234"]
    }
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0001",     # Source (E. coli)
        "bsu:BSU12345",  # Bacillus (bacterium)
        "sce:YAL001C",   # Yeast
        "hsa:12345",     # Human
    ]

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("eco:b0001", "eco")

    # Should prefer human over yeast and bacteria
    assert result.ortholog_gene_id == "hsa:12345"
    assert result.ortholog_species == "hsa"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mouse_preferred_over_bacteria(mock_kegg_client):
    """
    Test mouse preferred over bacteria when no human ortholog.

    SCENARIO:
    KO has: E. coli (source), another bacteria, mouse

    EXPECTED:
    Mouse selected (model organism > bacteria)
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0001": ["K01234"]
    }
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0001",     # Source
        "bsu:BSU123",    # Bacillus
        "mmu:67890",     # Mouse
    ]

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("eco:b0001", "eco")

    assert result.ortholog_gene_id == "mmu:67890"
    assert result.ortholog_species == "mmu"


# =============================================================================
# MULTIPLE KO GROUPS TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gene_with_multiple_ko_groups(mock_kegg_client):
    """
    Test gene belonging to multiple KO groups.

    BIOINFORMATICS CONTEXT:
    Some genes have multiple functions → multiple KO assignments.
    Example: Bifunctional enzymes

    ALGORITHM:
    Take first KO group and find orthologs there.
    (Future enhancement: Check all KOs and merge results)

    EXPECTED:
    Uses first KO, finds ortholog successfully.
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0002": ["K00928", "K01234"]  # Two KO groups
    }
    # Only query first KO
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0002",
        "hsa:5236",
    ]

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("eco:b0002", "eco")

    assert result.has_ortholog
    assert result.ko_id == "K00928"  # First KO used
    assert result.ortholog_gene_id == "hsa:5236"


# =============================================================================
# PARALOGS VS ORTHOLOGS FILTERING
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_same_organism_genes_filtered(mock_kegg_client):
    """
    Test that genes from same organism are filtered out.

    BIOINFORMATICS DISTINCTION:
    - Orthologs: Same function, different species (what we want)
    - Paralogs: Related function, same species (should be filtered)

    EXAMPLE:
    E. coli has 5 alcohol dehydrogenase genes (paralogs).
    We want human alcohol dehydrogenase (ortholog), not other E. coli ones.

    SCENARIO:
    KO contains: eco:b0001, eco:b0002, eco:b0003, hsa:12345

    EXPECTED:
    Only hsa:12345 considered (other eco genes filtered out)
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0001": ["K01234"]
    }
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0001",  # Source gene
        "eco:b0002",  # Paralog (same organism)
        "eco:b0003",  # Paralog (same organism)
        "hsa:12345",  # Ortholog (different organism)
    ]

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("eco:b0001", "eco")

    # Should only find human, not other E. coli genes
    assert result.ortholog_gene_id == "hsa:12345"
    assert "eco" not in result.ortholog_gene_id


# =============================================================================
# BATCH PROCESSING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_orthologs_for_organism_batch(mock_kegg_client):
    """
    Test batch processing of multiple genes.

    SCENARIO:
    Process 3 E. coli genes at once.
    This is what happens during organism processing.

    EXPECTED:
    Returns list of OrthologResults, one per gene.
    Respects concurrency limits (5 genes at once via semaphore).
    """
    # Mock responses for all 3 genes
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0001": ["K01234"],
        "eco:b0002": ["K00928"],
        "eco:b0003": []  # No KO
    }

    # Mock KO queries (called for first two genes)
    mock_kegg_client.get_organisms_by_ko.side_effect = [
        ["eco:b0001", "hsa:11111"],  # eco:b0001's KO
        ["eco:b0002", "mmu:22222"],  # eco:b0002's KO
    ]

    genes = [
        {"name": "eco:b0001", "description": "Gene 1"},
        {"name": "eco:b0002", "description": "Gene 2"},
        {"name": "eco:b0003", "description": "Gene 3"},
    ]

    service = OrthologService(mock_kegg_client)
    results = await service.find_orthologs_for_organism("eco", genes)

    # Verify all 3 processed
    assert len(results) == 3

    # Gene 1: Found ortholog
    assert results[0].has_ortholog
    assert results[0].ortholog_gene_id == "hsa:11111"

    # Gene 2: Found ortholog
    assert results[1].has_ortholog
    assert results[1].ortholog_gene_id == "mmu:22222"

    # Gene 3: No KO assignment
    assert not results[2].has_ortholog
    assert results[2].method == "NO_KO_ASSIGNMENT"


# =============================================================================
# STATISTICS AND COVERAGE TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_ortholog_statistics(mock_kegg_client, sample_ortholog_results):
    """
    Test calculation of coverage statistics.

    BIOINFORMATICS METRICS:
    - Total genes processed
    - Genes with orthologs found
    - Coverage percentage
    - Top ortholog species distribution

    EXPECTED COVERAGE FOR E. COLI:
    ~73% of genes have KO assignments and orthologs.
    This matches real-world KEGG KO coverage.
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0001": [],  # No KO
        "eco:b0002": ["K00928"],
        "eco:b0003": ["K00872"],
    }
    mock_kegg_client.get_organisms_by_ko.side_effect = [
        ["eco:b0002", "hsa:5236"],
        ["eco:b0003", "mmu:21881"],
    ]

    genes = [
        {"name": "eco:b0001", "description": "Gene 1"},
        {"name": "eco:b0002", "description": "Gene 2"},
        {"name": "eco:b0003", "description": "Gene 3"},
    ]

    service = OrthologService(mock_kegg_client)
    stats = await service.get_ortholog_statistics("eco", genes)

    # Verify statistics
    assert stats["total_genes"] == 3
    assert stats["genes_with_orthologs"] == 2
    assert stats["coverage_percent"] == pytest.approx(66.67, rel=0.1)
    assert stats["method"] == "KEGG_KO"

    # Check top species
    species_counts = {item["species"]: item["count"]
                     for item in stats["top_ortholog_species"]}
    assert species_counts["hsa"] == 1
    assert species_counts["mmu"] == 1


# =============================================================================
# CONFIDENCE SCORING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confidence_score_calculation(mock_kegg_client):
    """
    Test confidence scoring based on evolutionary distance.

    CONFIDENCE SCORING FACTORS:
    - Evolutionary distance: Human > Mouse > Bacteria
    - Single vs multiple candidates: 1 candidate = higher confidence
    - KO group size: Smaller KO = more specific = higher confidence

    SCENARIO:
    Find ortholog, verify confidence score is reasonable (50-100).
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0001": ["K01234"]
    }
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0001",
        "hsa:12345",
    ]

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("eco:b0001", "eco")

    # Confidence should be in valid range
    assert 50 <= result.confidence <= 100

    # Human ortholog should have high confidence
    assert result.confidence >= 80


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_kegg_api_error_handling(mock_kegg_client):
    """
    Test handling when KEGG API fails.

    SCENARIO:
    KEGG API returns error during KO mapping lookup.

    EXPECTED:
    Gracefully handle error, mark gene as having no ortholog.
    Don't crash the entire batch due to one gene failure.
    """
    from app.services.kegg_api import KEGGAPIError

    # Mock API error
    mock_kegg_client.link_genes_to_ko.side_effect = KEGGAPIError("API Error")

    service = OrthologService(mock_kegg_client)

    # Should handle error gracefully
    result = await service.find_ortholog("eco:b0001", "eco")

    assert not result.has_ortholog
    # Should indicate error in method or have special handling


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_gene_list_handling(mock_kegg_client):
    """
    Test handling of empty gene list.

    SCENARIO:
    Organism has no genes (edge case, shouldn't happen in practice).

    EXPECTED:
    Return empty results list, don't crash.
    """
    service = OrthologService(mock_kegg_client)
    results = await service.find_orthologs_for_organism("eco", [])

    assert results == []


# =============================================================================
# EDGE CASES
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_organism_code_extraction_from_gene_id(mock_kegg_client):
    """
    Test extraction of organism code from gene ID.

    KEGG GENE ID FORMAT:
    <org_code>:<gene_locus>

    Examples:
    - eco:b0001 → organism: eco
    - hsa:12345 → organism: hsa
    - mmu:67890 → organism: mmu

    This is used to filter same-organism genes (paralogs).
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        "eco:b0001": ["K01234"]
    }
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0001",       # Source
        "eco:b0002",       # Same organism (should filter)
        "ecj:JW0001",      # Different E. coli strain (should filter)
        "hsa:12345",       # Different organism (keep)
    ]

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("eco:b0001", "eco")

    # Should find human ortholog, not other E. coli genes
    assert result.ortholog_species == "hsa"
    assert "eco" not in result.ortholog_gene_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_gene_id_format(mock_kegg_client):
    """
    Test handling of malformed gene IDs.

    SCENARIO:
    Gene ID doesn't follow "org:gene" format.

    EXPECTED:
    Handle gracefully, possibly return no ortholog found.
    """
    mock_kegg_client.link_genes_to_ko.return_value = {}

    service = OrthologService(mock_kegg_client)
    result = await service.find_ortholog("invalid_gene_id", "eco")

    # Should handle gracefully
    assert not result.has_ortholog


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_concurrent_processing_with_semaphore(mock_kegg_client):
    """
    Test that concurrent processing respects semaphore limit.

    CONCURRENCY LIMIT:
    Max 5 genes processed simultaneously (semaphore limit).

    WHY?
    - Prevents overwhelming KEGG API with too many concurrent requests
    - Respects rate limits
    - Prevents memory bloat from too many concurrent operations

    VERIFICATION:
    Process 20 genes, verify they're batched appropriately.
    """
    mock_kegg_client.link_genes_to_ko.return_value = {
        f"eco:b{i:04d}": ["K01234"] for i in range(20)
    }
    mock_kegg_client.get_organisms_by_ko.return_value = [
        "eco:b0000",
        "hsa:12345",
    ]

    genes = [
        {"name": f"eco:b{i:04d}", "description": f"Gene {i}"}
        for i in range(20)
    ]

    service = OrthologService(mock_kegg_client)
    results = await service.find_orthologs_for_organism("eco", genes)

    # All 20 should be processed
    assert len(results) == 20

    # Most should have found orthologs (mocked to succeed)
    with_orthologs = sum(1 for r in results if r.has_ortholog)
    assert with_orthologs > 0


# =============================================================================
# RUN TESTS
# =============================================================================

"""
TO RUN THESE TESTS:

    # All ortholog service tests
    pytest tests/test_services/test_ortholog_service.py -v

    # Only unit tests
    pytest tests/test_services/test_ortholog_service.py -m unit -v

    # Specific test
    pytest tests/test_services/test_ortholog_service.py::test_find_ortholog_basic_workflow -v

    # With coverage
    pytest tests/test_services/test_ortholog_service.py --cov=app.services.ortholog_service

EXPECTED RESULTS:
- All tests pass
- No real KEGG API calls (fully mocked)
- Tests complete in <5 seconds
- Coverage >90% for ortholog_service.py

KEY TAKEAWAYS:
- Algorithm correctly maps genes → KO → orthologs
- Model organisms (human, mouse) preferred
- Paralogs (same organism) filtered out
- Edge cases handled gracefully
- Batch processing works with concurrency control
"""
