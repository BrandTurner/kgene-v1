from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Organism(Base):
    """
    Organism model representing a biological organism from KEGG.
    One organism has many genes (one-to-many relationship).
    """

    __tablename__ = "organisms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # e.g., "hsa", "eco"
    name = Column(String, nullable=False)  # e.g., "Homo sapiens"
    status = Column(String, nullable=True)  # null, "pending", "complete", "error"
    job_error = Column(String(1000), nullable=True)
    job_id = Column(String, nullable=True)  # ARQ job ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship to genes (one-to-many)
    genes = relationship("Gene", back_populates="organism", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organism(id={self.id}, code={self.code}, name={self.name})>"
