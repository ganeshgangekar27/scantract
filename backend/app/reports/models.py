"""
Pydantic models for contract risk reports.

These models define the structure of assembled contract reports,
including risk findings, clauses, and legal references.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ClauseWithRisk(BaseModel):
    """
    Clause annotated with risk information.
    
    Represents a single contract clause with flags indicating
    whether it has associated risk findings.
    """
    clause_id: int  # INTEGER, not UUID
    clause_number: str  # e.g., "4.2"
    clause_text: str
    has_risk: bool
    risk_severity: Optional[str] = None  # None if no risk, else "high"/"medium"/"low"
    risk_reason: Optional[str] = None


class RiskyClauseReport(BaseModel):
    """
    Report entry for a risky clause finding.
    
    Includes the clause details, risk assessment, and cached
    explanation/citation from Stage 8.
    """
    finding_id: str  # UUID as string
    clause_id: int  # INTEGER
    clause_number: str
    clause_text: str
    severity: str  # "high"/"medium"/"low"
    reason: str
    explanation: str  # From Stage 8 cached value
    formatted_citation: str  # From Stage 8 cached value


class MissingClauseReport(BaseModel):
    """
    Report entry for a missing clause finding.
    
    Identifies expected clauses that are absent from the contract.
    """
    finding_id: str  # UUID as string
    expected_clause_type: str
    severity: str  # "high"/"medium"/"low"
    reason: str
    explanation: str  # From Stage 8 cached value
    formatted_citation: str  # From Stage 8 cached value


class RiskSummary(BaseModel):
    """
    Aggregate risk statistics for a contract.
    
    Provides high-level counts and overall risk level assessment.
    """
    total_clauses: int
    risky_clauses_count: int
    missing_clauses_count: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    overall_risk_level: str  # "high"/"medium"/"low"/"none"
    
    # Computed: "high" if any high-severity findings,
    # "medium" if any medium (but no high),
    # "low" if any low (but no high/medium),
    # "none" otherwise


class LegalReference(BaseModel):
    """
    Legal citation with usage tracking.
    
    Represents a unique legal reference and how many findings cite it.
    """
    citation: str  # Formatted citation from Stage 8
    usage_count: int  # How many findings reference this citation


class ContractReport(BaseModel):
    """
    Complete contract risk report.
    
    Assembles all contract data, risk findings, explanations,
    and legal references into a single comprehensive report.
    """
    contract_id: int  # INTEGER
    filename: str
    upload_date: datetime
    all_clauses: List[ClauseWithRisk]  # Ordered by clause_number
    risky_clauses: List[RiskyClauseReport]  # Ordered by severity desc, then clause_number
    missing_clauses: List[MissingClauseReport]  # Ordered by severity desc
    risk_summary: RiskSummary
    legal_references: List[LegalReference]  # Ordered by usage_count desc, then alphabetically
