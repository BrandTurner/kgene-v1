"""
CSV Export Service for KEGG Explore API

**What**: Exports gene and ortholog data to CSV format
**Why**: Researchers need to download results for analysis in Excel, R, Python, etc.
**How**: Streaming CSV generation using async generators (memory efficient)

**Bioinformatics Context**:
CSV is the universal format for sharing biological data:
- Import into Excel for quick analysis
- Load into R/Python for statistical analysis
- Share with collaborators without special software
- Archive results for publications

**Usage Example**:
```python
from app.services.csv_export import export_organism_genes_csv

@router.get("/organisms/{id}/download")
async def download(organism_id: int, db: AsyncSession = Depends(get_db)):
    # Stream CSV directly to response
    generator = export_organism_genes_csv(db, organism_id)
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=eco_genes.csv"}
    )
```
"""

import csv
import io
from typing import AsyncIterator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Gene, Organism
from app.core.exceptions import OrganismNotFoundError


# =============================================================================
# CSV Export Functions
# =============================================================================

async def export_organism_genes_csv(
    db: AsyncSession,
    organism_id: int,
    include_no_orthologs: bool = True
) -> AsyncIterator[str]:
    """
    Export all genes for an organism to CSV format (streaming).

    **What**: Generates CSV with gene and ortholog data
    **Why**: Streaming prevents memory issues with large datasets (4,600+ genes)
    **How**: Yields CSV chunks as they're generated (generator pattern)

    **Args**:
    - db: Database session
    - organism_id: Organism to export
    - include_no_orthologs: Include genes without orthologs (default: True)

    **Returns**: Async generator yielding CSV chunks (strings)

    **CSV Format**:
    ```
    gene_name,gene_description,ortholog_name,ortholog_description,ortholog_species,ortholog_length,ortholog_sw_score,ortholog_identity
    eco:b0001,thrL; thr operon leader peptide,hsa:10458,Actin-like 6A,Homo sapiens,429,1250,45.5
    eco:b0002,thrA; Bifunctional aspartokinase,,,,,
    ```

    **Bioinformatics Note**:
    Genes without orthologs (orphan genes) are included by default because:
    - They're scientifically interesting (species-specific innovations)
    - Researchers want complete datasets
    - Empty ortholog columns clearly show "no match found"
    """
    # Verify organism exists
    result = await db.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    organism = result.scalar_one_or_none()
    if not organism:
        raise OrganismNotFoundError(organism_id=organism_id)

    # Build query for genes
    query = select(Gene).where(Gene.organism_id == organism_id)

    # Filter by ortholog presence if requested
    if not include_no_orthologs:
        # Only include genes WITH orthologs
        query = query.where(Gene.ortholog_name.isnot(None))

    # Order by gene name for consistent output
    query = query.order_by(Gene.name)

    # Execute query
    result = await db.execute(query)
    genes = result.scalars().all()

    # Create CSV in memory (StringIO buffer)
    output = io.StringIO()
    writer = csv.writer(output)

    # Write CSV header
    # **Column Descriptions**:
    # - gene_name: KEGG gene identifier (e.g., "eco:b0001")
    # - gene_description: Gene function/annotation from KEGG
    # - ortholog_name: Best ortholog match gene identifier
    # - ortholog_description: Ortholog function
    # - ortholog_species: Organism name of ortholog (e.g., "Homo sapiens")
    # - ortholog_length: Sequence length of ortholog (amino acids or nucleotides)
    # - ortholog_sw_score: Smith-Waterman alignment score
    # - ortholog_identity: Sequence identity percentage (0-100)
    writer.writerow([
        "gene_name",
        "gene_description",
        "ortholog_name",
        "ortholog_description",
        "ortholog_species",
        "ortholog_length",
        "ortholog_sw_score",
        "ortholog_identity"
    ])

    # Yield header
    yield output.getvalue()
    output.truncate(0)
    output.seek(0)

    # Write gene rows in batches
    # **Why batches**: Prevents building huge string in memory
    # **Batch size**: 100 genes per chunk (good balance)
    batch_size = 100
    for i, gene in enumerate(genes):
        # Write row
        writer.writerow([
            gene.name or "",
            gene.description or "",
            gene.ortholog_name or "",
            gene.ortholog_description or "",
            gene.ortholog_species or "",
            gene.ortholog_length if gene.ortholog_length is not None else "",
            gene.ortholog_sw_score if gene.ortholog_sw_score is not None else "",
            f"{gene.ortholog_identity:.2f}" if gene.ortholog_identity is not None else ""
        ])

        # Yield batch every N rows
        if (i + 1) % batch_size == 0:
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    # Yield remaining rows
    if output.getvalue():
        yield output.getvalue()


