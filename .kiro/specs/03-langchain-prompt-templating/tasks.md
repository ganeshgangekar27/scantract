# Tasks: Prompt Templating Implementation (Stage 3)

## Overview
Implement LangChain prompt templating layer for ScanTract with file-based templates, lazy loading, placeholder validation, and compliance instructions.

**Cross-Spec Reconciliation**: `build_risk_prompt()` signature changed from separate `legal_context`/`corpus_context` parameters to single `retrieved_context` parameter for consistency with Stage 6 merge output. See `design.md` for rationale.

---

## Task 1: Create Directory Structure
**File**: `backend/rag/prompts/`

**Actions**:
- Create `backend/rag/` directory if it doesn't exist
- Create `backend/rag/prompts/` subdirectory
- Create `backend/rag/prompts/.gitkeep` to ensure directory is tracked
- Create `backend/rag/__init__.py` (empty or with module docstring)

**Acceptance Criteria**:
- Directory exists at `backend/rag/prompts/`
- Directory is tracked in git
- No template files yet (created in Tasks 2-3)

---

## Task 2: Write Clause Classification Template
**File**: `backend/rag/prompts/clause_classification.txt`

**Actions**:
- Create template file with these exact variable placeholders:
  - `{clause_text}` - The clause content to classify
  - `{clause_index}` - Clause identifier (e.g., "1.1", "para_5")
  - `{contract_type}` - "rental" or "freelance"
  - `{retrieved_context}` - RAG-retrieved context from Stage 5A/5B

**Required Content**:
1. **System Instructions Section**:
   - Clear role definition: "You are analyzing a contract clause"
   - Input structure explanation
   - Output format requirements (JSON schema)

2. **Compliance Instructions** (verbatim from FR-5):
   - "Never provide legal advice or use imperative language like 'you should' or 'you must'"
   - "Always cite which legal rule or reference clause triggered this classification"
   - "Use descriptive language: 'this clause differs from standard practice because...'"
   - "Assign confidence scores based on textual evidence, not assumptions"

3. **Task Description**:
   - "Classify this clause from a {contract_type} contract"
   - "Consider the retrieved context below when making your determination"

4. **Context Section**:
   - Header: "## Retrieved Context"
   - Placeholder: `{retrieved_context}`

5. **Clause to Classify**:
   - Header: "## Clause to Classify"
   - "Clause {clause_index}:"
   - Placeholder: `{clause_text}`

6. **Output Format Specification**:
   - JSON structure with: clause_type, key_entities, confidence
   - Explicit instruction: "Respond with ONLY valid JSON, no preamble"

**Acceptance Criteria**:
- All 4 placeholders present: `{clause_text}`, `{clause_index}`, `{contract_type}`, `{retrieved_context}`
- All FR-5 compliance instructions included verbatim
- Clear JSON output schema specified
- Template is valid UTF-8 text file

---

## Task 3: Write Risk Detection Template
**File**: `backend/rag/prompts/risk_detection.txt`

**Actions**:
- Create template file with these exact variable placeholders:
  - `{clauses_list}` - Full list of classified clauses (formatted as text)
  - `{retrieved_context}` - **Single merged context** from Stage 6 (reconciled parameter)
  - `{contract_type}` - "rental" or "freelance"

**Required Content**:
1. **System Instructions Section**:
   - Clear role: "You are analyzing a complete contract for risks and missing clauses"
   - Input structure explanation
   - Output format requirements (JSON with risky_clauses and missing_clauses arrays)

2. **Compliance Instructions** (verbatim from FR-5):
   - "Never provide legal advice or use imperative language like 'you should' or 'you must'"
   - "CRITICAL: Every finding MUST include 'triggering_rule_or_corpus' field with exact citation from context"
   - "Use descriptive comparisons: 'this clause differs from X because Y'"
   - "Assign severity (low/medium/high) based on legal impact and standard practice deviation"
   - "Be factual and educational, not prescriptive"

