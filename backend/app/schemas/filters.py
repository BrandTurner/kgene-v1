"""
Filtering and Sorting Schemas for KEGG Explore API

**What**: Reusable query parameter models for filtering and sorting
**Why**: Provides consistent filtering/sorting across all list endpoints
**How**: Use FastAPI Depends() to inject as query parameters

**Usage Example**:
```python
from app.schemas.filters import OrganismFilters, SortParams

@router.get("/organisms")
async def list_organisms(
    filters: OrganismFilters = Depends(),
    sort: SortParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    query = select(Organism)

    # Apply filters
    if filters.status:
        query = query.where(Organism.status == filters.status)
    if filters.name_pattern:
        query = query.where(Organism.name.ilike(f"%{filters.name_pattern}%"))

    # Apply sorting
    if sort.sort_by:
        order_col = getattr(Organism, sort.sort_by)
        query = query.order_by(order_col.desc() if sort.order == "desc" else order_col)

    result = await db.execute(query.offset(filters.skip).limit(filters.limit))
    return result.scalars().all()
```
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Pagination Parameters
# =============================================================================

class PaginationParams(BaseModel):
    """
    Standard pagination parameters for list endpoints.

    **What**: skip/limit pattern for offset-based pagination
    **Why**: Prevents accidentally loading thousands of records
    **Default**: skip=0, limit=100 (first 100 records)

    **Usage**:
    ```
    GET /organisms?skip=0&limit=50   # First 50 records
    GET /organisms?skip=50&limit=50  # Next 50 records (page 2)
    ```

    **Note**: For very large datasets, cursor-based pagination is better,
    but offset/limit is simpler and sufficient for this use case.
    """

    skip: int = Field(
        0,
        ge=0,
        description="Number of records to skip (offset)",
        examples=[0, 10, 100]
    )
    limit: int = Field(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return (1-1000)",
        examples=[10, 50, 100, 500]
    )


# =============================================================================
# Sort Parameters
# =============================================================================

# Sort order: ascending or descending
SortOrder = Literal["asc", "desc"]


class OrganismSortParams(BaseModel):
    """
    Sorting parameters for organisms.

    **What**: Allows sorting by name, code, created_at, updated_at
    **Why**: Users want to find recently added organisms or sort alphabetically
    **Default**: No sorting (database order, usually by ID)

    **Usage**:
    ```
    GET /organisms?sort_by=name&order=asc    # Alphabetical A-Z
    GET /organisms?sort_by=name&order=desc   # Alphabetical Z-A
    GET /organisms?sort_by=created_at&order=desc  # Newest first
    ```
    """

    sort_by: Optional[Literal["name", "code", "created_at", "updated_at"]] = Field(
        None,
        description="Field to sort by"
    )
    order: SortOrder = Field(
        "asc",
        description="Sort order: asc (ascending) or desc (descending)"
    )


class GeneSortParams(BaseModel):
    """
    Sorting parameters for genes.

    **What**: Allows sorting by name, identity, sw_score, etc.
    **Why**: Users want to find best orthologs (highest identity) or sort genes
    **Default**: No sorting (database order)

    **Bioinformatics Use Cases**:
    - sort_by=ortholog_identity&order=desc → Best matches first
    - sort_by=name&order=asc → Alphabetical gene list
    """

    sort_by: Optional[Literal["name", "ortholog_identity", "ortholog_sw_score", "created_at"]] = Field(
        None,
        description="Field to sort by"
    )
    order: SortOrder = Field(
        "asc",
        description="Sort order: asc or desc"
    )


# =============================================================================
# Organism Filters
# =============================================================================

class OrganismFilters(PaginationParams):
    """
    Filtering parameters for organisms.

    **What**: Filter organisms by status, name pattern, date range
    **Why**: Users want to find specific organisms or filter by processing status
    **Inherits**: skip, limit from PaginationParams

    **Usage Examples**:
    ```
    # Get completed organisms
    GET /organisms?status=complete

    # Search by name (case-insensitive)
    GET /organisms?name_pattern=coli

    # Get organisms created after a date
    GET /organisms?created_after=2024-01-01T00:00:00Z

    # Combine filters
    GET /organisms?status=complete&name_pattern=human&limit=50
    ```
    """

    status: Optional[Literal["pending", "complete", "error"]] = Field(
        None,
        description="Filter by processing status"
    )

    code_pattern: Optional[str] = Field(
        None,
        min_length=1,
        max_length=10,
        description="Filter by organism code (case-insensitive partial match)",
        examples=["eco", "hsa", "mm"]
    )

    name_pattern: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Filter by organism name (case-insensitive partial match)",
        examples=["coli", "human", "mouse"]
    )

    created_after: Optional[datetime] = Field(
        None,
        description="Filter organisms created after this timestamp (ISO 8601)",
        examples=["2024-01-01T00:00:00Z", "2024-12-01T10:30:00Z"]
    )

    created_before: Optional[datetime] = Field(
        None,
        description="Filter organisms created before this timestamp (ISO 8601)",
        examples=["2024-12-31T23:59:59Z"]
    )


# =============================================================================
# Gene Filters
# =============================================================================

class GeneFilters(PaginationParams):
    """
    Filtering parameters for genes.

    **What**: Filter genes by organism, ortholog presence, identity range
    **Why**: Core bioinformatics queries - find genes with/without orthologs
    **Inherits**: skip, limit from PaginationParams

    **Bioinformatics Use Cases**:
    ```
    # Get all genes for E. coli
    GET /genes?organism_id=1

    # Get genes WITH orthologs found
    GET /genes?organism_id=1&has_ortholog=true

    # Get genes WITHOUT orthologs (orphan genes)
    GET /genes?organism_id=1&has_ortholog=false

    # Get high-confidence orthologs (>70% identity)
    GET /genes?organism_id=1&min_identity=70.0

    # Get genes with identity in specific range
    GET /genes?organism_id=1&min_identity=40.0&max_identity=60.0
    ```

    **Identity Ranges**:
    - 100%: Identical sequences
    - 70-100%: High confidence orthologs
    - 40-70%: Moderate confidence
    - <40%: Low confidence (may not be true orthologs)
    """

    organism_id: Optional[int] = Field(
        None,
        gt=0,
        description="Filter by organism ID"
    )

    has_ortholog: Optional[bool] = Field(
        None,
        description="Filter by ortholog presence (true=has ortholog, false=no ortholog)"
    )

    min_identity: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Minimum ortholog identity percentage (0-100)",
        examples=[40.0, 50.0, 70.0]
    )

    max_identity: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Maximum ortholog identity percentage (0-100)",
        examples=[60.0, 80.0, 100.0]
    )

    ortholog_species: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Filter by ortholog species name (case-insensitive partial match)",
        examples=["Homo sapiens", "Mus musculus", "coli"]
    )


# =============================================================================
# Combined Filter Classes (with sorting)
# =============================================================================

class OrganismListParams(OrganismFilters):
    """
    Complete parameters for listing organisms (filters + sorting).

    **What**: Combines filtering and sorting in one model
    **Why**: Single Depends() injection for all query params
    **Inherits**: OrganismFilters (which inherits PaginationParams)

    **Usage**:
    ```python
    @router.get("/organisms")
    async def list_organisms(
        params: OrganismListParams = Depends(),
        db: AsyncSession = Depends(get_db)
    ):
        # params has: skip, limit, status, name_pattern, sort_by, order
    ```
    """

    sort_by: Optional[Literal["name", "code", "created_at", "updated_at"]] = Field(
        None,
        description="Field to sort by"
    )
    order: SortOrder = Field(
        "asc",
        description="Sort order: asc or desc"
    )


class GeneListParams(GeneFilters):
    """
    Complete parameters for listing genes (filters + sorting).

    **What**: Combines filtering and sorting in one model
    **Why**: Single Depends() injection for all query params
    **Inherits**: GeneFilters (which inherits PaginationParams)
    """

    sort_by: Optional[Literal["name", "ortholog_identity", "ortholog_sw_score", "created_at"]] = Field(
        None,
        description="Field to sort by"
    )
    order: SortOrder = Field(
        "asc",
        description="Sort order: asc or desc"
    )


# =============================================================================
# Validation
# =============================================================================

# Note: Pydantic automatically validates that min_identity <= max_identity
# is not enforced here, but we could add a @model_validator if needed:
#
# @model_validator(mode='after')
# def validate_identity_range(self) -> 'GeneFilters':
#     if self.min_identity and self.max_identity:
#         if self.min_identity > self.max_identity:
#             raise ValueError("min_identity cannot be greater than max_identity")
#     return self


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PaginationParams',
    'SortOrder',
    'OrganismSortParams',
    'GeneSortParams',
    'OrganismFilters',
    'GeneFilters',
    'OrganismListParams',
    'GeneListParams',
]
