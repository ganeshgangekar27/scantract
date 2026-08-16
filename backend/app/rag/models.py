"""
Pydantic models for retrieval merge and context assembly (Stage 6).

Contains unified models for combining legal rules (5A) and reference corpus (5B)
results into a single context structure for Stage 7 risk detection.
"""

from pydantic import BaseModel, Field
from typing import Literal


SourceType = Literal["legal_rule", "reference_corpus"]


class ContextChunk(BaseModel):
    """
    Unified context chunk from retrieval merge.
    
    Combines results from Stage 5A (legal rules) and Stage 5B (reference corpus)
    into a single normalized format. Field mappings:
    
    - LegalRuleSearchResult.similarity → ContextChunk.similarity_score
    - LegalRuleSearchResult.rule_text → ContextChunk.text
    - ReferenceClauseSearchResult.similarity → ContextChunk.similarity_score
    - ReferenceClauseSearchResult.clause_text → ContextChunk.text
    
    Note: similarity_score validation (0.0-1.0) is enforced here even though
    ReferenceClauseSearchResult itself lacks this validation, ensuring data
    integrity at the merge layer.
    """
    source_type: SourceType = Field(
        description="Source of this chunk: legal_rule or reference_corpus"
    )
    source_reference: str = Field(
        description="Full citation or label for traceability (e.g., 'Model Tenancy Act 2021, Section 7(1)' or 'Standard practice - fair deposit terms')"
    )
    text: str = Field(
        description="The actual content text (normalized from rule_text or clause_text)"
    )
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Original search similarity score (0.0-1.0), mapped from source's 'similarity' field"
    )
    
    def format_for_prompt(self) -> str:
        """
        Format chunk for inclusion in LLM prompt.
        
        Returns:
            Formatted string with source label and text
        """
        source_label = "Legal Rule" if self.source_type == "legal_rule" else "Reference Example"
        return f"[{source_label}: {self.source_reference}]\n{self.text}"
    
    class Config:
        frozen = True  # Immutable for safety


class MergeResult(BaseModel):
    """
    Result of merge operation with metadata and statistics.
    
    Contains the merged and deduplicated chunks along with stats about
    the merge process (deduplication, token budget trimming).
    """
    chunks: list[ContextChunk] = Field(
        description="Merged and deduplicated context chunks, ordered by similarity descending"
    )
    total_tokens: int = Field(
        description="Total token count of all chunks (after trimming)"
    )
    deduplication_stats: dict[str, int] = Field(
        default_factory=dict,
        description="Deduplication statistics: total_input, duplicates_removed, final_count"
    )
    trimming_stats: dict[str, int] = Field(
        default_factory=dict,
        description="Token budget trimming statistics: before_trim, after_trim, tokens_saved"
    )