async def export_genes_csv(
    db: AsyncSession,
    organism_id: Optional[int] = None,
    has_ortholog: Optional[bool] = None,
    min_identity: Optional[float] = None,
    max_identity: Optional[float] = None,
    ortholog_species: Optional[str] = None,
    limit: int = 10000
) -> AsyncIterator[str]:
    """
    Export genes to CSV with optional filtering (streaming).

    **What**: Filtered gene export (supports same filters as GET /genes)
    **Why**: Export specific subsets (e.g., only high-confidence orthologs)
    **How**: Applies filters before generating CSV

    **Args**:
    - db: Database session
    - organism_id: Filter by organism
    - has_ortholog: Filter by ortholog presence
    - min_identity: Minimum identity percentage
    - max_identity: Maximum identity percentage
    - ortholog_species: Filter by species name (partial match)
    - limit: Max genes to export (default: 10,000, prevents accidental huge exports)

    **Returns**: Async generator yielding CSV chunks

    **Use Cases**:
    ```
    # Export only high-confidence orthologs (>70% identity)
    GET /genes/export?organism_id=1&min_identity=70.0

    # Export orphan genes only
    GET /genes/export?organism_id=1&has_ortholog=false

    # Export genes with human orthologs
    GET /genes/export?organism_id=1&ortholog_species=Homo sapiens
    ```
    """
    # Build query with filters
    query = select(Gene)

    if organism_id is not None:
        query = query.where(Gene.organism_id == organism_id)

    if has_ortholog is not None:
        if has_ortholog:
            query = query.where(Gene.ortholog_name.isnot(None))
        else:
            query = query.where(Gene.ortholog_name.is_(None))

    if min_identity is not None:
        query = query.where(Gene.ortholog_identity >= min_identity)

    if max_identity is not None:
        query = query.where(Gene.ortholog_identity <= max_identity)

    if ortholog_species:
        query = query.where(Gene.ortholog_species.ilike(f"%{ortholog_species}%"))

    # Order and limit
    query = query.order_by(Gene.name).limit(limit)

    # Execute query
    result = await db.execute(query)
    genes = result.scalars().all()

    # Generate CSV (same logic as export_organism_genes_csv)
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "gene_name",
        "gene_description",
        "ortholog_name",
        "ortholog_description",
        "ortholog_species",
        "ortholog_length",
        "ortholog_sw_score",
        "ortholog_identity"
    ])

    yield output.getvalue()
    output.truncate(0)
    output.seek(0)

    # Write rows in batches
    batch_size = 100
    for i, gene in enumerate(genes):
        writer.writerow([
            gene.name or "",
            gene.description or "",
            gene.ortholog_name or "",
            gene.ortholog_description or "",
            gene.ortholog_species or "",
            gene.ortholog_length if gene.ortholog_length is not None else "",
            gene.ortholog_sw_score if gene.ortholog_sw_score is not None else "",
            f"{gene.ortholog_identity:.2f}" if gene.ortholog_identity is not None else ""
        ])

        if (i + 1) % batch_size == 0:
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    # Yield remaining
    if output.getvalue():
        yield output.getvalue()


# =============================================================================
# Helper Functions
# =============================================================================

def get_csv_filename(organism_code: str, include_no_orthologs: bool = True) -> str:
    """
    Generate CSV filename based on organism and filters.

    **What**: Creates descriptive filename for download
    **Why**: Users want meaningful filenames, not "download.csv"
    **Format**: {organism_code}_genes[_orthologs_only].csv

    **Examples**:
    - eco_genes.csv (all genes)
    - eco_genes_orthologs_only.csv (orthologs only)
    - hsa_genes.csv (human genes)
    """
    suffix = "" if include_no_orthologs else "_orthologs_only"
    return f"{organism_code}_genes{suffix}.csv"


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'export_organism_genes_csv',
    'export_genes_csv',
    'get_csv_filename',
]
