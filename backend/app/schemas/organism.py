from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class OrganismBase(BaseModel):
    """Base schema for Organism."""

    code: str = Field(..., description="KEGG organism code (e.g., 'hsa', 'eco')")
    name: str = Field(..., description="Organism name (e.g., 'Homo sapiens')")


class OrganismCreate(OrganismBase):
    """Schema for creating a new organism."""

    pass


class OrganismUpdate(BaseModel):
    """Schema for updating an organism."""

    code: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    job_error: Optional[str] = None
    job_id: Optional[str] = None


class Organism(OrganismBase):
    """Schema for organism response."""

    id: int
    status: Optional[str] = None
    job_error: Optional[str] = None
    job_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)


class OrganismWithProgress(Organism):
    """Organism schema with gene processing progress and statistics."""

    total_genes: int = 0
    genes_with_orthologs: int = 0
    coverage_percent: Optional[float] = None  # Percentage of genes with orthologs found
