# Stage 6: Retrieval Merge & Context Assembly — Implementation Tasks

## Overview
Implement Stage 6 (Retrieval Merge) of ScanTract: merge legal rules (5A) and reference corpus (5B) results, deduplicate near-identical chunks, enforce token budgets, and produce unified context for Stage 7 risk detection.

## Field Mapping Corrections (Critical)

**Source Models (as actually built in Stage 5A/5B):**
- `LegalRuleSearchResult`: id, state (Optional[str]), act_name, section_reference, **rule_text**, **similarity** (float)
- `ReferenceClauseSearchResult`: id, contract_type, clause_category, **clause_text**, source_label, **similarity** (float)

**Key Mappings for ContextChunk Model:**
- `similarity` (from both sources) → `similarity_score` (ContextChunk field with Pydantic validation ge=0.0, le=1.0)
- `rule_text` (LegalRuleSearchResult) → `text` (ContextChunk field)
- `clause_text` (ReferenceClauseSearchResult) → `text` (ContextChunk field)
- Legal citation: format as `f"{act_name}, {section_reference}"` (add state in parens if present)
- Reference citation: use `source_label` directly

**No Overlapping Fields Between Sources:**
- Legal rules have: state, act_name, section_reference, rule_text
- Reference clauses have: contract_type, clause_category, clause_text, source_label
- Both have: id, similarity (normalized to similarity_score in ContextChunk)

---

## Tasks

### Task 1: Create Unified Data Models
**File:** `backend/app/rag/models.py`

