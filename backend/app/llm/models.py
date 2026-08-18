"""
Data models for LLM clause classification and risk detection.

Defines the clause type taxonomy, classification results, risk detection models,
and validation logic.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Clause type taxonomy - exactly 12 types
ClauseType = Literal[
    "payment_terms",
    "termination",
    "liability",
    "confidentiality",
    "intellectual_property",
    "dispute_resolution",
    "term_duration",
    "renewal",
    "indemnification",
    "warranties",
    "force_majeure",
    "other"
]


class ClauseClassification(BaseModel):
    """
    Classification result for a single clause.
    
    Attributes:
        clause_type: Type from the 12-item taxonomy
        key_entities: List of entities mentioned (max 20)
        confidence: Confidence score between 0.0 and 1.0
        reasoning: Explanation of classification decision
    """
    clause_type: ClauseType
    key_entities: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    
    @field_validator("key_entities")
    @classmethod
    def cap_key_entities(cls, v: list[str]) -> list[str]:
        """Cap key_entities at 20 items, log warning if truncated."""
        if len(v) > 20:
            logger.warning(
                f"key_entities list contains {len(v)} items, truncating to 20"
            )
            return v[:20]
        return v


class ClassificationResult(BaseModel):
    """
    Result of classifying a single clause, including success or error state.
    
    Attributes:
        clause_index: Identifier of the clause (e.g., "1.1", "para_5")
        classification: Successful classification result, or None if error
        error: Error message if classification failed, or None if success
        tokens_used: Number of tokens consumed by LLM call
    """
    clause_index: str
    classification: ClauseClassification | None = None
    error: str | None = None
    tokens_used: int = 0


# ============================================================================
# Risk Detection Models
# ============================================================================

class Severity(str, Enum):
    """Severity level for risk findings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskyClauseFinding(BaseModel):
    """
    Represents a risky clause detected in the contract.
    
    Attributes:
        clause_id: Identifier of the clause (e.g., "1.1", "para_5")
        reason: Explanation of why this clause is risky (min 10 chars)
        triggering_rule_or_corpus: MANDATORY citation from legal KB or reference corpus
        severity: Risk severity level (low, medium, high)
    """
    clause_id: str
    reason: str = Field(min_length=10)
    triggering_rule_or_corpus: str = Field(min_length=1)
    severity: Severity
    
    @field_validator("triggering_rule_or_corpus")
    @classmethod
    def validate_traceability(cls, v: str) -> str:
        """
        Validate that triggering_rule_or_corpus is non-empty and not whitespace-only.
        This is a NON-NEGOTIABLE requirement for traceability.
        """
        if not v or not v.strip():
            raise ValueError(
                "triggering_rule_or_corpus cannot be empty or whitespace-only. "
                "Every risky clause finding MUST be traceable to a specific legal rule "
                "or reference example."
            )
        return v.strip()


class MissingClauseFinding(BaseModel):
    """
    Represents a missing clause that should be present in the contract.
    
    Attributes:
        expected_clause_type: Type of clause that is missing
        why_expected: Explanation of why this clause should be present (min 10 chars)
        triggering_rule_or_corpus: MANDATORY citation from legal KB or reference corpus
        severity: Risk severity level (low, medium, high)
    """
    expected_clause_type: str
    why_expected: str = Field(min_length=10)
    triggering_rule_or_corpus: str = Field(min_length=1)
    severity: Severity
    
    @field_validator("triggering_rule_or_corpus")
    @classmethod
    def validate_traceability(cls, v: str) -> str:
        """
        Validate that triggering_rule_or_corpus is non-empty and not whitespace-only.
        This is a NON-NEGOTIABLE requirement for traceability.
        """
        if not v or not v.strip():
            raise ValueError(
                "triggering_rule_or_corpus cannot be empty or whitespace-only. "
                "Every missing clause finding MUST be traceable to a specific legal rule "
                "or reference example."
            )
        return v.strip()


