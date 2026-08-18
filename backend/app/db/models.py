"""
Database models for ScanTract.
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


class Contract(Base):
    """Contract model."""
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_type = Column(String(50), nullable=False)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    clauses = relationship("Clause", back_populates="contract")
    risk_findings = relationship(
        "RiskFinding",
        back_populates="contract",
        cascade="all, delete-orphan"
    )


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



class RiskFinding(Base):
    """
    Risk finding model for Stage 7 risk detection results.
    
    Stores both risky clauses and missing clauses with mandatory traceability.
    Every finding must have a non-empty triggering_rule_or_corpus field.
    """
    __tablename__ = "risk_findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_type = Column(String(20), nullable=False, index=True)
    
    # For risky clauses
    clause_id = Column(Integer, ForeignKey("clauses.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # For missing clauses
    expected_clause_type = Column(String(100), nullable=True)
    
    # Common fields
    reason = Column(Text, nullable=False)
    triggering_rule_or_corpus = Column(Text, nullable=False)  # MANDATORY - NON-NEGOTIABLE
    severity = Column(String(10), nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), nullable=True)
    
    # Stage 8: Explanation caching fields
    explanation = Column(Text, nullable=True)
    formatted_citation = Column(Text, nullable=True)
    explanation_generated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    contract = relationship("Contract", back_populates="risk_findings")
    clause = relationship("Clause", foreign_keys=[clause_id])
    
    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "finding_type IN ('risky_clause', 'missing_clause')",
            name="valid_finding_type"
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="valid_severity"
        ),
        CheckConstraint(
            "finding_type = 'missing_clause' OR clause_id IS NOT NULL",
            name="risky_clause_has_id"
        ),
        CheckConstraint(
            "finding_type = 'risky_clause' OR expected_clause_type IS NOT NULL",
            name="missing_clause_has_type"
        ),
    )
