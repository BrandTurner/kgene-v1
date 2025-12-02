from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Literal
import re


# =============================================================================
# Type Definitions
# =============================================================================

# Valid organism status values
# **What**: Enum for organism.status field
# **Why**: Prevents invalid status values like "running", "failed", "done"
# **Valid values**:
# - null: Never processed
# - "pending": Job queued or in progress
# - "complete": Processing finished successfully
# - "error": Processing failed
StatusType = Optional[Literal["pending", "complete", "error"]]


# =============================================================================
# Schema Classes
# =============================================================================

class OrganismBase(BaseModel):
    """Base schema for Organism."""

    code: str = Field(
        ...,
        min_length=3,
        max_length=4,
        description="KEGG organism code (3-4 lowercase letters, e.g., 'hsa', 'eco')",
        examples=["eco", "hsa", "mmu", "sce"]
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Organism name (e.g., 'Homo sapiens', 'Escherichia coli')",
        examples=["Homo sapiens", "Escherichia coli", "Mus musculus"]
    )

    @field_validator('code')
    @classmethod
    def validate_organism_code(cls, v: str) -> str:
        """
        Validate organism code follows KEGG format.

        **What**: Ensures code is 3-4 lowercase letters
        **Why**: KEGG uses strict organism code format (e.g., "eco", "hsa")
        **Examples**:
        - Valid: "eco", "hsa", "mmu", "sce"
        - Invalid: "ECO" (uppercase), "e.coli" (punctuation), "12" (numbers)

        **Raises**:
        - ValueError: If code doesn't match format
        """
        # Check if code matches KEGG format: 3-4 lowercase letters
        if not re.match(r'^[a-z]{3,4}$', v):
            raise ValueError(
                f"Organism code must be 3-4 lowercase letters (e.g., 'eco', 'hsa'). Got: '{v}'"
            )
        return v


class OrganismCreate(OrganismBase):
    """Schema for creating a new organism."""

    pass


class OrganismUpdate(BaseModel):
    """
    Schema for updating an organism.

    **What**: Allows partial updates to organism fields
    **Why**: PUT endpoint should allow updating status, job info, etc.
    **Note**: code and name should rarely be updated (usually set at creation)
    """

    code: Optional[str] = Field(
        None,
        min_length=3,
        max_length=4,
        description="KEGG organism code",
        pattern=r'^[a-z]{3,4}$'  # Pydantic v2 pattern validation
    )
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: StatusType = None
    job_error: Optional[str] = Field(None, max_length=1000)
    job_id: Optional[str] = Field(None, max_length=100)

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate status is one of the allowed values.

        **What**: Ensures status is "pending", "complete", "error", or null
        **Why**: Prevents typos like "completed", "processing", "failed"
        **Note**: Pydantic Literal already validates this, but we add helpful error message
        """
        if v is not None and v not in ("pending", "complete", "error"):
            raise ValueError(
                f"Status must be 'pending', 'complete', 'error', or null. Got: '{v}'"
            )
        return v


class Organism(OrganismBase):
    """
    Schema for organism response.

    **What**: Full organism data returned by API
    **When**: GET /organisms, GET /organisms/{id}, POST /organisms
    **Fields**: All organism fields including status and timestamps
    """

    id: int = Field(..., description="Database primary key", gt=0)
    status: StatusType = Field(None, description="Processing status (pending/complete/error)")
    job_error: Optional[str] = Field(None, max_length=1000, description="Error message if status is 'error'")
    job_id: Optional[str] = Field(None, max_length=100, description="ARQ job ID for tracking")
    created_at: datetime = Field(..., description="When organism was created")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)


class OrganismWithProgress(Organism):
    """Organism schema with gene processing progress and statistics."""

    total_genes: int = 0
    genes_with_orthologs: int = 0
    coverage_percent: Optional[float] = None  # Percentage of genes with orthologs found
