from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class GeneBase(BaseModel):
    """Base schema for Gene."""

    organism_id: int
    name: str = Field(..., description="Gene name (e.g., 'hsa:10458')")
    description: Optional[str] = None


class GeneCreate(GeneBase):
    """Schema for creating a new gene."""

    pass


class GeneUpdate(BaseModel):
    """Schema for updating a gene (mainly for ortholog data)."""

    description: Optional[str] = None
    ortholog_name: Optional[str] = None
    ortholog_description: Optional[str] = None
    ortholog_species: Optional[str] = None
    ortholog_length: Optional[int] = None
    ortholog_sw_score: Optional[int] = None
    ortholog_identity: Optional[float] = None


class Gene(GeneBase):
    """Schema for gene response."""

    id: int
    ortholog_name: Optional[str] = None
    ortholog_description: Optional[str] = None
    ortholog_species: Optional[str] = None
    ortholog_length: Optional[int] = None
    ortholog_sw_score: Optional[int] = None
    ortholog_identity: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