3. **Task Description**:
   - "Analyze this {contract_type} contract for risky and missing clauses"
   - "Cross-reference each clause with the legal rules and reference examples below"

4. **Context Section**:
   - Header: "## Retrieved Context"
   - Subheader: "Legal Rules and Reference Examples:"
   - Placeholder: `{retrieved_context}`

5. **Contract Clauses Section**:
   - Header: "## Contract Clauses"
   - Placeholder: `{clauses_list}`

6. **Output Format Specification**:
   - JSON structure with `risky_clauses` and `missing_clauses` arrays
   - Each risky clause: clause_id, reason, triggering_rule_or_corpus, severity
   - Each missing clause: expected_clause_type, why_expected, triggering_rule_or_corpus, severity
   - Explicit instruction: "Respond with ONLY valid JSON. No markdown, no preamble."
   - Emphasis: "triggering_rule_or_corpus is MANDATORY and must reference specific context above"

**Acceptance Criteria**:
- All 3 placeholders present: `{clauses_list}`, `{retrieved_context}`, `{contract_type}`
- Note: `{retrieved_context}` (singular) not separate legal/corpus contexts (reconciled design)
- All FR-5 compliance instructions included
- Extra emphasis on mandatory traceability field
- Clear JSON schema with both risky_clauses and missing_clauses arrays
- Template is valid UTF-8 text file

---

## Task 4: Implement Prompt Builder Module Structure
**File**: `backend/app/rag/prompt_builder.py`

**Actions**:
- Create file with module docstring explaining purpose
- Add imports:
  ```python
  from pathlib import Path
  from typing import Any
  import logging
  ```
- Define module-level constants:
  - `PROMPTS_DIR = Path(__file__).parent.parent.parent / "rag" / "prompts"`
  - `_template_cache: dict[str, str] = {}` (for lazy loading)
- Add logger setup: `logger = logging.getLogger(__name__)`

**Acceptance Criteria**:
- File created at `backend/app/rag/prompt_builder.py`
- Module docstring present
- Constants defined
- Cache dictionary initialized
- Imports present and correct

---

## Task 5: Implement Template Loading and Caching
**File**: `backend/app/rag/prompt_builder.py` (continued)

**Actions**:
- Implement `_load_template(template_name: str) -> str` function:
  - Check if template in `_template_cache`, return if cached
  - Construct file path: `PROMPTS_DIR / f"{template_name}.txt"`
  - Verify file exists, raise `FileNotFoundError` with clear message if not
  - Read file contents as UTF-8
  - Store in `_template_cache[template_name]`
  - Log cache miss and successful load
  - Return template string

**Acceptance Criteria**:
- Function signature: `_load_template(template_name: str) -> str`
- Uses module-level cache (`_template_cache`)
- Lazy loading (only reads file on first call)
- Raises `FileNotFoundError` with message including expected file path
- Logs cache misses and loads at INFO level
- Returns template as string

---

## Task 6: Implement build_classification_prompt()
**File**: `backend/app/rag/prompt_builder.py` (continued)

**Actions**:
- Implement function signature:
  ```python
  def build_classification_prompt(
      clause_text: str,
      clause_index: str,
      contract_type: str,
      retrieved_context: str
  ) -> list[dict[str, str]]:
  ```

- Load template: `template = _load_template("clause_classification")`
- Perform variable substitution:
  - Replace `{clause_text}` with provided value
  - Replace `{clause_index}` with provided value
  - Replace `{contract_type}` with provided value
  - Replace `{retrieved_context}` with provided value
- Validate no placeholders remain (call validation function from Task 7)
- Return LangChain-compatible message array:
  ```python
  return [{"role": "user", "content": filled_template}]
  ```

**Acceptance Criteria**:
- Function signature matches specification exactly
- All 4 parameters are required (no defaults)
- Uses `_load_template()` to get template
- Substitutes all 4 variables
- Calls placeholder validation before returning
- Returns `list[dict[str, str]]` in LangChain message format
- Includes type hints for all parameters and return type

