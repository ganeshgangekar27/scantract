# Spec: Retrieval Merge & Context Assembly

## Overview
Build the retrieval merge layer for ScanTract — Stage 6 of the core pipeline that combines results from the legal rules knowledge base (Stage 5A) and reference contract corpus (Stage 5B), deduplicates near-identical chunks, tags sources for traceability, and manages token budgets for LLM context windows.

## Scope
- Merge function combining legal rules + reference corpus results
- Near-duplicate detection using cosine similarity
- Source tagging for citation traceability
- Token budget management with priority-based trimming
- Ordered context list ready for Stage 7 risk detection prompt
- Unit tests covering edge cases

## Requirements

### Functional Requirements

**FR-1: Merge Function**
- Function: `merge_retrieval_results(legal_results, corpus_results) -> list[ContextChunk]`
- Combines results from Stage 5A (legal rules) and Stage 5B (reference corpus)
- Returns unified list of context chunks
- Each chunk tagged with source type and reference
- Preserves similarity scores from original searches

**FR-2: Deduplication**
- Detect near-duplicate text chunks using cosine similarity
- Threshold: similarity > 0.95 = considered duplicate
- When duplicates found: keep the one with higher similarity score
- If scores equal: prioritize legal rules over corpus (legal authority > example)
- Deduplication runs on text content, not embeddings (recompute similarity)


**FR-3: Source Tagging**
- Each context chunk tagged with:
  - `source_type`: "legal_rule" or "reference_corpus"
  - `source_reference`: Full citation/label for traceability
    - Legal rules: "Model Tenancy Act 2021, Section 7(1)"
    - Reference corpus: "Standard practice - fair deposit terms"
  - `text`: The actual content
  - `similarity_score`: Original search similarity (0.0-1.0)
- Tags must survive through to Stage 8 (citation generation)

**FR-4: Token Budget Management**
- Read `MAX_CONTEXT_TOKENS` from environment (default: 4000)
- Count tokens in merged context using tiktoken (OpenAI tokenizer)
- If context exceeds budget: trim lower-similarity chunks
- Prioritization when trimming:
  1. Higher similarity score first
  2. Legal rules over corpus (if scores equal)
  3. Never reduce below minimum (e.g., 1 legal rule + 1 corpus example)
- Log warning if trimming occurs

**FR-5: Ordering**
- Return chunks ordered by similarity score (descending)
- Most relevant context appears first
- Maintains consistent ordering for reproducible results

