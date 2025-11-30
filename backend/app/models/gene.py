from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Gene(Base):
    """
    Gene model representing a gene from KEGG database.
    Each gene belongs to one organism (many-to-one relationship).
    """

    __tablename__ = "genes"

    id = Column(Integer, primary_key=True, index=True)
    organism_id = Column(Integer, ForeignKey("organisms.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False, index=True)  # e.g., "hsa:10458"
    description = Column(String(1000), nullable=True)

    # Ortholog information
    ortholog_name = Column(String, nullable=True)
    ortholog_description = Column(String(1000), nullable=True)
    ortholog_species = Column(String(1000), nullable=True)
    ortholog_length = Column(Integer, nullable=True)
    ortholog_sw_score = Column(Integer, nullable=True)
    ortholog_identity = Column(Float, nullable=True)  # 0.0-100.0

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship to organism (many-to-one)
    organism = relationship("Organism", back_populates="genes")

    # Composite index for queries
    __table_args__ = (
        Index("idx_organism_ortholog", "organism_id", "ortholog_name"),
    )

    def __repr__(self):
        return f"<Gene(id={self.id}, name={self.name}, organism_id={self.organism_id})>"
