"""
Data models for LLM clause classification.

Defines the clause type taxonomy, classification results, and validation logic.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal
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