class RiskDetectionResponse(BaseModel):
    """
    Response from LLM containing detected risks and missing clauses.
    
    Attributes:
        risky_clauses: List of risky clauses found in the contract
        missing_clauses: List of clauses that should be present but are missing
    """
    risky_clauses: list[RiskyClauseFinding] = Field(default_factory=list)
    missing_clauses: list[MissingClauseFinding] = Field(default_factory=list)


class RiskDetectionResult(BaseModel):
    """
    Complete result of risk detection analysis for a contract.
    
    Attributes:
        contract_id: UUID of the analyzed contract
        risky_clauses: List of risky clauses found
        missing_clauses: List of missing clauses identified
        total_risks: Total number of risky clauses
        total_missing: Total number of missing clauses
        high_severity_count: Number of high-severity findings
        medium_severity_count: Number of medium-severity findings
        low_severity_count: Number of low-severity findings
        processed_at: ISO timestamp of when analysis was performed
    """
    contract_id: str
    risky_clauses: list[RiskyClauseFinding]
    missing_clauses: list[MissingClauseFinding]
    total_risks: int
    total_missing: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    processed_at: str
    
    def summary(self) -> str:
        """Generate human-readable summary of risk detection results."""
        return (
            f"Risk Detection Summary for Contract {self.contract_id}:\n"
            f"  - Total Risky Clauses: {self.total_risks}\n"
            f"  - Total Missing Clauses: {self.total_missing}\n"
            f"  - Severity Breakdown:\n"
            f"    * High: {self.high_severity_count}\n"
            f"    * Medium: {self.medium_severity_count}\n"
            f"    * Low: {self.low_severity_count}\n"
            f"  - Processed At: {self.processed_at}"
        )


# ============================================================================
# Explanation Generation Models (Stage 8)
# ============================================================================

class ExplanationResponse(BaseModel):
    """
    Base model for a single finding with explanation and citation.
    
    Attributes:
        finding_id: UUID of the risk finding
        finding_type: Type of finding (risky_clause or missing_clause)
        clause_id: ID of the clause (INTEGER, for risky clauses only)
        expected_clause_type: Type of expected clause (for missing clauses only)
        reason: Reason for the finding
        severity: Severity level (low, medium, high)
        explanation: Plain-language explanation (2-4 sentences)
        formatted_citation: Formatted citation from traced reference
    """
    finding_id: str
    finding_type: Literal["risky_clause", "missing_clause"]
    clause_id: int | None = None
    expected_clause_type: str | None = None
    reason: str
    severity: str
    explanation: str = Field(
        description="Plain-language explanation (2-4 sentences)"
    )
    formatted_citation: str = Field(
        description="Formatted legal citation from traced reference"
    )


class RiskyClauseExplanation(ExplanationResponse):
    """
    Risky clause with explanation and clause details.
    
    Attributes:
        finding_type: Always "risky_clause"
        clause_id: ID of the risky clause (INTEGER, required)
        clause_text: Full text of the clause
        clause_number: Clause identifier (e.g., "1.1", "para_5")
    """
    finding_type: Literal["risky_clause"] = "risky_clause"
    clause_id: int
    clause_text: str
    clause_number: str


class MissingClauseExplanation(ExplanationResponse):
    """
    Missing clause with explanation.
    
    Attributes:
        finding_type: Always "missing_clause"
        expected_clause_type: Type of clause that should be present (required)
    """
    finding_type: Literal["missing_clause"] = "missing_clause"
    expected_clause_type: str


class ContractExplanationsResponse(BaseModel):
    """
    Complete explanation response for a contract with all findings.
    
    Attributes:
        contract_id: ID of the contract (INTEGER)
        risky_clauses: List of risky clause explanations
        missing_clauses: List of missing clause explanations
        summary: Summary counts (total_risks, total_missing, severity breakdown)
    """
    contract_id: int
    risky_clauses: list[RiskyClauseExplanation]
    missing_clauses: list[MissingClauseExplanation]
    summary: dict[str, int] = Field(
        description="Counts: total_risks, total_missing, high_severity, medium_severity, low_severity"
    )
