from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import Organism
from app.schemas import organism as schemas

router = APIRouter()


@router.get("/organisms", response_model=List[schemas.Organism])
async def list_organisms(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all organisms."""
    result = await db.execute(
        select(Organism).offset(skip).limit(limit)
    )
    organisms = result.scalars().all()
    return organisms


@router.post("/organisms", response_model=schemas.Organism, status_code=status.HTTP_201_CREATED)
async def create_organism(
    organism_in: schemas.OrganismCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new organism."""
    # Check if organism code already exists
    result = await db.execute(
        select(Organism).where(Organism.code == organism_in.code)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organism with code '{organism_in.code}' already exists"
        )

    # Create new organism
    db_organism = Organism(**organism_in.model_dump())
    db.add(db_organism)
    await db.commit()
    await db.refresh(db_organism)
    return db_organism


@router.get("/organisms/{organism_id}", response_model=schemas.Organism)
async def get_organism(
    organism_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific organism by ID."""
    result = await db.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    organism = result.scalar_one_or_none()
    if not organism:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organism with id {organism_id} not found"
        )
    return organism


@router.put("/organisms/{organism_id}", response_model=schemas.Organism)
async def update_organism(
    organism_id: int,
    organism_in: schemas.OrganismUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an organism."""
    result = await db.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    organism = result.scalar_one_or_none()
    if not organism:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organism with id {organism_id} not found"
        )

    # Update organism fields
    update_data = organism_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organism, field, value)

    await db.commit()
    await db.refresh(organism)
    return organism


@router.delete("/organisms/{organism_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organism(
    organism_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an organism and all its genes (cascade)."""
    result = await db.execute(
        select(Organism).where(Organism.id == organism_id)
    )
    organism = result.scalar_one_or_none()
    if not organism:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organism with id {organism_id} not found"
        )

    await db.delete(organism)
    await db.commit()
    return None
