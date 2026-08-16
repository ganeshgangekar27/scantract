"""
Reference corpus models for ScanTract.

SQLAlchemy ORM and Pydantic models for reference contract clauses.
"""

from datetime import datetime
from sqlalchemy import String, Text, Column, Integer
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from pydantic import BaseModel, ConfigDict


Base = declarative_base()


class ReferenceClause(Base):
    """
    Reference clause from model contracts (rental/freelance).
    
    Represents standard/model contract language used for comparison
    against uploaded contract clauses.
    """
    __tablename__ = "reference_clauses"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_type: Mapped[str] = mapped_column(String(50), nullable=False)
    clause_category: Mapped[str] = mapped_column(String(100), nullable=False)
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_label: Mapped[str] = mapped_column(String(200), nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(3072), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    def __repr__(self) -> str:
        return (
            f"<ReferenceClause(id={self.id}, "
            f"contract_type='{self.contract_type}', "
            f"category='{self.clause_category}')>"
        )


class ReferenceClauseData(BaseModel):
    """
    Pydantic model for reference clause seed data (before embedding).
    
    Used for loading and validating seed data from JSON files.
    """
    contract_type: str
    clause_category: str
    clause_text: str
    source_label: str
    
    model_config = ConfigDict(from_attributes=True)


class ReferenceClauseSearchResult(BaseModel):
    """
    Pydantic model for reference clause search results with similarity score.
    
    Used for returning search results from semantic similarity queries.
    """
    id: int
    contract_type: str
    clause_category: str
    clause_text: str
    source_label: str
    similarity: float
    
    model_config = ConfigDict(from_attributes=True)