---

## Task 7: Implement build_risk_prompt()
**File**: `backend/app/rag/prompt_builder.py` (continued)

**Actions**:
- Implement function signature (reconciled per design.md):
  ```python
  def build_risk_prompt(
      clauses_list: list[dict[str, Any]],
      retrieved_context: str,  # Single merged context (reconciled)
      contract_type: str
  ) -> list[dict[str, str]]:
  ```

- Format `clauses_list` into human-readable text:
  - Iterate over clause dicts (expecting: clause_id, clause_type, clause_text)
  - Format as: "Clause {clause_id} ({clause_type}): {clause_text}"
  - Join with double newlines
- Load template: `template = _load_template("risk_detection")`
- Perform variable substitution:
  - Replace `{clauses_list}` with formatted clauses text
  - Replace `{retrieved_context}` with provided value (already merged by Stage 6)
  - Replace `{contract_type}` with provided value
- Validate no placeholders remain (call validation function)
- Return LangChain-compatible message array:
  ```python
  return [{"role": "user", "content": filled_template}]
  ```

**Acceptance Criteria**:
- Function signature uses `retrieved_context` (singular, reconciled parameter)
- Formats `clauses_list` into readable text format
- All 3 variables substituted correctly
- Calls placeholder validation before returning
- Returns `list[dict[str, str]]` in LangChain message format
- Includes type hints for all parameters and return type
- Includes docstring explaining reconciliation (references design.md)

---

## Task 8: Implement Placeholder Validation
**File**: `backend/app/rag/prompt_builder.py` (continued)

**Actions**:
- Implement `_validate_no_placeholders(prompt: str, template_name: str) -> None` function:
  - Use regex to find remaining `{...}` patterns: `r'\{([^}]+)\}'`
  - If any matches found:
    - Extract placeholder names from matches
    - Raise `ValueError` with message:
      - "Unfilled placeholders in {template_name} template: {list of placeholders}"
      - "This indicates missing required variables"
  - If no matches, return silently (validation passed)
  - Log validation pass at DEBUG level

**Acceptance Criteria**:
- Function signature: `_validate_no_placeholders(prompt: str, template_name: str) -> None`
- Uses regex to detect `{variable}` patterns
- Raises `ValueError` with clear message listing unfilled placeholders
- Error message includes template name for debugging
- Does not raise error if all placeholders filled
- Logs successful validation at DEBUG level

---

## Task 9: Write Unit Tests - Template Loading
**File**: `backend/tests/test_prompt_builder.py`

**Actions**:
- Create test file with imports and fixtures
- Test: `test_load_template_clause_classification()`
  - Call `_load_template("clause_classification")`
  - Assert returns string
  - Assert contains all 4 placeholders: `{clause_text}`, `{clause_index}`, `{contract_type}`, `{retrieved_context}`
  - Assert contains FR-5 compliance instructions (check for keywords: "never provide legal advice", "always cite")

- Test: `test_load_template_risk_detection()`
  - Call `_load_template("risk_detection")`
  - Assert returns string
  - Assert contains all 3 placeholders: `{clauses_list}`, `{retrieved_context}`, `{contract_type}`
  - Assert contains FR-5 compliance instructions
  - Assert contains "triggering_rule_or_corpus" in output schema

- Test: `test_template_caching()`
  - Clear cache: `_template_cache.clear()`
  - Call `_load_template("clause_classification")` twice
  - Mock file read to count calls
  - Assert file read only once (second call uses cache)

- Test: `test_load_template_not_found()`
  - Call `_load_template("nonexistent")`
  - Assert raises `FileNotFoundError`
  - Assert error message includes expected file path

**Acceptance Criteria**:
- All 4 tests pass
- Tests verify template structure (placeholders present)
- Tests verify compliance instructions present
- Tests verify caching works (no redundant file I/O)
- Tests verify error handling for missing files