**FR-6: Edge Cases**
- Handle empty results from either source gracefully
- Handle case where all chunks are duplicates
- Handle single-result cases (nothing to dedupe)
- Handle over-budget with only 1-2 chunks (don't trim below minimum)

### Non-Functional Requirements

**NFR-1: Performance**
- Merge operation completes in <50ms for typical case (10 legal + 10 corpus)
- Deduplication algorithm: O(n²) acceptable for small n (<50 chunks)
- Token counting: <10ms using tiktoken

**NFR-2: Accuracy**
- Deduplication threshold (0.95) balances precision/recall
- Token counting accurate within 5% of actual LLM token count
- No information loss during merge (all metadata preserved)

**NFR-3: Type Safety**
- All functions use type hints (Python 3.11+)
- Pydantic models for context chunks
- Clear input/output contracts


**NFR-4: Maintainability**
- Clear separation: deduplication vs trimming logic
- Configurable thresholds (similarity, token budget, minimum chunks)
- Logging for debugging (what was deduplicated, what was trimmed)

**NFR-5: Traceability**
- Every chunk traceable to original source
- Citations survive merge/dedup/trim operations
- Audit trail in logs (for debugging citation issues)

## Technical Design

### Module Structure

**Location:** `backend/app/rag/`

```
backend/app/rag/
├── __init__.py
├── embeddings.py          # Shared embedding (from Stage 5A/5B)
├── merge_context.py       # Merge logic (NEW)
├── models.py              # Pydantic models (NEW)
└── prompts/               # Prompt templates (from Stage 3)
```

### Data Models

**File: backend/app/rag/models.py**

```python
from pydantic import BaseModel, Field
from typing import Literal

SourceType = Literal["legal_rule", "reference_corpus"]

class ContextChunk(BaseModel):
    """
    Unified context chunk from retrieval merge.
    
    Used in Stage 7 risk detection prompt.
    """
    source_type: SourceType
    source_reference: str = Field(
        description="Full citation or label for traceability"
    )
    text: str = Field(description="The actual content")
    similarity_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Original search similarity score"
    )
    
    def format_for_prompt(self) -> str:
        """Format for inclusion in LLM prompt."""
        source_label = "Legal Rule" if self.source_type == "legal_rule" else "Reference Example"
        return f"[{source_label}: {self.source_reference}]\n{self.text}"
    
    class Config:
        frozen = True  # Immutable for safety

class MergeResult(BaseModel):
    """Result of merge operation with metadata."""
    chunks: list[ContextChunk]
    total_tokens: int
    deduplication_stats: dict[str, int] = Field(
        description="Stats: total_input, duplicates_removed, final_count"
    )
    trimming_stats: dict[str, int] = Field(
        description="Stats: before_trim, after_trim, tokens_saved"
    )
```


### Core Merge Logic

**File: backend/app/rag/merge_context.py**

```python
"""
Retrieval merge and context assembly for ScanTract Stage 6.

Combines results from legal KB (5A) and reference corpus (5B),
deduplicates, tags sources, and manages token budgets.
"""

import os
import logging
from typing import List
import tiktoken

from .models import ContextChunk, MergeResult, SourceType
from ..db.legal_kb.models import LegalRuleSearchResult
from ..db.reference_corpus.models import ReferenceClauseSearchResult

logger = logging.getLogger(__name__)

# Configuration
DEDUPLICATION_THRESHOLD = float(os.getenv("DEDUPLICATION_THRESHOLD", "0.95"))
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "4000"))
MIN_CHUNKS_PER_SOURCE = int(os.getenv("MIN_CHUNKS_PER_SOURCE", "1"))

def merge_retrieval_results(
    legal_results: List[LegalRuleSearchResult],
    corpus_results: List[ReferenceClauseSearchResult]
) -> MergeResult:
    """
    Merge and deduplicate retrieval results from both sources.
    
    Args:
        legal_results: Results from Stage 5A (legal KB)
        corpus_results: Results from Stage 5B (reference corpus)
    
    Returns:
        MergeResult with deduplicated, trimmed, and tagged chunks
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
            "tokens_saved": _count_tokens(_format_chunks(chunks[:chunks_before_trim])) - total_tokens
        }
    )
```


### Helper Functions

**File: backend/app/rag/merge_context.py (continued)**

```python
def _convert_to_chunks(
    legal_results: List[LegalRuleSearchResult],
    corpus_results: List[ReferenceClauseSearchResult]
) -> List[ContextChunk]:
    """Convert search results to unified ContextChunk format."""
    chunks = []
    
    # Convert legal rules
    for result in legal_results:
        reference = f"{result.act_name}, {result.section_reference}"
        if result.state:
            reference += f" ({result.state})"
        
        chunks.append(ContextChunk(
            source_type="legal_rule",
            source_reference=reference,
            text=result.rule_text,
            similarity_score=result.similarity_score
        ))
    
    # Convert reference corpus
    for result in corpus_results:
        chunks.append(ContextChunk(
            source_type="reference_corpus",
            source_reference=result.source_label,
            text=result.clause_text,
            similarity_score=result.similarity_score
        ))
    
    return chunks

def _deduplicate_chunks(chunks: List[ContextChunk]) -> List[ContextChunk]:
    """
    Remove near-duplicate chunks using text similarity.
    
    Strategy:
    - Compare all pairs of chunks
    - If similarity > threshold (0.95): mark as duplicate
    - Keep chunk with higher similarity score
    - If scores equal: prefer legal_rule over reference_corpus
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
            
            # Compute text similarity
            similarity = _compute_text_similarity(chunks[i].text, chunks[j].text)
            
            if similarity > DEDUPLICATION_THRESHOLD:
                # Determine which to keep
                if chunks[i].similarity_score > chunks[j].similarity_score:
                    to_remove.add(j)
                    logger.debug(f"Duplicate detected: keeping chunk {i} (score={chunks[i].similarity_score:.3f})")
                elif chunks[j].similarity_score > chunks[i].similarity_score:
                    to_remove.add(i)
                    logger.debug(f"Duplicate detected: keeping chunk {j} (score={chunks[j].similarity_score:.3f})")
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
    Compute cosine similarity between two text strings.
    
    Uses character n-gram overlap for speed (no embedding needed).
    For more accurate deduplication, could use embeddings, but n-grams
    are sufficient for near-exact duplicates.
    """
    # Simple implementation: character 3-grams
    def get_ngrams(text: str, n: int = 3) -> set:
        text = text.lower().replace(" ", "")
        return set(text[i:i+n] for i in range(len(text) - n + 1))
    
    ngrams1 = get_ngrams(text1)
    ngrams2 = get_ngrams(text2)
    
    if not ngrams1 or not ngrams2:
        return 0.0
    
    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)
    
    return intersection / union if union > 0 else 0.0
```


### Token Budget Management

**File: backend/app/rag/merge_context.py (continued)**

```python
def _trim_to_budget(
    chunks: List[ContextChunk],
    max_tokens: int
) -> tuple[List[ContextChunk], int]:
    """
    Trim chunks to fit within token budget.
    
    Strategy:
    - Chunks already sorted by similarity (descending)
    - Add chunks in order until budget reached
    - Ensure minimum representation from each source
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
        # Format chunk for prompt
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
                    f"({legal_count}/{MIN_CHUNKS_PER_SOURCE})"
                )
            elif chunk.source_type == "reference_corpus" and corpus_count < MIN_CHUNKS_PER_SOURCE:
                logger.warning(
                    f"Exceeding token budget to meet minimum corpus examples "
                    f"({corpus_count}/{MIN_CHUNKS_PER_SOURCE})"
                )
            else:
                # Budget exceeded and minimum met
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
    """Count tokens in text using tiktoken."""
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(tokenizer.encode(text))

def _format_chunks(chunks: List[ContextChunk]) -> str:
    """Format chunks for prompt inclusion."""
    return "\n\n".join(chunk.format_for_prompt() for chunk in chunks)

def format_merged_context(merge_result: MergeResult) -> str:
    """
    Format merged context for Stage 7 risk detection prompt.
    
    Returns:
        Formatted string ready to inject into prompt template
    """
    if not merge_result.chunks:
        return "No relevant context found."
    
    formatted = "## Retrieved Context\n\n"
    formatted += _format_chunks(merge_result.chunks)
    
    return formatted
```


## Test Plan

### Test Strategy

**Test Fixtures:**
- Small sets of legal rules and corpus results
- Predefined duplicate pairs
- Token budget scenarios (under, at, over budget)

### Test Cases

**Test File:** `backend/tests/test_merge_context.py`

**TC-1: Basic Merge - No Duplicates**
- Input: 3 legal rules + 3 corpus results, all unique
- Verify: 6 chunks returned
- Verify: All chunks have correct source_type and source_reference
- Verify: Chunks ordered by similarity (descending)

**TC-2: Exact Duplicates - Same Text**
- Input: 2 legal rules with identical text but different scores (0.9, 0.8)
- Verify: 1 chunk returned (higher score kept)
- Verify: Correct source_reference preserved

**TC-3: Near Duplicates - Similar Text**
- Input: 2 chunks with 96% similarity (above 0.95 threshold)
- Verify: 1 chunk returned
- Verify: Higher similarity score chunk kept

**TC-4: Priority When Scores Equal**
- Input: Legal rule + corpus result with identical text and same score
- Verify: Legal rule kept (prioritized over corpus)

**TC-5: No Duplicates - Below Threshold**
- Input: 2 chunks with 90% similarity (below 0.95 threshold)
- Verify: Both chunks returned (not considered duplicates)

**TC-6: Empty Results**
- Input: Empty legal_results and empty corpus_results
- Verify: Empty chunks list returned gracefully
- Verify: No errors raised

**TC-7: Single Source Only**
- Input: 5 legal rules, 0 corpus results
- Verify: All 5 legal rules returned
- Verify: No errors

**TC-8: Token Budget - Under Budget**
- Input: 3 chunks totaling 500 tokens, budget=1000
- Verify: All 3 chunks returned
- Verify: total_tokens = 500

**TC-9: Token Budget - Over Budget (Trimming)**
- Input: 10 chunks totaling 5000 tokens, budget=1000
- Verify: Fewer than 10 chunks returned
- Verify: total_tokens <= 1000
- Verify: Higher similarity chunks prioritized
- Verify: trimming_stats populated

**TC-10: Token Budget - Minimum Chunks Enforced**
- Input: 1 legal rule (800 tokens) + 1 corpus (800 tokens), budget=1000
- Verify: Both chunks returned (minimum 1 per source)
- Verify: Budget exceeded but minimum met
- Verify: Warning logged

**TC-11: Source Tagging - Legal Rules**
- Input: Legal rule from "Model Tenancy Act 2021, Section 7(1)"
- Verify: source_type = "legal_rule"
- Verify: source_reference includes act name and section
- Verify: format_for_prompt() includes "[Legal Rule: ...]"

**TC-12: Source Tagging - Reference Corpus**
- Input: Corpus result with source_label "Standard practice"
- Verify: source_type = "reference_corpus"
- Verify: source_reference = "Standard practice"
- Verify: format_for_prompt() includes "[Reference Example: ...]"

**TC-13: Format for Prompt**
- Input: MergeResult with 3 chunks
- Call format_merged_context()
- Verify: Returns formatted string with "## Retrieved Context"
- Verify: Each chunk formatted with source label
- Verify: Chunks separated by double newlines

**TC-14: Deduplication Stats**
- Input: 10 chunks with 3 duplicates
- Verify: deduplication_stats["total_input"] = 10
- Verify: deduplication_stats["duplicates_removed"] = 3
- Verify: deduplication_stats["final_count"] = 7

**TC-15: Ordering Consistency**
- Input: Chunks with scores [0.9, 0.7, 0.95, 0.8]
- Verify: Output ordered [0.95, 0.9, 0.8, 0.7]
- Verify: Order deterministic across multiple runs


## Environment Variables

**Configuration (.env):**
```bash
# Deduplication threshold (0.0-1.0)
DEDUPLICATION_THRESHOLD=0.95  # Chunks with >95% similarity are duplicates

# Maximum tokens for merged context
MAX_CONTEXT_TOKENS=4000  # Fits comfortably in most LLM context windows

# Minimum chunks per source (ensures balanced context)
MIN_CHUNKS_PER_SOURCE=1  # At least 1 legal rule and 1 corpus example
```

## Integration with Pipeline

**Updated Stage 7 Risk Detection Flow:**

```python
from backend.app.rag.merge_context import merge_retrieval_results, format_merged_context
from backend.db.legal_kb.search import search_legal_rules
from backend.db.reference_corpus.search import search_reference_corpus

async def detect_risks_for_contract(
    contract_id: str,
    contract_type: str,
    state: str | None,
    db: AsyncSession
) -> RiskDetectionResult:
    """Stage 7: Risk detection with merged context from 5A + 5B."""
    
    # Fetch clauses for contract
    clauses = await fetch_contract_clauses(contract_id, db)
    
    all_risks = []
    
    for clause in clauses:
        # Stage 5A: Search legal rules
        legal_results = await search_legal_rules(
            clause_text=clause.clause_text,
            state=state,
            top_k=5,
            db=db
        )
        
        # Stage 5B: Search reference corpus
        corpus_results = await search_reference_corpus(
            clause_text=clause.clause_text,
            contract_type=contract_type,
            top_k=5,
            db=db
        )
        
        # Stage 6: Merge and deduplicate
        merge_result = merge_retrieval_results(legal_results, corpus_results)
        
        # Format for prompt
        context_str = format_merged_context(merge_result)
        
        # Stage 7: LLM risk detection with merged context
        risks = await detect_clause_risks(
            clause=clause,
            context=context_str,
            contract_type=contract_type
        )
        
        all_risks.extend(risks)
    
    return RiskDetectionResult(
        contract_id=contract_id,
        risks=all_risks,
        context_stats=merge_result.deduplication_stats
    )
```


## Design Tradeoffs

### Deduplication Algorithm

**Chosen: Character n-gram similarity (Jaccard index)**

**Pros:**
- Fast: O(n) per comparison, no external API calls
- Sufficient for near-exact duplicates (>95% similar)
- Deterministic and reproducible
- No additional embedding generation needed

**Cons:**
- Less accurate than semantic similarity
- May miss paraphrased duplicates
- Sensitive to minor wording changes

**Alternative Considered:** Embedding-based cosine similarity
- More accurate semantically
- Would require generating embeddings for deduplication (costly)
- Overkill for detecting near-exact duplicates

**When to Upgrade:**
- If seeing too many "pseudo-duplicates" (same meaning, different words)
- Could switch to embedding-based for threshold <0.90
- Current approach good for threshold >0.95

### Token Counting

**Chosen: tiktoken (OpenAI tokenizer)**

**Pros:**
- Accurate for OpenAI models (GPT-3.5, GPT-4)
- Fast: <10ms for typical context
- Handles edge cases (emojis, special chars)

**Cons:**
- OpenAI-specific (not ideal for Claude)
- Undercounts slightly for Claude (different tokenizer)

**Alternative:** Approximate (character count / 4)
- Fast but inaccurate (±20% error)
- Not acceptable for strict budget enforcement

**Future:** Support multiple tokenizers via LLM_PROVIDER

### Trimming Strategy

**Chosen: Greedy by similarity score**

**Strategy:**
1. Sort by similarity (descending)
2. Add chunks until budget reached
3. Enforce minimum per source

**Pros:**
- Simple and predictable
- Prioritizes most relevant content
- Guarantees balanced representation

**Cons:**
- May drop entire categories (e.g., all payment clauses)
- No diversity consideration

**Alternative:** Category-aware trimming
- Ensure at least 1 chunk per category
- More complex implementation
- Could add in future if needed


## Files to Create/Modify

### New Files

**Module:**
1. `backend/app/rag/models.py` - Pydantic models (ContextChunk, MergeResult)
2. `backend/app/rag/merge_context.py` - Merge and deduplication logic

**Tests:**
3. `backend/tests/test_merge_context.py` - Unit tests (15 test cases)
4. `backend/tests/fixtures/merge_test_data.py` - Test fixtures

### Modified Files

5. `backend/requirements.txt` - Add tiktoken
6. `backend/.env.example` - Document merge config vars
7. `backend/README.md` - Document merge step in pipeline

## Dependencies

**Python Packages (backend/requirements.txt):**
```
# Token counting
tiktoken>=0.5.0

# Already included from previous specs:
# pydantic, sqlalchemy, asyncpg, openai
```

## Performance Benchmarks

**Target Performance:**
- Merge operation: <50ms for 20 chunks
- Deduplication (n=20): <30ms (O(n²) = 400 comparisons)
- Token counting: <10ms
- Total Stage 6 time: <100ms

**Complexity Analysis:**
- Deduplication: O(n²) where n = number of chunks
- For n=50: 2,500 comparisons (still <100ms)
- For n=100: 10,000 comparisons (may need optimization)

**Optimization Opportunities:**
- Early exit after first duplicate found per chunk
- Parallel comparison (asyncio) if n >50
- Cache n-grams to avoid recomputation

## Out of Scope

**Explicitly NOT included in this spec:**
- Stage 7 (Risk detection with merged context) - separate spec
- Stage 8 (Citation generation) - separate spec
- Advanced deduplication (semantic, ML-based)
- Category-aware trimming
- Multi-language deduplication
- Context compression (summarization)
- User-configurable merging strategies


## Success Criteria

- [ ] `merge_retrieval_results()` combines legal rules + corpus results
- [ ] Near-duplicate detection using >0.95 similarity threshold
- [ ] Duplicates removed, higher-score chunk kept
- [ ] Legal rules prioritized over corpus when scores equal
- [ ] All chunks tagged with source_type and source_reference
- [ ] Citations fully traceable through merge operation
- [ ] Token counting accurate using tiktoken
- [ ] Token budget enforced (trims lower-similarity chunks)
- [ ] Minimum chunks per source enforced (at least 1 legal + 1 corpus)
- [ ] Chunks ordered by similarity score (descending)
- [ ] `format_merged_context()` produces prompt-ready string
- [ ] Empty results handled gracefully (no errors)
- [ ] All 15 test cases pass
- [ ] Merge completes in <50ms for typical case
- [ ] Deduplication stats and trimming stats populated

## Notes

- This spec covers Stage 6 (Retrieval Merge) of the ScanTract pipeline
- Stage 5A (Legal KB) and 5B (Reference Corpus) provide input
- Stage 7 (Risk Detection) consumes merged context
- Stage 8 (Citation Generation) uses source_reference tags
- Deduplication threshold (0.95) may need tuning based on production data
- Token budget (4000) leaves room for prompt + response in 8K context window
- Use Conventional Commits: `feat:` for merge logic, `test:` for tests

## References

- tiktoken docs: https://github.com/openai/tiktoken
- Jaccard similarity: https://en.wikipedia.org/wiki/Jaccard_index
- N-gram algorithms: https://en.wikipedia.org/wiki/N-gram
- LLM context windows: https://platform.openai.com/docs/models

## Appendix: Example Merge Operation

**Input:**
```python
legal_results = [
    LegalRuleSearchResult(
        id="1",
        act_name="Model Tenancy Act 2021",
        section_reference="Section 7(1)",
        rule_text="The security deposit shall not exceed two months' rent...",
        similarity_score=0.92
    ),
    LegalRuleSearchResult(
        id="2",
        act_name="Maharashtra Rent Control Act 1999",
        section_reference="Section 11(2)",
        rule_text="Security deposit for residential premises shall not exceed three months' rent...",
        similarity_score=0.88
    )
]

corpus_results = [
    ReferenceClauseSearchResult(
        id="3",
        contract_type="rental",
        clause_category="security_deposit",
        clause_text="The security deposit shall be equivalent to two months' rent...",
        source_label="Standard practice - fair deposit terms",
        similarity_score=0.94
    ),
    ReferenceClauseSearchResult(
        id="4",
        contract_type="rental",
        clause_category="security_deposit",
        clause_text="The security deposit shall not exceed two months' rent...",
        source_label="Fair practice example",
        similarity_score=0.91
    )
]
```

**Deduplication:**
- Chunk 1 (legal) and Chunk 4 (corpus) are 97% similar (above 0.95 threshold)
- Keep Chunk 1 (score 0.92 vs 0.91, and legal rule prioritized)

**Output (after merge):**
```python
MergeResult(
    chunks=[
        ContextChunk(
            source_type="reference_corpus",
            source_reference="Standard practice - fair deposit terms",
            text="The security deposit shall be equivalent to two months' rent...",
            similarity_score=0.94
        ),
        ContextChunk(
            source_type="legal_rule",
            source_reference="Model Tenancy Act 2021, Section 7(1)",
            text="The security deposit shall not exceed two months' rent...",
            similarity_score=0.92
        ),
        ContextChunk(
            source_type="legal_rule",
            source_reference="Maharashtra Rent Control Act 1999, Section 11(2) (Maharashtra)",
            text="Security deposit for residential premises shall not exceed three months' rent...",
            similarity_score=0.88
        )
    ],
    total_tokens=245,
    deduplication_stats={
        "total_input": 4,
        "duplicates_removed": 1,
        "final_count": 3
    },
    trimming_stats={
        "before_trim": 3,
        "after_trim": 3,
        "tokens_saved": 0
    }
)
```

**Formatted for Prompt:**
```
## Retrieved Context

[Reference Example: Standard practice - fair deposit terms]
The security deposit shall be equivalent to two months' rent...

[Legal Rule: Model Tenancy Act 2021, Section 7(1)]
The security deposit shall not exceed two months' rent...

[Legal Rule: Maharashtra Rent Control Act 1999, Section 11(2) (Maharashtra)]
Security deposit for residential premises shall not exceed three months' rent...
```
