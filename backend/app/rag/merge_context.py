"""
Retrieval merge and context assembly for ScanTract Stage 6.

Combines results from legal KB (5A) and reference corpus (5B),
deduplicates near-identical chunks, tags sources for traceability,
and manages token budgets for LLM context windows.
"""

import os
import logging
from typing import List

import tiktoken

from .models import ContextChunk, MergeResult, SourceType
from db.legal_kb.models import LegalRuleSearchResult
from db.reference_corpus.models import ReferenceClauseSearchResult

logger = logging.getLogger(__name__)

# Configuration from environment
DEDUPLICATION_THRESHOLD = float(os.getenv("DEDUPLICATION_THRESHOLD", "0.95"))
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "4000"))
MIN_CHUNKS_PER_SOURCE = int(os.getenv("MIN_CHUNKS_PER_SOURCE", "1"))


def merge_retrieval_results(
    legal_results: List[LegalRuleSearchResult],
    corpus_results: List[ReferenceClauseSearchResult]
) -> MergeResult:
    """
    Merge and deduplicate retrieval results from both sources.
    
    Orchestrates the complete merge pipeline:
    1. Convert both source types to unified ContextChunk format
    2. Deduplicate near-identical chunks (>95% similarity)
    3. Sort by similarity score descending
    4. Trim to token budget while enforcing minimum per source
    
    Args:
        legal_results: Results from Stage 5A (legal KB search)
        corpus_results: Results from Stage 5B (reference corpus search)
    
    Returns:
        MergeResult with deduplicated, trimmed, and tagged chunks plus stats
    """
    # Step 1: Convert to unified format
    chunks = _convert_to_chunks(legal_results, corpus_results)
    initial_count = len(chunks)
    
    # Step 2: Deduplicate near-identical chunks
    chunks = _deduplicate_chunks(chunks)
    duplicates_removed = initial_count - len(chunks)
    
    logger.info(
        f"Deduplication: {initial_count} -> {len(chunks)} "
        f"(removed {duplicates_removed} duplicates)"
    )
    
    # Step 3: Sort by similarity score (descending)
    chunks.sort(key=lambda c: c.similarity_score, reverse=True)
    
    # Step 4: Trim to token budget
    chunks_before_trim = len(chunks)
    chunks, total_tokens = _trim_to_budget(chunks, MAX_CONTEXT_TOKENS)
    chunks_after_trim = len(chunks)
    
    if chunks_before_trim > chunks_after_trim:
        logger.warning(
            f"Context trimmed: {chunks_before_trim} -> {chunks_after_trim} chunks "
            f"to fit {MAX_CONTEXT_TOKENS} token budget"
        )
    
    # Calculate tokens saved
    tokens_before = _count_tokens(_format_chunks(chunks[:chunks_before_trim])) if chunks_before_trim > 0 else 0
    tokens_saved = max(0, tokens_before - total_tokens)
    
    return MergeResult(
        chunks=chunks,
        total_tokens=total_tokens,
        deduplication_stats={
            "total_input": initial_count,
            "duplicates_removed": duplicates_removed,
            "final_count": len(chunks)
        },
        trimming_stats={
            "before_trim": chunks_before_trim,
            "after_trim": chunks_after_trim,
            "tokens_saved": tokens_saved
        }
    )


