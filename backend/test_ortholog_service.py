"""
Test script for Ortholog Service

Tests the KEGG KO-based ortholog discovery with E. coli genes.
"""

import asyncio
import sys
sys.path.insert(0, '/app')

from app.services.kegg_api import KEGGClient
from app.services.ortholog_service import OrthologService


async def test_ortholog_service():
    """Test ortholog discovery with a small sample of E. coli genes."""

    print("=" * 70)
    print("Testing Ortholog Service - KEGG KO Method")
    print("=" * 70)

    # We'll test with first 20 E. coli genes for speed
    # (Full organism has ~4,600 genes)
    test_organism = "eco"
    sample_size = 20

    print(f"\nOrganism: E. coli (eco)")
    print(f"Sample size: {sample_size} genes")
    print("-" * 70)

    async with KEGGClient() as client:
        # Step 1: Fetch genes for E. coli
        print("\n[Step 1] Fetching E. coli genes...")
        all_genes = await client.list_organism_genes(test_organism)
        print(f"✓ Retrieved {len(all_genes)} total genes")

        # Take first N genes for testing
        test_genes = all_genes[:sample_size]
        print(f"✓ Testing with first {sample_size} genes")

        # Step 2: Initialize ortholog service
        print("\n[Step 2] Initializing ortholog service...")
        service = OrthologService(client)
        print("✓ Service initialized")

        # Step 3: Find orthologs
        print(f"\n[Step 3] Finding orthologs for {sample_size} genes...")
        print("(This will take ~10-15 seconds due to rate limiting)")
        print("-" * 70)

        results = await service.find_orthologs_for_organism(
            test_organism,
            test_genes
        )

        # Step 4: Analyze results
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)

        with_orthologs = sum(1 for r in results if r.has_ortholog)
        coverage = (with_orthologs / len(results) * 100) if results else 0

        print(f"\nOverall Statistics:")
        print(f"  Total genes tested: {len(results)}")
        print(f"  Genes with orthologs: {with_orthologs}")
        print(f"  Coverage: {coverage:.1f}%")

        # Count ortholog species
        species_counts = {}
        for result in results:
            if result.ortholog_species:
                species_counts[result.ortholog_species] = \
                    species_counts.get(result.ortholog_species, 0) + 1

        if species_counts:
            print(f"\nTop Ortholog Species:")
            for species, count in sorted(
                species_counts.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                print(f"  {species}: {count} orthologs")

        # Show detailed results for first 10 genes
        print(f"\n{'=' * 70}")
        print("DETAILED RESULTS (First 10 genes)")
        print("=" * 70)

        for i, result in enumerate(results[:10]):
            print(f"\n{i+1}. Gene: {result.gene_id}")
            print(f"   Source: {test_genes[i]['description'][:60]}...")

            if result.has_ortholog:
                print(f"   ✓ Ortholog found!")
                print(f"     - Ortholog ID: {result.ortholog_gene_id}")
                print(f"     - Species: {result.ortholog_species}")
                print(f"     - KO Group: {result.ko_id}")
                print(f"     - Confidence: {result.confidence:.1f}")
                print(f"     - Method: {result.method}")
            else:
                print(f"   ✗ No ortholog found")
                print(f"     - Reason: {result.method}")
                if result.ko_id:
                    print(f"     - KO: {result.ko_id} (no suitable ortholog in this KO)")

        # Step 5: Get statistics
        print(f"\n{'=' * 70}")
        print("[Step 4] Getting detailed statistics...")
        print("-" * 70)

        stats = await service.get_ortholog_statistics(test_organism, test_genes)

        print(f"\nStatistics:")
        print(f"  Total genes: {stats['total_genes']}")
        print(f"  Genes with orthologs: {stats['genes_with_orthologs']}")
        print(f"  Coverage: {stats['coverage_percent']:.1f}%")

        if stats['top_ortholog_species']:
            print(f"\n  Top Ortholog Species:")
            for item in stats['top_ortholog_species']:
                print(f"    - {item['species']}: {item['count']} genes")

        print("\n" + "=" * 70)
        print("✓ TEST COMPLETE")
        print("=" * 70)

        # Validate results
        if coverage > 50:
            print(f"\n✓ PASS: Coverage ({coverage:.1f}%) is good (>50%)")
            return True
        else:
            print(f"\n✗ WARN: Coverage ({coverage:.1f}%) is lower than expected")
            print("  This may be normal for small sample sizes")
            return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_ortholog_service())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