---

## Task 10: Write Unit Tests - Classification Prompt
**File**: `backend/tests/test_prompt_builder.py` (continued)

**Actions**:
- Test: `test_build_classification_prompt_all_variables()`
  - Call with all 4 parameters provided:
    - `clause_text="Test clause text"`
    - `clause_index="1.1"`
    - `contract_type="rental"`
    - `retrieved_context="Legal rule: Model Tenancy Act"`
  - Assert returns list with one dict
  - Assert dict has keys "role" and "content"
  - Assert "role" == "user"
  - Assert "content" contains all 4 provided values
  - Assert no `{...}` placeholders remain in content

- Test: `test_build_classification_prompt_no_placeholders()`
  - Call with valid parameters
  - Extract content string
  - Use regex to check for any `{variable}` patterns
  - Assert no matches (all placeholders filled)

- Test: `test_build_classification_prompt_empty_context()`
  - Call with `retrieved_context=""` (empty string)
  - Assert function succeeds (empty context is valid)
  - Assert returned prompt contains empty context section

**Acceptance Criteria**:
- All 3 tests pass
- Tests verify all variables substituted correctly
- Tests verify no unfilled placeholders
- Tests verify LangChain message format (list of dicts)
- Tests verify empty context handled gracefully

---

## Task 11: Write Unit Tests - Risk Prompt
**File**: `backend/tests/test_prompt_builder.py` (continued)

**Actions**:
- Test: `test_build_risk_prompt_all_variables()`
  - Call with all 3 parameters:
    - `clauses_list=[{"clause_id": "1", "clause_type": "payment", "clause_text": "Test"}]`
    - `retrieved_context="Merged context from Stage 6"`
    - `contract_type="rental"`
  - Assert returns list with one dict
  - Assert dict has "role" == "user" and "content" key
  - Assert content contains formatted clause
  - Assert content contains retrieved context
  - Assert content contains contract type
  - Assert no `{...}` placeholders remain

- Test: `test_build_risk_prompt_multiple_clauses()`
  - Call with 3 clauses in `clauses_list`
  - Extract content
  - Assert all 3 clauses present in formatted output
  - Assert clauses separated by newlines

- Test: `test_build_risk_prompt_reconciled_parameter()`
  - Verify function accepts single `retrieved_context` parameter (not separate legal/corpus)
  - Call with merged context string
  - Assert function succeeds
  - Assert merged context appears in final prompt
  - Comment in test referencing design.md reconciliation

**Acceptance Criteria**:
- All 3 tests pass
- Tests verify reconciled `retrieved_context` parameter (singular)
- Tests verify clause list formatting works
- Tests verify multiple clauses handled correctly
- Tests verify no unfilled placeholders
- Test comments reference design.md for reconciliation rationale

---

## Task 12: Write Unit Tests - Validation
**File**: `backend/tests/test_prompt_builder.py` (continued)

**Actions**:
- Test: `test_validate_no_placeholders_success()`
  - Create test string with no `{...}` patterns
  - Call `_validate_no_placeholders(test_string, "test_template")`
  - Assert no exception raised

- Test: `test_validate_no_placeholders_failure()`
  - Create test string with unfilled placeholder: "Text with {unfilled_var}"
  - Call `_validate_no_placeholders(test_string, "test_template")`
  - Assert raises `ValueError`
  - Assert error message contains "unfilled_var"
  - Assert error message contains "test_template"

- Test: `test_validate_multiple_placeholders()`
  - Create string with multiple unfilled: "Text {var1} and {var2}"
  - Call validation
  - Assert raises `ValueError`
  - Assert error message lists both "var1" and "var2"

- Test: `test_escaped_braces()`
  - Create string with escaped braces: "Literal {{braces}}"
  - Call validation
  - Assert no exception (escaped braces should not trigger validation)

