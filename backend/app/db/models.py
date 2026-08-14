"""
Database models for ScanTract.
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Contract(Base):
    """Contract model."""
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_type = Column(String(50), nullable=False)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationship to clauses
    clauses = relationship("Clause", back_populates="contract")


class Clause(Base):
    """Clause model with classification fields."""
    __tablename__ = "clauses"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    clause_id = Column(String(50), nullable=False)
    position = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    
    # Classification fields (Stage 4)
    clause_type = Column(String(50), nullable=True, index=True)
    key_entities = Column(JSONB, nullable=True)
    confidence = Column(Float, nullable=True, index=True)
    classification_error = Column(Text, nullable=True)
    classified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship to contract
    contract = relationship("Contract", back_populates="clauses")