def _convert_to_chunks(
    legal_results: List[LegalRuleSearchResult],
    corpus_results: List[ReferenceClauseSearchResult]
) -> List[ContextChunk]:
    """
    Convert search results to unified ContextChunk format.
    
    Field mappings (CRITICAL - see tasks.md):
    - LegalRuleSearchResult.rule_text → ContextChunk.text
    - LegalRuleSearchResult.similarity → ContextChunk.similarity_score
    - ReferenceClauseSearchResult.clause_text → ContextChunk.text
    - ReferenceClauseSearchResult.similarity → ContextChunk.similarity_score
    
    Args:
        legal_results: Legal rule search results from Stage 5A
        corpus_results: Reference corpus search results from Stage 5B
    
    Returns:
        List of unified ContextChunk instances
    """
    chunks = []
    
    # Convert legal rules
    for result in legal_results:
        # Format citation: "{act_name}, {section_reference}" + optional state suffix
        reference = f"{result.act_name}, {result.section_reference}"
        if result.state:
            reference += f" ({result.state})"
        
        # Map rule_text -> text, similarity -> similarity_score
        chunks.append(ContextChunk(
            source_type="legal_rule",
            source_reference=reference,
            text=result.rule_text,  # Map from rule_text
            similarity_score=result.similarity  # Map from similarity
        ))
    
    # Convert reference corpus
    for result in corpus_results:
        # Map clause_text -> text, similarity -> similarity_score
        chunks.append(ContextChunk(
            source_type="reference_corpus",
            source_reference=result.source_label,  # Use source_label directly
            text=result.clause_text,  # Map from clause_text
            similarity_score=result.similarity  # Map from similarity
        ))
    
    return chunks


def _deduplicate_chunks(chunks: List[ContextChunk]) -> List[ContextChunk]:
    """
    Remove near-duplicate chunks using text similarity.
    
    Strategy:
    - Compare all pairs of chunks using character n-gram similarity
    - If similarity > DEDUPLICATION_THRESHOLD (0.95): mark as duplicate
    - Keep chunk with higher similarity_score
    - If scores equal: prefer legal_rule over reference_corpus
    
    Args:
        chunks: List of chunks to deduplicate
    
    Returns:
        Deduplicated list of chunks
    """
    if len(chunks) <= 1:
        return chunks
    
    # Track which chunks to remove
    to_remove = set()
    
    for i in range(len(chunks)):
        if i in to_remove:
            continue
        
        for j in range(i + 1, len(chunks)):
            if j in to_remove:
                continue
            
            # Compute text similarity using n-grams
            similarity = _compute_text_similarity(chunks[i].text, chunks[j].text)
            
            if similarity > DEDUPLICATION_THRESHOLD:
                # Determine which to keep based on similarity_score
                if chunks[i].similarity_score > chunks[j].similarity_score:
                    to_remove.add(j)
                    logger.debug(
                        f"Duplicate detected: keeping chunk {i} "
                        f"(score={chunks[i].similarity_score:.3f} > {chunks[j].similarity_score:.3f})"
                    )
                elif chunks[j].similarity_score > chunks[i].similarity_score:
                    to_remove.add(i)
                    logger.debug(
                        f"Duplicate detected: keeping chunk {j} "
                        f"(score={chunks[j].similarity_score:.3f} > {chunks[i].similarity_score:.3f})"
                    )
                else:
                    # Scores equal: prefer legal rule
                    if chunks[i].source_type == "legal_rule":
                        to_remove.add(j)
                        logger.debug(f"Duplicate detected: keeping legal rule (chunk {i})")
                    else:
                        to_remove.add(i)
                        logger.debug(f"Duplicate detected: keeping legal rule (chunk {j})")
                
                break  # Only mark one duplicate per chunk
    
    # Return non-duplicate chunks
    return [chunk for idx, chunk in enumerate(chunks) if idx not in to_remove]


def _compute_text_similarity(text1: str, text2: str) -> float:
    """
    Compute similarity between two text strings using character n-grams.
    
    Uses Jaccard index (intersection over union) on character 3-grams.
    This is fast and deterministic, sufficient for detecting near-exact
    duplicates without requiring embedding generation.
    
    Args:
        text1: First text string
        text2: Second text string
    
    Returns:
        Similarity score 0.0-1.0 (1.0 = identical)
    """
    def get_ngrams(text: str, n: int = 3) -> set:
        """Generate character n-grams from text."""
        text = text.lower().replace(" ", "")
        return set(text[i:i+n] for i in range(len(text) - n + 1))
    
    ngrams1 = get_ngrams(text1)
    ngrams2 = get_ngrams(text2)
    
    if not ngrams1 or not ngrams2:
        return 0.0
    
    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)
    
    return intersection / union if union > 0 else 0.0


