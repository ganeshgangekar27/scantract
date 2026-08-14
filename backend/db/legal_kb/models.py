"""
SQLAlchemy and Pydantic models for Legal Knowledge Base.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field
from typing import Optional

Base = declarative_base()


class LegalRule(Base):
    """
    SQLAlchemy model for legal rules with pgvector embeddings.
    
    Represents Indian legal provisions (central and state-specific) with
    semantic embeddings for similarity search.
    """
    __tablename__ = "legal_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(50), nullable=True, index=True)
    act_name = Column(String(255), nullable=False, index=True)
    section_reference = Column(String(100), nullable=False)
    rule_text = Column(Text, nullable=False)
    embedding = Column(Vector(3072), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default="NOW()")
    updated_at = Column(DateTime(timezone=True), server_default="NOW()", onupdate="NOW()")
    
    __table_args__ = (
        UniqueConstraint('act_name', 'section_reference', 'state', name='uq_legal_rule'),
    )


class LegalRuleData(BaseModel):
    """
    Pydantic model for loading legal rules (without embedding).
    
    Used for seed data loading and validation before embedding generation.
    """
    state: Optional[str] = Field(
        None,
        max_length=50,
        description="State code (e.g., MH, KA, DL, TN) or None for central laws"
    )
    act_name: str = Field(
        ...,
        max_length=255,
        description="Name of the act/statute (e.g., Model Tenancy Act 2021)"
    )
    section_reference: str = Field(
        ...,
        max_length=100,
        description="Section or clause reference (e.g., Section 7(1))"
    )
    rule_text: str = Field(
        ...,
        min_length=10,
        description="Full text of the legal rule with context"
    )


class LegalRuleSearchResult(BaseModel):
    """
    Pydantic model for search results with similarity scores.
    
    Returned by search_legal_rules() with cosine similarity score.
    """
    id: int
    state: Optional[str]
    act_name: str
    section_reference: str
    rule_text: str
    similarity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cosine similarity score (0.0 = dissimilar, 1.0 = identical)"
    )
    
    class Config:
        from_attributes = True

