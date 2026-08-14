# Design Decisions: Prompt Templating (Stage 3)

## Cross-Spec Dependency Resolution

### Issue
The original Stage 3 requirements (FR-2) specified that `build_risk_prompt()` should accept separate `legal_context` and `corpus_context` parameters:

```python
# Original requirement (FR-2)
build_risk_prompt(
    clauses_list=[...],
    legal_context="...",      # Legal rules from Stage 5A
    corpus_context="...",     # Reference examples from Stage 5B
    contract_type="rental"
)
```

However, the downstream Stage 7 (risk detection) spec shows the actual usage after Stage 6 has already merged and deduplicated the contexts:

```python
# Actual usage in Stage 7
prompt_messages = build_risk_prompt(
    clauses_list=[...],
    legal_context=merged_context,  # Already merged by Stage 6
    contract_type=contract.contract_type
)
```

### Resolution
**Decision**: Make `build_risk_prompt()` accept a **single** `retrieved_context` parameter instead of separate `legal_context` and `corpus_context` parameters.

**Rationale**:
1. **Separation of Concerns**: Stage 6 (merge_context) is responsible for combining, deduplicating, and formatting context from both sources. Stage 3 (prompt templates) should not need to know about the internal structure of retrieval sources.

2. **Consistency**: The `build_classification_prompt()` function already uses `retrieved_context` as its parameter name. Using the same naming convention across both prompt builders improves API consistency.

3. **Simplicity**: By the time risk detection runs (Stage 7), context has already been merged into a single formatted string. Requiring two separate parameters would force Stage 7 to artificially split what has already been unified.

4. **Flexibility**: If future stages need to provide context from additional sources (e.g., case law, regulatory guidance), the single `retrieved_context` parameter can accommodate any merged format without changing the prompt builder signature.

### Final Signature
```python
def build_risk_prompt(
    clauses_list: list[dict],
    retrieved_context: str,  # Single merged context from Stage 6
    contract_type: str
) -> list[dict]:
    """
    Build risk detection prompt.
    
    Args:
        clauses_list: List of clause dicts with clause_id, clause_type, clause_text
        retrieved_context: Merged and formatted context from Stage 6 (includes both
                          legal rules and reference corpus examples)
        contract_type: "rental" or "freelance"
    
    Returns:
        LangChain-compatible message array ready for LLM
    """
```

### Template Variable
The `risk_detection.txt` template will use `{retrieved_context}` as the placeholder, matching the parameter name.

## Template Loading Strategy

### Lazy Loading with Caching
Templates are loaded once at first use and cached in memory to avoid repeated file I/O operations.

**Implementation**:
- Module-level cache dictionary: `_template_cache = {}`
- First call to `_load_template("risk_detection")` reads file and caches result
- Subsequent calls return cached string
- No cache invalidation during runtime (templates are static)

**Benefits**:
- Fast prompt assembly (<1ms after first load)
- No file I/O during request processing
- Simple implementation (no external cache library needed)

## Placeholder Validation Strategy

### Two-Phase Validation
1. **Template-Level Validation** (at load time):
   - Verify template file exists
   - Verify template is valid text
   - Log available placeholders for debugging

2. **Assembly-Level Validation** (at runtime):
   - After variable substitution, scan for remaining `{...}` patterns
   - If any `{variable}` remains unfilled, raise `ValueError` with clear message
   - Exception message lists which variables were not filled

**Edge Cases**:
- Literal braces in template text: Escape as `{{` and `}}` (Python format string convention)
- Optional variables: Not supported in initial implementation (all variables required)
- Nested placeholders: Not supported (simple flat substitution only)

## Compliance Instructions Integration

The mandatory compliance instructions from FR-5 are embedded directly in both template files:

**Required Instructions**:
1. "Never provide legal advice or use imperative language like 'you should' or 'you must'"
2. "Always cite which legal rule or reference clause triggered each finding"
3. "Use descriptive comparisons: 'this clause differs from X because Y'"
4. "Assign severity scores (low/medium/high) based on objective criteria"
5. "Provide explanations that are factual and educational, not prescriptive"

These instructions appear verbatim in the system prompt section of both templates to ensure consistent LLM behavior across classification and risk detection.
