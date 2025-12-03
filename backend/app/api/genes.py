from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.exceptions import GeneNotFoundError, OrganismNotFoundError
from app.database import get_db
from app.models import Gene, Organism
from app.schemas import gene as schemas
from app.schemas.filters import GeneListParams
from app.services.csv_export import export_genes_csv

router = APIRouter()


@router.get("/genes", response_model=List[schemas.Gene])
async def list_genes(
    params: GeneListParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    List all genes with optional filtering and sorting.

    **Query Parameters**:
    - organism_id: Filter by organism ID
    - has_ortholog: Filter by ortholog presence (true=has, false=no ortholog)
    - min_identity: Minimum ortholog identity percentage (0-100)
    - max_identity: Maximum ortholog identity percentage (0-100)
    - ortholog_species: Filter by ortholog species (case-insensitive partial match)
    - sort_by: Field to sort by (name/ortholog_identity/ortholog_sw_score/created_at)
    - order: Sort order (asc/desc)
    - skip: Pagination offset (default: 0)
    - limit: Max records to return (default: 100, max: 1000)

    **Bioinformatics Examples**:
    ```
    # Get genes WITH orthologs for E. coli
    GET /genes?organism_id=1&has_ortholog=true

    # Get genes WITHOUT orthologs (orphan genes)
    GET /genes?organism_id=1&has_ortholog=false

    # Get high-confidence orthologs (>70% identity)
    GET /genes?organism_id=1&min_identity=70.0&sort_by=ortholog_identity&order=desc

    # Get genes with human orthologs
    GET /genes?organism_id=1&ortholog_species=Homo sapiens
    ```
    """
    # Start with base query
    query = select(Gene)

    # Apply filters
    if params.organism_id is not None:
        query = query.where(Gene.organism_id == params.organism_id)

    if params.has_ortholog is not None:
        if params.has_ortholog:
            # Has ortholog: ortholog_name is not null
            query = query.where(Gene.ortholog_name.isnot(None))
        else:
            # No ortholog: ortholog_name is null
            query = query.where(Gene.ortholog_name.is_(None))

    if params.min_identity is not None:
        # Filter by minimum identity percentage
        query = query.where(Gene.ortholog_identity >= params.min_identity)

    if params.max_identity is not None:
        # Filter by maximum identity percentage
        query = query.where(Gene.ortholog_identity <= params.max_identity)

    if params.ortholog_species:
        # Case-insensitive partial match on species name
        query = query.where(Gene.ortholog_species.ilike(f"%{params.ortholog_species}%"))

    # Apply sorting
    if params.sort_by:
        # Get the column to sort by
        sort_column = getattr(Gene, params.sort_by)

        # Apply ascending or descending order
        if params.order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset(params.skip).limit(params.limit)

    # Execute query
    result = await db.execute(query)
    genes = result.scalars().all()
    return genes


@router.get("/genes/export")
async def export_genes_filtered(
    params: GeneListParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Export filtered genes to CSV with the same filtering options as the list endpoint.

    **Query Parameters**: Same as GET /genes
    - organism_id: Filter by organism ID
    - has_ortholog: Filter by ortholog presence (true=has, false=no ortholog)
    - min_identity: Minimum ortholog identity percentage (0-100)
    - max_identity: Maximum ortholog identity percentage (0-100)
    - ortholog_species: Filter by ortholog species (case-insensitive partial match)
    - limit: Max records to export (default: 100, max: 1000)

    **Returns**: CSV file download with columns:
    - gene_name, gene_description, ortholog_name, ortholog_description
    - ortholog_species, ortholog_length, ortholog_sw_score, ortholog_identity

    **Examples**:
    ```
    # Export all genes with orthologs for organism 1
    GET /genes/export?organism_id=1&has_ortholog=true

    # Export high-confidence orthologs (>70% identity)
    GET /genes/export?organism_id=1&min_identity=70.0

    # Export genes with human orthologs
    GET /genes/export?organism_id=1&ortholog_species=Homo sapiens
    ```
    """
    return StreamingResponse(
        export_genes_csv(
            db,
            organism_id=params.organism_id,
            has_ortholog=params.has_ortholog,
            min_identity=params.min_identity,
            max_identity=params.max_identity,
            ortholog_species=params.ortholog_species,
            limit=params.limit
        ),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=genes_export.csv"}
    )


@router.post("/genes", response_model=schemas.Gene, status_code=status.HTTP_201_CREATED)
async def create_gene(
    gene_in: schemas.GeneCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new gene."""
    # Check if organism exists
    result = await db.execute(
        select(Organism).where(Organism.id == gene_in.organism_id)
    )
    organism = result.scalar_one_or_none()
    if not organism:
        raise OrganismNotFoundError(organism_id=gene_in.organism_id)

    # Create new gene
    db_gene = Gene(**gene_in.model_dump())
    db.add(db_gene)
    await db.commit()
    await db.refresh(db_gene)
    return db_gene


@router.get("/genes/{gene_id}", response_model=schemas.Gene)
async def get_gene(
    gene_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific gene by ID."""
    result = await db.execute(
        select(Gene).where(Gene.id == gene_id)
    )
    gene = result.scalar_one_or_none()
    if not gene:
        raise GeneNotFoundError(gene_id=gene_id)
    return gene


@router.put("/genes/{gene_id}", response_model=schemas.Gene)
async def update_gene(
    gene_id: int,
    gene_in: schemas.GeneUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a gene."""
    result = await db.execute(
        select(Gene).where(Gene.id == gene_id)
    )
    gene = result.scalar_one_or_none()
    if not gene:
        raise GeneNotFoundError(gene_id=gene_id)

    # Update gene fields
    update_data = gene_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(gene, field, value)

    await db.commit()
    await db.refresh(gene)
    return gene


@router.delete("/genes/{gene_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gene(
    gene_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a gene."""
    result = await db.execute(
        select(Gene).where(Gene.id == gene_id)
    )
    gene = result.scalar_one_or_none()
    if not gene:
        raise GeneNotFoundError(gene_id=gene_id)

    await db.delete(gene)
    await db.commit()
    return None