**Acceptance Criteria**:
- All 4 tests pass
- Tests verify validation catches unfilled placeholders
- Tests verify validation allows valid prompts
- Tests verify error messages are clear and helpful
- Tests verify multiple unfilled placeholders reported
- Tests verify escaped braces ({{, }}) don't trigger false positives

---

## Task 13: Write Integration Test
**File**: `backend/tests/test_prompt_builder.py` (continued)

**Actions**:
- Test: `test_full_classification_flow()`
  - Ensure template files exist (skip if not)
  - Call `build_classification_prompt()` with realistic data
  - Assert returns valid message array
  - Assert content is well-formed
  - Assert all compliance instructions present in final prompt
  - Log prompt to verify human readability (optional, debug only)

- Test: `test_full_risk_detection_flow()`
  - Ensure template files exist
  - Call `build_risk_prompt()` with realistic multi-clause data
  - Assert returns valid message array
  - Assert JSON schema instructions present
  - Assert traceability emphasis present ("triggering_rule_or_corpus")
  - Assert reconciled parameter works (single context)

**Acceptance Criteria**:
- Both integration tests pass
- Tests use realistic data (multiple clauses, actual context text)
- Tests verify end-to-end prompt assembly
- Tests verify compliance instructions make it to final prompt
- Tests verify LangChain message format compatibility

---

## Task 14: Add Module Documentation
**File**: `backend/app/rag/prompt_builder.py` (continued)

**Actions**:
- Add comprehensive module docstring at top:
  - Purpose: "LangChain prompt template loading and assembly for ScanTract"
  - Usage examples for both functions
  - Note about lazy loading and caching
  - Reference to template files location
- Add docstrings to all functions:
  - `_load_template()`: Explain caching behavior
  - `build_classification_prompt()`: Explain parameters and return format
  - `build_risk_prompt()`: Explain reconciled parameter design, reference design.md
  - `_validate_no_placeholders()`: Explain validation logic
- Add inline comments for complex logic (e.g., clause list formatting)

**Acceptance Criteria**:
- Module docstring present and complete
- All functions have docstrings with Args, Returns, Raises sections
- `build_risk_prompt()` docstring references design.md for reconciliation
- Inline comments explain non-obvious code
- Docstrings follow Google or NumPy style (consistent with project)

---

## Task 15: Update Requirements
**File**: `backend/requirements.txt`

**Actions**:
- Add LangChain dependency if not already present:
  ```
  langchain>=0.1.0
  ```
- Verify no other new dependencies needed for this stage
- Update comments to note LangChain is used for prompt templates

**Acceptance Criteria**:
- `langchain>=0.1.0` in requirements.txt
- File is properly formatted
- Comments clear about LangChain usage

---

## Verification Checklist

Before marking Stage 3 complete, verify:

- [ ] Template directory exists: `backend/rag/prompts/`
- [ ] Template files created:
  - [ ] `clause_classification.txt` with 4 placeholders
  - [ ] `risk_detection.txt` with 3 placeholders (reconciled)
- [ ] Both templates include FR-5 compliance instructions
- [ ] `prompt_builder.py` implements both build functions
- [ ] Lazy loading with caching implemented
- [ ] Placeholder validation implemented
- [ ] All 15+ unit tests pass
- [ ] Integration tests verify end-to-end flow
- [ ] Documentation complete (module + function docstrings)
- [ ] design.md documents reconciliation decision
- [ ] No `{variable}` placeholders can slip through to LLM

---

## Dependencies

**Upstream (must be complete before starting)**:
- None (Stage 3 is foundational, only depends on directory structure)

**Downstream (blocks these stages)**:
- Stage 4 (Clause Classification): Uses `build_classification_prompt()`
- Stage 7 (Risk Detection): Uses `build_risk_prompt()`

**Critical Notes**:
- The `retrieved_context` parameter reconciliation affects Stage 7 integration
- Stage 6 must provide merged context (not separate legal/corpus)
- Stage 7 must call with single `retrieved_context` parameter
- All downstream specs already use reconciled signature (verified in review)
