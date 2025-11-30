"""
Quick test script for KEGG API client.

Usage: python test_kegg_client.py
"""

import asyncio
import sys
sys.path.insert(0, '/app')

from app.services.kegg_api import KEGGClient, fetch_organism_genes


async def test_kegg_client():
    """Test the KEGG API client with E. coli (small organism)."""

    print("=" * 60)
    print("Testing KEGG API Client")
    print("=" * 60)

    # Test 1: Fetch genes for E. coli K-12 (eco)
    print("\n[Test 1] Fetching genes for E. coli (eco)...")
    print("This organism has ~4,300 genes, so this might take a few moments.")
    print("-" * 60)

    try:
        async with KEGGClient() as client:
            genes = await client.list_organism_genes("eco")

            print(f"\n✓ Success! Retrieved {len(genes)} genes")
            print(f"\nFirst 5 genes:")
            for gene in genes[:5]:
                print(f"  - {gene['name']}: {gene['description'][:60]}...")

            if len(genes) > 5:
                print(f"  ... and {len(genes) - 5} more genes")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

    # Test 2: Fetch KO mappings
    print("\n" + "=" * 60)
    print("[Test 2] Fetching KO (KEGG Orthology) mappings for eco...")
    print("-" * 60)

    try:
        async with KEGGClient() as client:
            ko_mappings = await client.link_genes_to_ko("eco")

            print(f"\n✓ Success! Retrieved KO mappings for {len(ko_mappings)} genes")

            # Show a few examples
            count = 0
            print(f"\nSample KO mappings:")
            for gene_id, ko_ids in ko_mappings.items():
                print(f"  - {gene_id} → {', '.join(ko_ids)}")
                count += 1
                if count >= 5:
                    break

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

    # Test 3: Test with a smaller organism for speed
    print("\n" + "=" * 60)
    print("[Test 3] Quick test with Mycoplasma genitalium (smallest bacteria)")
    print("-" * 60)

    try:
        genes = await fetch_organism_genes("mgn")
        print(f"\n✓ Success! Retrieved {len(genes)} genes for M. genitalium")
        print(f"   (This organism only has ~500 genes)")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = asyncio.run(test_kegg_client())
    sys.exit(0 if success else 1)
