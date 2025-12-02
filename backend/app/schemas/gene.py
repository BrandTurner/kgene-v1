from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class GeneBase(BaseModel):
    """
    Base schema for Gene.

    **What**: Core gene fields (organism, name, description)
    **Note**: Ortholog fields are separate (added during processing)
    """

    organism_id: int = Field(..., description="Foreign key to organism table", gt=0)
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Gene name from KEGG (e.g., 'hsa:10458', 'eco:b0001')",
        examples=["hsa:10458", "eco:b0001", "mmu:12345"]
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Gene description/function from KEGG",
        examples=["ATP synthase subunit alpha", "DNA polymerase III subunit beta"]
    )


class GeneCreate(GeneBase):
    """Schema for creating a new gene."""

    pass


class GeneUpdate(BaseModel):
    """
    Schema for updating a gene (mainly for ortholog data).

    **What**: Allows updating gene fields after creation
    **Primary use**: Background worker updates ortholog fields after finding matches
    **Validation**: Ensures ortholog scores are in valid ranges
    """

    description: Optional[str] = Field(None, max_length=500)
    ortholog_name: Optional[str] = Field(None, max_length=100)
    ortholog_description: Optional[str] = Field(None, max_length=500)
    ortholog_species: Optional[str] = Field(None, max_length=200)
    ortholog_length: Optional[int] = Field(None, ge=0, description="Ortholog sequence length (>= 0)")
    ortholog_sw_score: Optional[int] = Field(None, ge=0, description="Smith-Waterman alignment score (>= 0)")
    ortholog_identity: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Sequence identity percentage (0-100)"
    )

    @field_validator('ortholog_identity')
    @classmethod
    def validate_ortholog_identity(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate ortholog identity is in valid range.

        **What**: Ensures identity percentage is 0-100
        **Why**: Identity can't be negative or > 100%
        **Examples**:
        - Valid: 45.5, 0.0, 100.0
        - Invalid: -10, 105.5, 999

        **Note**: Pydantic ge/le already validates this, but we add helpful error
        """
        if v is not None and (v < 0.0 or v > 100.0):
            raise ValueError(
                f"Ortholog identity must be between 0.0 and 100.0 percent. Got: {v}"
            )
        return v


class Gene(GeneBase):
    """
    Schema for gene response.

    **What**: Full gene data including ortholog information
    **When**: GET /genes, GET /genes/{id}
    **Ortholog fields**: Populated by background worker after processing
    """

    id: int = Field(..., description="Database primary key", gt=0)

    # Ortholog fields (null if no ortholog found)
    ortholog_name: Optional[str] = Field(None, max_length=100, description="Best ortholog gene name")
    ortholog_description: Optional[str] = Field(None, max_length=500, description="Ortholog function/description")
    ortholog_species: Optional[str] = Field(None, max_length=200, description="Ortholog organism name")
    ortholog_length: Optional[int] = Field(None, ge=0, description="Ortholog sequence length")
    ortholog_sw_score: Optional[int] = Field(None, ge=0, description="Smith-Waterman alignment score")
    ortholog_identity: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Sequence identity percentage (0-100)"
    )

    created_at: datetime = Field(..., description="When gene was created")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