**Requirements:**
- Create `ContextChunk` Pydantic model:
  - `source_type`: Literal["legal_rule", "reference_corpus"]
  - `source_reference`: str (formatted citation/label for traceability)
  - `text`: str (normalized content field from rule_text or clause_text)
  - `similarity_score`: float with Pydantic validation `ge=0.0, le=1.0` (mapped from source's `similarity` field)
  - `format_for_prompt() -> str` method: returns formatted string like `[Legal Rule: {source_reference}]\n{text}` or `[Reference Example: {source_reference}]\n{text}`
  - Mark as `frozen=True` (immutable for safety)

- Create `MergeResult` Pydantic model:
  - `chunks`: list[ContextChunk]
  - `total_tokens`: int
  - `deduplication_stats`: dict[str, int] with keys: total_input, duplicates_removed, final_count
  - `trimming_stats`: dict[str, int] with keys: before_trim, after_trim, tokens_saved

**Code Comments:**
- Explicitly document the `similarity` → `similarity_score` mapping in docstrings
- Note that validation is added here even though ReferenceClauseSearchResult lacks it

---

### Task 2: Implement Core Merge Logic
**File:** `backend/app/rag/merge_context.py`

**Import Corrections:**
- Import from `db.legal_kb.models import LegalRuleSearchResult` (NOT app.db)
- Import from `db.reference_corpus.models import ReferenceClauseSearchResult` (NOT app.db)
- Import from `.models import ContextChunk, MergeResult` (local to app/rag/)

**Functions to Implement:**

**2.1: `_convert_to_chunks(legal_results, corpus_results) -> list[ContextChunk]`**
- For each `LegalRuleSearchResult`:
  - Extract `rule_text` → map to ContextChunk.text
  - Extract `similarity` → map to ContextChunk.similarity_score
  - Format citation: `f"{act_name}, {section_reference}"` (add ` ({state})` suffix if state is not None)
  - Set source_type="legal_rule"
  
- For each `ReferenceClauseSearchResult`:
  - Extract `clause_text` → map to ContextChunk.text
  - Extract `similarity` → map to ContextChunk.similarity_score
  - Use `source_label` directly as source_reference
  - Set source_type="reference_corpus"

- Add explicit code comments showing field mappings (e.g., `# Map rule_text -> text, similarity -> similarity_score`)

**2.2: `_deduplicate_chunks(chunks) -> list[ContextChunk]`**
- Use `_compute_text_similarity()` helper (character n-grams, Jaccard index)
- Threshold: `DEDUPLICATION_THRESHOLD` (default 0.95 from env)
- Deduplication rules:
  1. If similarity > threshold: mark as duplicate
  2. Keep chunk with higher `similarity_score`
  3. If scores equal: prefer `source_type=="legal_rule"` over `"reference_corpus"`
- Return deduplicated list
- Log debug info for each duplicate detected

**2.3: `_compute_text_similarity(text1, text2) -> float`**
- Character 3-gram approach using Jaccard index
- Lowercase and strip whitespace before n-gram generation
- Return float 0.0-1.0 (intersection / union)

**2.4: `_trim_to_budget(chunks, max_tokens) -> tuple[list[ContextChunk], int]`**
- Use tiktoken to count tokens for each chunk's formatted output
- Assume chunks already sorted by similarity_score descending
- Greedily add chunks until budget reached
- Enforce `MIN_CHUNKS_PER_SOURCE` (default 1) even if exceeding budget:
  - Track legal_count and corpus_count
  - If under minimum for a source type, allow budget overrun with warning log
- Return (selected_chunks, total_tokens)

**2.5: `_count_tokens(text) -> int`**
- Use tiktoken.encoding_for_model("gpt-3.5-turbo")
- Return token count for given text

**2.6: `_format_chunks(chunks) -> str`**
- Call each chunk's `format_for_prompt()` method
- Join with `\n\n` separator
- Return concatenated string

**2.7: `merge_retrieval_results(legal_results, corpus_results) -> MergeResult`**
- Orchestrate: convert → deduplicate → sort → trim
- Sort by similarity_score descending after deduplication
- Populate deduplication_stats and trimming_stats dicts
- Log info/warning messages for deduplication and trimming
- Return MergeResult

**2.8: `format_merged_context(merge_result) -> str`**
- Format as `## Retrieved Context\n\n{formatted_chunks}`
- Handle empty chunks case: return "No relevant context found."
- This output is ready for Stage 7's risk detection prompt (single `retrieved_context` parameter)

**Configuration:**
- Read from environment: `DEDUPLICATION_THRESHOLD`, `MAX_CONTEXT_TOKENS`, `MIN_CHUNKS_PER_SOURCE`
- Default values: 0.95, 4000, 1

---

### Task 3: Update Environment Configuration
**Files:** `backend/.env.example` and `backend/.env`

**Add these variables with defaults:**
```bash
# Stage 6: Retrieval Merge Configuration
DEDUPLICATION_THRESHOLD=0.95  # Text similarity >0.95 = duplicate (0.0-1.0)
MAX_CONTEXT_TOKENS=4000        # Maximum tokens for merged context (enforced via tiktoken)
MIN_CHUNKS_PER_SOURCE=1        # Minimum chunks from each source (legal_rule, reference_corpus)
```

**Documentation in comments:**
- Explain that 0.95 threshold balances precision/recall for near-exact duplicates
- 4000 tokens fits comfortably in typical LLM context windows (leaves room for prompt + response)
- MIN_CHUNKS_PER_SOURCE ensures balanced representation even when over budget

---

### Task 4: Add tiktoken Dependency
**File:** `backend/requirements.txt`

**Action:**
- Check if `tiktoken>=0.5.0` already present
- If not, add it under the "# LLM & RAG" section (after openai/anthropic/google-generativeai lines)
- Format: `tiktoken>=0.5.0  # Token counting for context budget management`

---

### Task 5: Create Test Fixtures
**File:** `backend/tests/fixtures/merge_test_data.py`

**Requirements:**
- Create small test fixtures using REAL field names from Stage 5A/5B models
- Mock LegalRuleSearchResult instances:
  - Use fields: id, state (Optional[str]), act_name, section_reference, **rule_text**, **similarity**
  - Example: `LegalRuleSearchResult(id=1, state="MH", act_name="Maharashtra Rent Control Act 1999", section_reference="Section 11(2)", rule_text="Security deposit shall not exceed...", similarity=0.92)`

- Mock ReferenceClauseSearchResult instances:
  - Use fields: id, contract_type, clause_category, **clause_text**, source_label, **similarity**
  - Example: `ReferenceClauseSearchResult(id=101, contract_type="rental", clause_category="security_deposit", clause_text="The security deposit shall be...", source_label="Standard practice - fair deposit terms", similarity=0.94)`

- Create fixtures for:
  - Unique chunks (no duplicates)
  - Exact duplicate pairs (same text, different scores)
  - Near-duplicate pairs (96% similarity, above threshold)
  - Below-threshold pairs (90% similarity)
  - Token budget scenarios (under budget, over budget)

**Import Path:**
- `from db.legal_kb.models import LegalRuleSearchResult`
- `from db.reference_corpus.models import ReferenceClauseSearchResult`

---

### Task 6: Implement Test Suite
**File:** `backend/tests/test_merge_context.py`

**Setup:**
- Import test fixtures from `fixtures.merge_test_data`
- Import actual models: LegalRuleSearchResult, ReferenceClauseSearchResult (with REAL field names)
- Import merge functions from `app.rag.merge_context`
- Use pytest fixtures for test data

**Test Cases (15 total):**

**TC-1: Basic Merge - No Duplicates**
- Input: 3 legal rules + 3 corpus results, all unique text
- Verify: 6 ContextChunks returned
- Verify: Each chunk has correct source_type ("legal_rule" or "reference_corpus")
- Verify: Legal chunks have source_reference formatted as `"{act_name}, {section_reference}"` (with state suffix if present)
- Verify: Corpus chunks have source_reference = source_label
- Verify: Chunks sorted by similarity_score descending

**TC-2: Exact Duplicates - Same Text**
- Input: 2 legal rules with identical rule_text but different similarity scores (0.9, 0.8)
- Verify: 1 chunk returned (higher score 0.9 kept)
- Verify: Deduplication stats: total_input=2, duplicates_removed=1, final_count=1

**TC-3: Near Duplicates - Above Threshold**
- Input: 2 chunks with 96% text similarity (above 0.95 threshold)
- Verify: 1 chunk returned
- Verify: Higher similarity_score chunk kept

**TC-4: Priority When Scores Equal**
- Input: 1 legal rule + 1 corpus result with identical clause_text/rule_text and same similarity (0.9)
- Verify: 1 chunk returned
- Verify: Legal rule kept (source_type="legal_rule")

**TC-5: Near Duplicates - Below Threshold**
- Input: 2 chunks with 90% similarity (below 0.95 threshold)
- Verify: 2 chunks returned (not considered duplicates)

**TC-6: Empty Results from Both Sources**
- Input: empty legal_results list, empty corpus_results list
- Verify: MergeResult returned with empty chunks list
- Verify: No exceptions raised
- Verify: total_tokens=0

**TC-7: Single Source Only (Legal Rules)**
- Input: 5 legal rules, 0 corpus results
- Verify: All 5 chunks returned (all with source_type="legal_rule")
- Verify: No errors, no duplicates

**TC-8: Token Budget - Under Budget**
- Input: 3 chunks totaling ~500 tokens, MAX_CONTEXT_TOKENS=1000
- Verify: All 3 chunks returned
- Verify: total_tokens ≈ 500
- Verify: trimming_stats: before_trim=3, after_trim=3, tokens_saved=0

**TC-9: Token Budget - Over Budget (Trimming)**
- Input: 10 chunks totaling ~5000 tokens, MAX_CONTEXT_TOKENS=1000
- Mock tiktoken to return predictable token counts
- Verify: Fewer than 10 chunks returned
- Verify: total_tokens ≤ 1000
- Verify: Higher similarity_score chunks prioritized
- Verify: trimming_stats shows chunks trimmed

**TC-10: Token Budget - Minimum Chunks Enforced**
- Input: 1 legal rule (~800 tokens) + 1 corpus result (~800 tokens), MAX_CONTEXT_TOKENS=1000
- Verify: Both chunks returned (MIN_CHUNKS_PER_SOURCE=1 enforced)
- Verify: total_tokens may exceed 1000 (budget overrun allowed to meet minimum)
- Verify: Warning logged about exceeding budget for minimum

**TC-11: Source Tagging - Legal Rules**
- Input: LegalRuleSearchResult with state="MH", act_name="Maharashtra Rent Control Act 1999", section_reference="Section 11(2)", rule_text="...", similarity=0.9
- Verify: ContextChunk created with:
  - source_type="legal_rule"
  - source_reference="Maharashtra Rent Control Act 1999, Section 11(2) (MH)" (note state suffix)
  - text=rule_text (mapped correctly)
  - similarity_score=0.9 (mapped from similarity)
- Verify: format_for_prompt() returns `[Legal Rule: Maharashtra Rent Control Act 1999, Section 11(2) (MH)]\n{text}`

**TC-12: Source Tagging - Reference Corpus**
- Input: ReferenceClauseSearchResult with source_label="Standard practice", clause_text="...", similarity=0.88
- Verify: ContextChunk created with:
  - source_type="reference_corpus"
  - source_reference="Standard practice" (uses source_label directly)
  - text=clause_text (mapped correctly)
  - similarity_score=0.88
- Verify: format_for_prompt() returns `[Reference Example: Standard practice]\n{text}`

**TC-13: Format Merged Context for Prompt**
- Input: MergeResult with 3 chunks
- Call format_merged_context(merge_result)
- Verify: Returns string starting with "## Retrieved Context\n\n"
- Verify: Each chunk formatted via format_for_prompt()
- Verify: Chunks separated by "\n\n"
- Verify: Empty chunks case returns "No relevant context found."

**TC-14: Deduplication Stats Accuracy**
- Input: 10 chunks with 3 pairs of duplicates (above threshold)
- Verify: deduplication_stats["total_input"] = 10
- Verify: deduplication_stats["duplicates_removed"] = 3
- Verify: deduplication_stats["final_count"] = 7

**TC-15: Ordering Consistency**
- Input: Chunks with similarity scores [0.7, 0.95, 0.8, 0.9] (unsorted order)
- Verify: Output ordered by similarity_score: [0.95, 0.9, 0.8, 0.7]
- Verify: Order deterministic across multiple test runs

**Field Name Verification in Tests:**
- All test fixtures MUST use actual Stage 5A/5B field names:
  - LegalRuleSearchResult: `rule_text`, `similarity` (NOT clause_text, NOT similarity_score)
  - ReferenceClauseSearchResult: `clause_text`, `similarity` (NOT rule_text, NOT similarity_score)
- Test assertions verify correct mapping to ContextChunk fields (text, similarity_score)

---

## Verification Steps

After completing all tasks:

1. **Run pytest on merge tests:**
   ```bash
   cd backend
   pytest tests/test_merge_context.py -v
   ```
   Must show 15/15 passing.

2. **Verify field mapping correctness:**
   - Manually inspect a ContextChunk created from LegalRuleSearchResult
   - Confirm `rule_text` → `text`, `similarity` → `similarity_score`
   - Confirm citation format includes state when present

3. **Verify tiktoken installed:**
   ```bash
   cd backend
   python -c "import tiktoken; print(tiktoken.__version__)"
   ```

4. **Verify env variables documented:**
   ```bash
   grep -E "DEDUPLICATION_THRESHOLD|MAX_CONTEXT_TOKENS|MIN_CHUNKS_PER_SOURCE" backend/.env.example
   ```

5. **Check import paths compile:**
   ```bash
   cd backend
   python -c "from app.rag.merge_context import merge_retrieval_results; print('Imports OK')"
   ```

---

## File Summary

**New Files Created:**
1. `backend/app/rag/models.py` — ContextChunk, MergeResult Pydantic models
2. `backend/app/rag/merge_context.py` — Merge, deduplicate, trim logic
3. `backend/tests/fixtures/merge_test_data.py` — Test fixtures with real field names
4. `backend/tests/test_merge_context.py` — 15 test cases (TC-1 through TC-15)

**Modified Files:**
5. `backend/requirements.txt` — Add tiktoken>=0.5.0
6. `backend/.env.example` — Add DEDUPLICATION_THRESHOLD, MAX_CONTEXT_TOKENS, MIN_CHUNKS_PER_SOURCE
7. `backend/.env` — Add same variables with defaults (if .env exists and is tracked)

---

## Critical Notes

1. **Field Name Consistency:**
   - Source models use `similarity` (float)
   - Unified model uses `similarity_score` (float with validation)
   - Mapping is explicit in _convert_to_chunks() with code comments

2. **Text Field Normalization:**
   - Legal rules: `rule_text` → ContextChunk.text
   - Reference corpus: `clause_text` → ContextChunk.text
   - Both map to single normalized `text` field in ContextChunk

3. **Citation Format:**
   - Legal: `f"{act_name}, {section_reference}"` + state suffix if present
   - Corpus: Use `source_label` as-is
   - Format must match what Stage 8 (citation generation) expects

4. **Integration Point:**
   - Stage 7 (risk detection) will call `merge_retrieval_results()` after Stage 5A/5B searches
   - Output fed to `format_merged_context()` → single `retrieved_context` string for LLM prompt
   - Stage 3's build_risk_prompt() was reconciled to take ONE retrieved_context param (not separate legal/corpus)

5. **Deduplication Algorithm:**
   - Character 3-gram Jaccard index (fast, deterministic)
   - Not semantic similarity (no additional embeddings needed)
   - Threshold 0.95 targets near-exact duplicates only

6. **Token Budget:**
   - Enforced via tiktoken (OpenAI tokenizer)
   - MIN_CHUNKS_PER_SOURCE may cause budget overrun (acceptable, logged as warning)
   - Future: support Claude tokenizer if LLM_PROVIDER=claude

---

## Dependencies Check

Before starting:
- Stage 5A (Legal KB) complete: `db.legal_kb.models.LegalRuleSearchResult` exists with fields: id, state, act_name, section_reference, rule_text, **similarity**
- Stage 5B (Reference Corpus) complete: `db.reference_corpus.models.ReferenceClauseSearchResult` exists with fields: id, contract_type, clause_category, clause_text, source_label, **similarity**
- Both models confirmed via inspection (see conversation history)

---

## Success Criteria

- [ ] ContextChunk model created with correct field mappings documented
- [ ] MergeResult model created with stats dicts
- [ ] _convert_to_chunks() maps fields correctly (rule_text/clause_text → text, similarity → similarity_score)
- [ ] _deduplicate_chunks() uses Jaccard similarity with 0.95 threshold
- [ ] _trim_to_budget() enforces MAX_CONTEXT_TOKENS and MIN_CHUNKS_PER_SOURCE
- [ ] merge_retrieval_results() orchestrates all steps, returns MergeResult
- [ ] format_merged_context() produces prompt-ready string
- [ ] tiktoken added to requirements.txt
- [ ] Environment variables added to .env.example with defaults
- [ ] Test fixtures use REAL field names from Stage 5A/5B models
- [ ] All 15 test cases pass (pytest tests/test_merge_context.py -v)
- [ ] Legal rule priority works (source_type="legal_rule" preferred on equal scores)
- [ ] State suffix added to legal citations when present
- [ ] Empty results handled gracefully (no exceptions)
- [ ] Token budget overrun logged as warning when MIN_CHUNKS_PER_SOURCE enforced

---

## Commit Strategy

Use Conventional Commits:
- `feat(rag): add merge context models (ContextChunk, MergeResult)` — Task 1
- `feat(rag): implement merge_retrieval_results with deduplication` — Task 2
- `chore(config): add merge context env vars (dedup threshold, token budget)` — Task 3
- `chore(deps): add tiktoken for token counting` — Task 4
- `test(rag): add merge context test fixtures with real field names` — Task 5
- `test(rag): add 15 merge context test cases (TC-1 to TC-15)` — Task 6