def _trim_to_budget(
    chunks: List[ContextChunk],
    max_tokens: int
) -> tuple[List[ContextChunk], int]:
    """
    Trim chunks to fit within token budget.
    
    Strategy:
    - Chunks assumed to be already sorted by similarity_score descending
    - Greedily add chunks in order until budget reached
    - Enforce MIN_CHUNKS_PER_SOURCE minimum even if exceeding budget
    
    Args:
        chunks: List of chunks (must be sorted by similarity descending)
        max_tokens: Maximum token budget
    
    Returns:
        Tuple of (selected_chunks, total_tokens)
    """
    if not chunks:
        return [], 0
    
    # Initialize tokenizer
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    selected_chunks = []
    total_tokens = 0
    
    # Track source representation
    legal_count = 0
    corpus_count = 0
    
    for chunk in chunks:
        # Format chunk and count tokens
        formatted = chunk.format_for_prompt()
        chunk_tokens = len(tokenizer.encode(formatted))
        
        # Check if adding this chunk would exceed budget
        if total_tokens + chunk_tokens > max_tokens:
            # Check if we have minimum representation
            if legal_count >= MIN_CHUNKS_PER_SOURCE and corpus_count >= MIN_CHUNKS_PER_SOURCE:
                logger.info(f"Token budget reached: {total_tokens}/{max_tokens} tokens")
                break
            
            # If we haven't met minimum, still add if it's from underrepresented source
            if chunk.source_type == "legal_rule" and legal_count < MIN_CHUNKS_PER_SOURCE:
                logger.warning(
                    f"Exceeding token budget to meet minimum legal rules "
                    f"({legal_count + 1}/{MIN_CHUNKS_PER_SOURCE}): adding {chunk_tokens} tokens"
                )
            elif chunk.source_type == "reference_corpus" and corpus_count < MIN_CHUNKS_PER_SOURCE:
                logger.warning(
                    f"Exceeding token budget to meet minimum corpus examples "
                    f"({corpus_count + 1}/{MIN_CHUNKS_PER_SOURCE}): adding {chunk_tokens} tokens"
                )
            else:
                # Budget exceeded and minimum met
                logger.info(f"Token budget limit reached at {total_tokens} tokens")
                break
        
        # Add chunk
        selected_chunks.append(chunk)
        total_tokens += chunk_tokens
        
        # Track source counts
        if chunk.source_type == "legal_rule":
            legal_count += 1
        else:
            corpus_count += 1
    
    logger.info(
        f"Selected {len(selected_chunks)} chunks: "
        f"{legal_count} legal rules, {corpus_count} corpus examples, "
        f"{total_tokens} tokens"
    )
    
    return selected_chunks, total_tokens


def _count_tokens(text: str) -> int:
    """
    Count tokens in text using tiktoken.
    
    Args:
        text: Text to count tokens for
    
    Returns:
        Number of tokens
    """
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(tokenizer.encode(text))


def _format_chunks(chunks: List[ContextChunk]) -> str:
    """
    Format chunks for prompt inclusion.
    
    Args:
        chunks: List of chunks to format
    
    Returns:
        Formatted string with all chunks
    """
    return "\n\n".join(chunk.format_for_prompt() for chunk in chunks)


def format_merged_context(merge_result: MergeResult) -> str:
    """
    Format merged context for Stage 7 risk detection prompt.
    
    Produces a prompt-ready string that can be injected into the
    retrieved_context parameter of Stage 7's risk detection prompt.
    
    Args:
        merge_result: Result from merge_retrieval_results()
    
    Returns:
        Formatted string ready to inject into prompt template
    """
    if not merge_result.chunks:
        return "No relevant context found."
    
    formatted = "## Retrieved Context\n\n"
    formatted += _format_chunks(merge_result.chunks)
    
    return formatted
