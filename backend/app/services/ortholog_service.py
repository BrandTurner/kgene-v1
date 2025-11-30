"""
Ortholog Discovery Service

This module finds orthologous genes across species using the KEGG KO (KEGG Orthology) API.

=== BIOINFORMATICS PRIMER ===

What are Orthologs?
-------------------
Orthologs are genes in different species that evolved from a common ancestral gene
through speciation events. They typically retain the same molecular function.

Example: Human insulin gene and mouse insulin gene are orthologs
- Both came from ancestral mammalian insulin gene
- Both regulate blood glucose
- ~85% sequence identity

Why Find Orthologs?
-------------------
1. Functional prediction: If gene X in organism A is orthologous to gene Y in organism B,
   and we know Y's function, we can infer X likely has the same function
2. Evolutionary studies: Track how genes evolved across species
3. Drug development: Find targets that work across species (mouse models → humans)
4. Disease research: Study human disease genes in model organisms (flies, worms, etc.)

What is KEGG KO?
----------------
KO = KEGG Orthology groups. Each KO group (identified by a K number like K12524)
contains genes from multiple species that perform the same molecular function.

Example KO group K12524:
- eco:b0002 (E. coli gene)
- hsa:2052 (Human gene)
- mmu:1234 (Mouse gene)
All three genes are aspartate kinase/homoserine dehydrogenase enzymes

How We Find Orthologs:
----------------------
1. Get gene's KO assignment (e.g., eco:b0002 → K12524)
2. Get all genes in that KO from other species
3. Filter out genes from same species
4. Rank by evolutionary distance and quality
5. Return best ortholog

=== END PRIMER ===
"""

import asyncio
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from app.services.kegg_api import KEGGClient, KEGGAPIError

logger = logging.getLogger(__name__)


@dataclass
class OrthologResult:
    """
    Result of ortholog search for a single gene.

    Attributes:
        gene_id: Original gene ID (e.g., "eco:b0002")
        ortholog_gene_id: Ortholog gene ID (e.g., "hsa:2052")
        ortholog_species: Species code (e.g., "hsa" for Homo sapiens)
        ortholog_name: Full ortholog identifier
        ortholog_description: Functional description from KEGG
        ko_id: KO group ID that linked them (e.g., "ko:K12524")
        confidence: Confidence score (0-100, higher = better)
        method: How ortholog was found ("KEGG_KO", "OMA", etc.)
    """
    gene_id: str
    ortholog_gene_id: Optional[str]
    ortholog_species: Optional[str]
    ortholog_name: Optional[str]
    ortholog_description: Optional[str]
    ko_id: Optional[str]
    confidence: float
    method: str

    @property
    def has_ortholog(self) -> bool:
        """Check if a valid ortholog was found."""
        return self.ortholog_gene_id is not None


