from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.exceptions import DuplicateOrganismError, OrganismNotFoundError
from app.database import get_db
from app.models import Organism
from app.schemas import organism as schemas
from app.schemas.filters import OrganismListParams

router = APIRouter()


@router.get("/organisms", response_model=List[schemas.Organism])
async def list_organisms(
    params: OrganismListParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    List all organisms with optional filtering and sorting.

    **Query Parameters**:
    - status: Filter by processing status (pending/complete/error)
    - code_pattern: Filter by organism code (case-insensitive partial match)
    - name_pattern: Filter by organism name (case-insensitive partial match)
    - created_after: Filter organisms created after timestamp
    - created_before: Filter organisms created before timestamp
    - sort_by: Field to sort by (name/code/created_at/updated_at)
    - order: Sort order (asc/desc)
    - skip: Pagination offset (default: 0)
    - limit: Max records to return (default: 100, max: 1000)

    **Examples**:
    ```
    # Get completed organisms sorted by name
    GET /organisms?status=complete&sort_by=name&order=asc

    # Search for organisms with "coli" in name
    GET /organisms?name_pattern=coli

    # Get organisms created in December 2024
    GET /organisms?created_after=2024-12-01T00:00:00Z&created_before=2024-12-31T23:59:59Z
    ```
    """
    # Start with base query
    query = select(Organism)

    # Apply filters
    if params.status is not None:
        query = query.where(Organism.status == params.status)

    if params.code_pattern:
        # Case-insensitive partial match (LIKE in SQL)
        query = query.where(Organism.code.ilike(f"%{params.code_pattern}%"))

    if params.name_pattern:
        # Case-insensitive partial match
        query = query.where(Organism.name.ilike(f"%{params.name_pattern}%"))

    if params.created_after:
        query = query.where(Organism.created_at >= params.created_after)

    if params.created_before:
        query = query.where(Organism.created_at <= params.created_before)

    # Apply sorting
    if params.sort_by:
        # Get the column to sort by
        sort_column = getattr(Organism, params.sort_by)

        # Apply ascending or descending order
        if params.order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset(params.skip).limit(params.limit)

    # Execute query
    result = await db.execute(query)
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
        raise DuplicateOrganismError(code=organism_in.code)

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
        raise OrganismNotFoundError(organism_id=organism_id)
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
        raise OrganismNotFoundError(organism_id=organism_id)

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
        raise OrganismNotFoundError(organism_id=organism_id)

    await db.delete(organism)
    await db.commit()
    return None
