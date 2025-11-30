from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models import Gene, Organism
from app.schemas import gene as schemas

router = APIRouter()


@router.get("/genes", response_model=List[schemas.Gene])
async def list_genes(
    organism_id: Optional[int] = Query(None, description="Filter by organism ID"),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all genes, optionally filtered by organism."""
    query = select(Gene)
    if organism_id is not None:
        query = query.where(Gene.organism_id == organism_id)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    genes = result.scalars().all()
    return genes


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organism with id {gene_in.organism_id} not found"
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gene with id {gene_id} not found"
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gene with id {gene_id} not found"
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Gene with id {gene_id} not found"
        )

    await db.delete(gene)
    await db.commit()
    return None