class OrthologService:
    """
    Service for discovering orthologous genes across species.

    Currently implements KEGG KO-based ortholog finding.
    Future: Will support OMA, eggNOG, OrthoDB as fallbacks.
    """

    # Preferred model organisms for ortholog selection
    # These are well-studied species with high-quality annotations
    # We prefer these when multiple orthologs are available
    MODEL_ORGANISMS = {
        'hsa': 100,  # Homo sapiens (human) - most studied mammal
        'mmu': 95,   # Mus musculus (mouse) - primary mammalian model
        'dme': 90,   # Drosophila melanogaster (fruit fly) - invertebrate model
        'cel': 90,   # C. elegans (roundworm) - development model
        'sce': 85,   # S. cerevisiae (yeast) - eukaryotic cell model
        'eco': 80,   # E. coli - primary bacterial model
        'bsu': 75,   # B. subtilis - gram-positive bacterial model
        'ath': 80,   # A. thaliana (thale cress) - plant model
        'rno': 90,   # Rattus norvegicus (rat) - mammalian model
        'dre': 85,   # Danio rerio (zebrafish) - vertebrate development model
    }

    def __init__(self, kegg_client: KEGGClient):
        """
        Initialize ortholog service.

        Args:
            kegg_client: Initialized KEGG API client
        """
        self.kegg_client = kegg_client
        self._ko_cache: Dict[str, List[str]] = {}  # Cache KO → genes mappings

    async def find_orthologs_for_organism(
        self,
        organism_code: str,
        genes: List[Dict[str, str]]
    ) -> List[OrthologResult]:
        """
        Find orthologs for all genes in an organism.

        This is the main entry point for batch ortholog discovery.
        Uses concurrent processing to speed up API calls while respecting rate limits.

        Args:
            organism_code: KEGG organism code (e.g., "eco")
            genes: List of gene dicts with 'name' and 'description'

        Returns:
            List of OrthologResult objects, one per gene

        Example:
            genes = [
                {'name': 'eco:b0001', 'description': 'thrL; thr operon leader'},
                {'name': 'eco:b0002', 'description': 'thrA; aspartate kinase'},
            ]
            results = await service.find_orthologs_for_organism('eco', genes)
        """
        logger.info(f"Finding orthologs for {len(genes)} genes in organism {organism_code}")

        # Step 1: Get KO mappings for ALL genes in this organism (single API call)
        # This is much faster than querying each gene individually
        ko_mappings = await self._get_ko_mappings_for_organism(organism_code)

        logger.info(
            f"Retrieved KO mappings for {len(ko_mappings)} / {len(genes)} genes "
            f"({len(ko_mappings) / len(genes) * 100:.1f}% coverage)"
        )

        # Step 2: Find orthologs for each gene using the KO mappings
        # Use semaphore to limit concurrent API calls (respect rate limits)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent ortholog lookups

        async def find_with_semaphore(gene: Dict[str, str]) -> OrthologResult:
            """Wrapper to limit concurrent API calls."""
            async with semaphore:
                return await self.find_ortholog_for_gene(
                    gene['name'],
                    organism_code,
                    ko_mappings
                )

        # Process all genes concurrently (but limited by semaphore)
        results = await asyncio.gather(
            *[find_with_semaphore(gene) for gene in genes],
            return_exceptions=True  # Don't fail entire batch if one gene fails
        )

        # Filter out exceptions and log errors
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error finding ortholog for {genes[i]['name']}: {result}")
                # Create a "no ortholog found" result for this gene
                valid_results.append(OrthologResult(
                    gene_id=genes[i]['name'],
                    ortholog_gene_id=None,
                    ortholog_species=None,
                    ortholog_name=None,
                    ortholog_description=None,
                    ko_id=None,
                    confidence=0.0,
                    method='ERROR'
                ))
            else:
                valid_results.append(result)

        # Log summary statistics
        with_orthologs = sum(1 for r in valid_results if r.has_ortholog)
        logger.info(
            f"Ortholog discovery complete: {with_orthologs} / {len(genes)} genes "
            f"({with_orthologs / len(genes) * 100:.1f}%) have orthologs"
        )

        return valid_results

    async def _get_ko_mappings_for_organism(
        self,
        organism_code: str
    ) -> Dict[str, List[str]]:
        """
        Get KO (KEGG Orthology) assignments for all genes in an organism.

        Why this is efficient:
        - Single API call gets KO for ALL genes
        - Result: gene_id → [ko_id1, ko_id2, ...]
        - Cache the result for subsequent lookups

        Args:
            organism_code: KEGG organism code (e.g., "eco")

        Returns:
            Dict mapping gene IDs to their KO assignments

        Example:
            {
                'eco:b0001': ['ko:K08278'],
                'eco:b0002': ['ko:K12524'],
                'eco:b0003': ['ko:K00872'],
            }

        Note: Some genes have multiple KO assignments (multi-functional genes)
        Note: Some genes have NO KO assignment (~27% in E. coli)
        """
        logger.debug(f"Fetching KO mappings for organism {organism_code}")

        # Use KEGG API to get all gene → KO mappings
        # This returns TSV format: gene_id\tko_id
        return await self.kegg_client.link_genes_to_ko(organism_code)

    async def find_ortholog_for_gene(
        self,
        gene_id: str,
        organism_code: str,
        ko_mappings: Optional[Dict[str, List[str]]] = None
    ) -> OrthologResult:
        """
        Find the best ortholog for a single gene using KEGG KO.

        Algorithm:
        1. Check if gene has KO assignment
        2. Get all genes in that KO group
        3. Filter out genes from same organism (not orthologs!)
        4. Rank by evolutionary distance and model organism preference
        5. Return best ortholog

        Args:
            gene_id: KEGG gene ID (e.g., "eco:b0002")
            organism_code: Source organism code (e.g., "eco")
            ko_mappings: Pre-fetched KO mappings (optional, for efficiency)

        Returns:
            OrthologResult with best ortholog or None if not found

        Bioinformatics Note:
            We prefer evolutionarily DISTANT orthologs (human vs E. coli) over
            close relatives (E. coli K12 vs E. coli O157) because:
            - Function is more conserved across large evolutionary distances
            - More interesting for comparative genomics
            - Better for functional inference
        """
        logger.debug(f"Finding ortholog for gene {gene_id}")

        # Step 1: Get KO assignment(s) for this gene
        if ko_mappings and gene_id in ko_mappings:
            ko_ids = ko_mappings[gene_id]
        else:
            # Fallback: Query individual gene (slower)
            logger.debug(f"No cached KO for {gene_id}, querying individually")
            ko_ids = []
            # TODO: Implement single-gene KO lookup if needed

        if not ko_ids:
            logger.debug(f"No KO assignment for {gene_id}")
            return OrthologResult(
                gene_id=gene_id,
                ortholog_gene_id=None,
                ortholog_species=None,
                ortholog_name=None,
                ortholog_description=None,
                ko_id=None,
                confidence=0.0,
                method='KEGG_KO_NO_ASSIGNMENT'
            )

        # Step 2: For each KO, get all genes in that KO group
        # If gene has multiple KOs, try each one until we find an ortholog
        for ko_id in ko_ids:
            try:
                ortholog = await self._find_best_ortholog_in_ko(
                    gene_id,
                    ko_id,
                    organism_code
                )

                if ortholog:
                    return ortholog

            except KEGGAPIError as e:
                logger.warning(f"Error searching KO {ko_id} for {gene_id}: {e}")
                continue

        # No ortholog found in any KO group
        return OrthologResult(
            gene_id=gene_id,
            ortholog_gene_id=None,
            ortholog_species=None,
            ortholog_name=None,
            ortholog_description=None,
            ko_id=ko_ids[0] if ko_ids else None,
            confidence=0.0,
            method='KEGG_KO_NO_ORTHOLOG'
        )

    async def _find_best_ortholog_in_ko(
        self,
        gene_id: str,
        ko_id: str,
        exclude_organism: str
    ) -> Optional[OrthologResult]:
        """
        Find best ortholog within a specific KO group.

        Ranking Strategy:
        1. Exclude genes from same organism (not orthologs!)
        2. Prefer model organisms (well-studied, high-quality annotations)
        3. Prefer evolutionarily distant species (more informative)
        4. For tied ranks, prefer the first one (arbitrary but consistent)

        Args:
            gene_id: Source gene ID (e.g., "eco:b0002")
            ko_id: KO group to search (e.g., "ko:K12524")
            exclude_organism: Organism to exclude (e.g., "eco")

        Returns:
            OrthologResult with best match, or None if no suitable ortholog

        Bioinformatics Concepts:
            - KO group = genes with same molecular function
            - Same species = paralogs (not orthologs)
            - Different species = potential orthologs
            - Model organisms = better annotations, more reliable
        """
        # Get all genes in this KO group
        # This will return genes from many species
        genes_in_ko = await self.kegg_client.get_organisms_by_ko(ko_id)

        if not genes_in_ko:
            return None

        # Filter and rank potential orthologs
        candidates = []

        for candidate_gene_id in genes_in_ko:
            # Parse organism code from gene ID
            # Format: "org:gene" (e.g., "hsa:10458", "eco:b0002")
            if ':' not in candidate_gene_id:
                continue

            candidate_org = candidate_gene_id.split(':')[0]

            # Skip genes from same organism (these are paralogs, not orthologs!)
            if candidate_org == exclude_organism:
                continue

            # Skip if it's the exact same gene (shouldn't happen, but be safe)
            if candidate_gene_id == gene_id:
                continue

            # Calculate rank score
            # Higher score = better ortholog candidate
            score = self._calculate_ortholog_score(
                source_org=exclude_organism,
                candidate_org=candidate_org
            )

            candidates.append((candidate_gene_id, candidate_org, score))

        if not candidates:
            return None

        # Sort by score (descending) and take best
        candidates.sort(key=lambda x: x[2], reverse=True)
        best_gene_id, best_org, score = candidates[0]

        logger.debug(
            f"Best ortholog for {gene_id} in KO {ko_id}: "
            f"{best_gene_id} (score: {score:.1f})"
        )

        # Get description for the ortholog gene
        # We'll need to fetch this from the gene list for that organism
        # For now, use a placeholder (can enhance later)
        description = f"Ortholog from {best_org}"

        return OrthologResult(
            gene_id=gene_id,
            ortholog_gene_id=best_gene_id,
            ortholog_species=best_org,
            ortholog_name=best_gene_id,
            ortholog_description=description,
            ko_id=ko_id,
            confidence=score,
            method='KEGG_KO'
        )

    def _calculate_ortholog_score(
        self,
        source_org: str,
        candidate_org: str
    ) -> float:
        """
        Calculate preference score for an ortholog candidate.

        Scoring Factors:
        1. Model organism bonus: +100 for human, +95 for mouse, etc.
        2. Domain diversity: Prefer candidates from different domains
           (e.g., if source is bacteria, prefer eukaryote ortholog)
        3. Not same species: Already filtered, but emphasize

        Returns:
            Score from 0-200 (higher = better candidate)

        Bioinformatics Rationale:
            - Model organisms have better annotations (more useful)
            - Cross-domain orthologs show deeper evolutionary conservation
            - Human orthologs are most relevant for medical research
        """
        score = 0.0

        # Model organism bonus
        if candidate_org in self.MODEL_ORGANISMS:
            score += self.MODEL_ORGANISMS[candidate_org]

        # Domain diversity bonus (simplified)
        # Prokaryotes: eco, bsu, etc. (3-letter codes, often lowercase)
        # Eukaryotes: hsa, mmu, dme, etc. (usually 3 letters)
        # This is a crude heuristic; a real implementation would use taxonomy

        # Example: If source is E. coli (prokaryote), prefer human (eukaryote)
        # This maximizes evolutionary distance
        if source_org == 'eco' and candidate_org == 'hsa':
            score += 10  # Cross-domain bonus

        # Similarly for other common pairs
        if source_org in ['eco', 'bsu'] and candidate_org in ['hsa', 'mmu', 'dme']:
            score += 5

        return score

    async def get_ortholog_statistics(
        self,
        organism_code: str,
        genes: List[Dict[str, str]]
    ) -> Dict[str, any]:
        """
        Get statistics about ortholog coverage for an organism.

        Useful for quality control and user feedback.

        Returns:
            Dict with statistics:
            - total_genes: Total genes analyzed
            - genes_with_ko: Genes that have KO assignments
            - genes_with_orthologs: Genes where we found orthologs
            - coverage_percent: % of genes with orthologs
            - top_ortholog_species: Most common ortholog species
        """
        results = await self.find_orthologs_for_organism(organism_code, genes)

        total = len(results)
        with_orthologs = sum(1 for r in results if r.has_ortholog)

        # Count ortholog species
        species_counts: Dict[str, int] = {}
        for result in results:
            if result.ortholog_species:
                species_counts[result.ortholog_species] = \
                    species_counts.get(result.ortholog_species, 0) + 1

        # Sort species by count
        top_species = sorted(
            species_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            'total_genes': total,
            'genes_with_orthologs': with_orthologs,
            'coverage_percent': (with_orthologs / total * 100) if total > 0 else 0,
            'top_ortholog_species': [
                {'species': sp, 'count': count}
                for sp, count in top_species
            ]
        }


# Convenience function for single-use
async def find_orthologs(
    organism_code: str,
    genes: List[Dict[str, str]]
) -> List[OrthologResult]:
    """
    Convenience function to find orthologs without managing client lifecycle.

    Args:
        organism_code: KEGG organism code
        genes: List of gene dicts

    Returns:
        List of OrthologResult objects
    """
    async with KEGGClient() as client:
        service = OrthologService(client)
        return await service.find_orthologs_for_organism(organism_code, genes)
