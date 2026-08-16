"""
Unit tests for Stage 6: Retrieval Merge & Context Assembly.

Tests TC-1 through TC-15: merge logic, deduplication, token budget,
source tagging, and formatting.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.rag.merge_context import (
    merge_retrieval_results,
    format_merged_context,
    _convert_to_chunks,
    _deduplicate_chunks,
    _compute_text_similarity,
    _trim_to_budget,
)
from app.rag.models import ContextChunk, MergeResult
from tests.fixtures.merge_test_data import (
    get_unique_legal_results,
    get_unique_corpus_results,
    get_exact_duplicate_legal_results,
    get_near_duplicate_results,
    get_below_threshold_results,
    get_equal_score_results,
    get_many_legal_results,
    get_many_corpus_results,
    get_large_chunk_legal,
    get_large_chunk_corpus,
    get_multiple_duplicate_results,
    get_unsorted_results,
)


# TC-1: Basic Merge - No Duplicates
def test_basic_merge_no_duplicates():
    """
    TC-1: Verify basic merge with unique chunks from both sources.
    """
    legal_results = get_unique_legal_results()  # 3 legal rules
    corpus_results = get_unique_corpus_results()  # 3 corpus results
    
    result = merge_retrieval_results(legal_results, corpus_results)
    
    # Should have all 6 chunks
    assert len(result.chunks) == 6
    
    # Verify source types
    legal_chunks = [c for c in result.chunks if c.source_type == "legal_rule"]
    corpus_chunks = [c for c in result.chunks if c.source_type == "reference_corpus"]
    assert len(legal_chunks) == 3
    assert len(corpus_chunks) == 3
    
    # Verify legal chunks have correctly formatted source_reference
    for i, chunk in enumerate(legal_chunks):
        legal_result = legal_results[i]
        expected_ref = f"{legal_result.act_name}, {legal_result.section_reference}"
        if legal_result.state:
            expected_ref += f" ({legal_result.state})"
        assert chunk.source_reference == expected_ref
    
    # Verify corpus chunks use source_label
    for i, chunk in enumerate(corpus_chunks):
        assert chunk.source_reference == corpus_results[i].source_label
    
    # Verify chunks sorted by similarity_score descending
    for i in range(len(result.chunks) - 1):
        assert result.chunks[i].similarity_score >= result.chunks[i + 1].similarity_score


# TC-2: Exact Duplicates - Same Text
def test_exact_duplicates_same_text():
    """
    TC-2: Test deduplication of exact duplicate text with different scores.
    """
    legal_results = get_exact_duplicate_legal_results()  # 2 with same text
    corpus_results = []
    
    result = merge_retrieval_results(legal_results, corpus_results)
    
    # Should keep only 1 chunk (higher score)
    assert len(result.chunks) == 1
    assert result.chunks[0].similarity_score == 0.90  # Higher score kept
    
    # Verify deduplication stats
    assert result.deduplication_stats["total_input"] == 2
    assert result.deduplication_stats["duplicates_removed"] == 1
    assert result.deduplication_stats["final_count"] == 1


# TC-3: Near Duplicates - Above Threshold
def test_near_duplicates_above_threshold():
    """
    TC-3: Test deduplication of near-duplicates (96% similarity, above 0.95 threshold).
    """
    results = get_near_duplicate_results()  # Legal + corpus with same text
    legal_results = [r for r in results if hasattr(r, 'rule_text')]
    corpus_results = [r for r in results if hasattr(r, 'clause_text')]
    
    result = merge_retrieval_results(legal_results, corpus_results)
    
    # Should keep only 1 chunk (higher score)
    assert len(result.chunks) == 1
    assert result.chunks[0].similarity_score == 0.91  # Legal rule has higher score


# TC-4: Priority When Scores Equal
def test_priority_when_scores_equal():
    """
    TC-4: Test that legal rule is prioritized over corpus when scores are equal.
    """
    results = get_equal_score_results()
    legal_results = [r for r in results if hasattr(r, 'rule_text')]
    corpus_results = [r for r in results if hasattr(r, 'clause_text')]
    
    result = merge_retrieval_results(legal_results, corpus_results)
    
    # Should keep only 1 chunk (legal rule prioritized)
    assert len(result.chunks) == 1
    assert result.chunks[0].source_type == "legal_rule"


# TC-5: Near Duplicates - Below Threshold
def test_near_duplicates_below_threshold():
    """
    TC-5: Test that chunks below threshold (90% similarity) are NOT deduplicated.
    """
    results = get_below_threshold_results()
    legal_results = [r for r in results if hasattr(r, 'rule_text')]
    corpus_results = [r for r in results if hasattr(r, 'clause_text')]
    
    result = merge_retrieval_results(legal_results, corpus_results)
    
    # Should keep both chunks (below deduplication threshold)
    assert len(result.chunks) == 2


# TC-6: Empty Results from Both Sources
def test_empty_results_from_both_sources():
    """
    TC-6: Test handling of empty results from both sources.
    """
    result = merge_retrieval_results([], [])
    
    # Should return empty chunks gracefully
    assert len(result.chunks) == 0
    assert result.total_tokens == 0
    assert result.deduplication_stats["total_input"] == 0


# TC-7: Single Source Only (Legal Rules)
def test_single_source_only_legal():
    """
    TC-7: Test merge with only legal rules, no corpus results.
    """
    legal_results = get_unique_legal_results()  # 3 legal rules
    corpus_results = []
    
    result = merge_retrieval_results(legal_results, corpus_results)
    
    # Should have all 3 legal chunks
    assert len(result.chunks) == 3
    assert all(c.source_type == "legal_rule" for c in result.chunks)


# TC-8: Token Budget - Under Budget
def test_token_budget_under_budget():
    """
    TC-8: Test that all chunks are kept when under token budget.
    """
    legal_results = get_unique_legal_results()[:2]  # 2 legal
    corpus_results = get_unique_corpus_results()[:1]  # 1 corpus
    
    # Mock environment to set low budget but still fits
    with patch('app.rag.merge_context.MAX_CONTEXT_TOKENS', 10000):
        result = merge_retrieval_results(legal_results, corpus_results)
    
    # All 3 chunks should be kept
    assert len(result.chunks) == 3
    assert result.trimming_stats["before_trim"] == 3
    assert result.trimming_stats["after_trim"] == 3
    assert result.trimming_stats["tokens_saved"] == 0


# TC-9: Token Budget - Over Budget (Trimming)
def test_token_budget_over_budget_trimming():
    """
    TC-9: Test that lower-similarity chunks are trimmed when over budget.
    """
    legal_results = get_many_legal_results(5)
    corpus_results = get_many_corpus_results(5)
    
    # Mock tiktoken to return predictable token counts
    def mock_encode(text):
        # Return 100 tokens per chunk
        return [0] * 100
    
    with patch('app.rag.merge_context.MAX_CONTEXT_TOKENS', 500):  # Budget for ~5 chunks
        with patch('tiktoken.encoding_for_model') as mock_tokenizer:
            mock_tokenizer.return_value.encode = mock_encode
            result = merge_retrieval_results(legal_results, corpus_results)
    
    # Should have fewer than 10 chunks
    assert len(result.chunks) < 10
    assert result.total_tokens <= 500
    
    # Higher similarity chunks should be prioritized
    # (chunks are already sorted by similarity descending in fixtures)
    assert result.trimming_stats["before_trim"] > result.trimming_stats["after_trim"]


# TC-10: Token Budget - Minimum Chunks Enforced
def test_token_budget_minimum_chunks_enforced():
    """
    TC-10: Test that minimum chunks per source are enforced even if over budget.
    """
    legal_results = get_large_chunk_legal()  # 1 large legal (~800 tokens)
    corpus_results = get_large_chunk_corpus()  # 1 large corpus (~800 tokens)
    
    # Mock tiktoken to return large token counts
    def mock_encode(text):
        return [0] * 800  # 800 tokens per chunk
    
    with patch('app.rag.merge_context.MAX_CONTEXT_TOKENS', 1000):  # Budget exceeded by both
        with patch('app.rag.merge_context.MIN_CHUNKS_PER_SOURCE', 1):
            with patch('tiktoken.encoding_for_model') as mock_tokenizer:
                mock_tokenizer.return_value.encode = mock_encode
                result = merge_retrieval_results(legal_results, corpus_results)
    
    # Both chunks should be kept (minimum enforced)
    assert len(result.chunks) == 2
    assert result.total_tokens > 1000  # Budget exceeded but acceptable


# TC-11: Source Tagging - Legal Rules
def test_source_tagging_legal_rules():
    """
    TC-11: Test source tagging for legal rules with state suffix.
    """
    legal_results = get_unique_legal_results()[:1]  # First has state="MH"
    
    chunks = _convert_to_chunks(legal_results, [])
    
    chunk = chunks[0]
    assert chunk.source_type == "legal_rule"
    assert "Maharashtra Rent Control Act 1999" in chunk.source_reference
    assert "Section 11(2)" in chunk.source_reference
    assert "(MH)" in chunk.source_reference  # State suffix
    assert chunk.text == legal_results[0].rule_text  # Mapped from rule_text
    assert chunk.similarity_score == 0.92  # Mapped from similarity
    
    # Test format_for_prompt
    formatted = chunk.format_for_prompt()
    assert formatted.startswith("[Legal Rule:")
    assert chunk.source_reference in formatted
    assert chunk.text in formatted


# TC-12: Source Tagging - Reference Corpus
def test_source_tagging_reference_corpus():
    """
    TC-12: Test source tagging for reference corpus results.
    """
    corpus_results = get_unique_corpus_results()[:1]
    
    chunks = _convert_to_chunks([], corpus_results)
    
    chunk = chunks[0]
    assert chunk.source_type == "reference_corpus"
    assert chunk.source_reference == "Standard practice - fair deposit terms"
    assert chunk.text == corpus_results[0].clause_text  # Mapped from clause_text
    assert chunk.similarity_score == 0.94  # Mapped from similarity
    
    # Test format_for_prompt
    formatted = chunk.format_for_prompt()
    assert formatted.startswith("[Reference Example:")
    assert chunk.source_reference in formatted
    assert chunk.text in formatted


# TC-13: Format Merged Context for Prompt
def test_format_merged_context_for_prompt():
    """
    TC-13: Test formatting of merged context for prompt inclusion.
    """
    legal_results = get_unique_legal_results()[:2]
    corpus_results = get_unique_corpus_results()[:1]
    
    result = merge_retrieval_results(legal_results, corpus_results)
    formatted = format_merged_context(result)
    
    # Should start with header
    assert formatted.startswith("## Retrieved Context\n\n")
    
    # Should contain formatted chunks
    for chunk in result.chunks:
        assert chunk.source_reference in formatted
        assert chunk.text in formatted
    
    # Chunks should be separated by double newlines
    assert "\n\n" in formatted
    
    # Test empty chunks case
    empty_result = MergeResult(
        chunks=[],
        total_tokens=0,
        deduplication_stats={},
        trimming_stats={}
    )
    empty_formatted = format_merged_context(empty_result)
    assert empty_formatted == "No relevant context found."


# TC-14: Deduplication Stats Accuracy
def test_deduplication_stats_accuracy():
    """
    TC-14: Test accuracy of deduplication statistics.
    """
    # Get 10 chunks with 3 pairs of duplicates
    all_results = get_multiple_duplicate_results()
    legal_results = [r for r in all_results if hasattr(r, 'rule_text')]
    corpus_results = [r for r in all_results if hasattr(r, 'clause_text')]
    
    result = merge_retrieval_results(legal_results, corpus_results)
    
    # Stats should reflect 3 duplicates removed
    assert result.deduplication_stats["total_input"] == 10
    assert result.deduplication_stats["duplicates_removed"] == 3
    assert result.deduplication_stats["final_count"] == 7


# TC-15: Ordering Consistency
def test_ordering_consistency():
    """
    TC-15: Test that output is consistently ordered by similarity_score descending.
    """
    all_results = get_unsorted_results()
    legal_results = [r for r in all_results if hasattr(r, 'rule_text')]
    corpus_results = [r for r in all_results if hasattr(r, 'clause_text')]
    
    result = merge_retrieval_results(legal_results, corpus_results)
    
    # Should be ordered [0.95, 0.90, 0.80, 0.70]
    expected_order = [0.95, 0.90, 0.80, 0.70]
    actual_order = [c.similarity_score for c in result.chunks]
    assert actual_order == expected_order
    
    # Run again to verify deterministic ordering
    result2 = merge_retrieval_results(legal_results, corpus_results)
    actual_order2 = [c.similarity_score for c in result2.chunks]
    assert actual_order2 == expected_order


# Additional helper function tests
def test_compute_text_similarity():
    """Test character n-gram similarity computation."""
    # Identical texts
    assert _compute_text_similarity("hello world", "hello world") == 1.0
    
    # Very similar texts (should be high)
    sim = _compute_text_similarity(
        "The security deposit shall not exceed two months rent",
        "The security deposit shall not exceed two months rent"
    )
    assert sim == 1.0
    
    # Completely different texts (should be low)
    sim = _compute_text_similarity("abc", "xyz")
    assert sim < 0.5
    
    # Empty texts
    assert _compute_text_similarity("", "") == 0.0
    assert _compute_text_similarity("hello", "") == 0.0
