# Stage 7: Risk & Missing Clause Detection — Implementation Tasks

## Overview
Implement Stage 7 (Risk Detection) of ScanTract: analyze classified clauses with merged context from Stage 6, identify risky clauses and missing clauses, assign severity scores, ensure every finding is traceable to a specific legal rule or reference example, and persist findings to database.

## Critical Corrections (Based on Actual Implementation)

**LLM Provider:**
- Use existing `call_llm()` from `backend/app/llm/llm_client.py` (already supports Claude, OpenAI, Gemini)
- Provider selected via `LLM_PROVIDER` env var (currently set to "gemini")
- Do NOT hardcode provider - abstraction handles routing automatically

**Context Input:**
- Stage 6's `format_merged_context()` produces **ONE** formatted string (not separate legal/corpus strings)
- `build_risk_prompt()` signature confirmed: `build_risk_prompt(clauses_list, retrieved_context, contract_type)`
- Parameter name is `retrieved_context` (not `legal_context` or separate params)

**Search Function Signatures (Confirmed):**
- `search_legal_rules(clause_text, db, state=None, contract_type=None, top_k=5, similarity_threshold=0.7)`
- `search_reference_corpus(clause_text, contract_type, db, top_k=5, similarity_threshold=0.7)`
- Note: `db` position differs between functions (2nd for legal, 3rd for corpus)

**Most Recent Migration:**
- Chain from: `004_create_reference_clauses` (revision ID: `'004_create_reference_clauses'`)
- Down revision: `'3b2943032b28'`

**Traceability Requirement (NON-NEGOTIABLE):**
- Every `risky_clause` and `missing_clause` finding MUST have non-empty `triggering_rule_or_corpus`
- Pydantic validator MUST reject empty strings or whitespace-only
- Retry logic MUST emphasize this requirement if validation fails
- If all retries fail: raise RuntimeError, do NOT save untraceable findings

---

## Tasks

### Task 1: Extend LLM Models with Risk Detection Types
**File:** `backend/app/llm/models.py`

**Requirements:**
- Add `Severity` enum: `LOW = "low"`, `MEDIUM = "medium"`, `HIGH = "high"`

- Add `RiskyClauseFinding` Pydantic model:
  - `clause_id: str`
  - `reason: str` with `min_length=10`
  - `triggering_rule_or_corpus: str` with `min_length=1` and custom `@field_validator`
  - `severity: Severity`
  - **Validator MUST reject empty/whitespace-only strings with clear error message**

- Add `MissingClauseFinding` Pydantic model:
  - `expected_clause_type: str`
  - `why_expected: str` with `min_length=10`
  - `triggering_rule_or_corpus: str` with `min_length=1` and custom `@field_validator`
  - `severity: Severity`
  - **Validator MUST reject empty/whitespace-only strings with clear error message**

- Add `RiskDetectionResponse` Pydantic model:
  - `risky_clauses: list[RiskyClauseFinding]` with `default_factory=list`
  - `missing_clauses: list[MissingClauseFinding]` with `default_factory=list`

- Add `RiskDetectionResult` Pydantic model:
  - `contract_id: str`
  - `risky_clauses: list[RiskyClauseFinding]`
  - `missing_clauses: list[MissingClauseFinding]`
  - `total_risks: int`
  - `total_missing: int`
  - `high_severity_count: int`
  - `medium_severity_count: int`
  - `low_severity_count: int`
  - `processed_at: str` (ISO timestamp)
  - `summary() -> str` method returning human-readable summary

**Validation Examples:**
```python
# MUST REJECT:
{"triggering_rule_or_corpus": ""}
{"triggering_rule_or_corpus": "   "}
{"triggering_rule_or_corpus": None}  # if field present but null

# MUST ACCEPT:
{"triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 7(1)"}
{"triggering_rule_or_corpus": "Standard practice - fair deposit terms"}
```

---

### Task 2: Create Alembic Migration for risk_findings Table
**File:** `backend/alembic/versions/005_create_risk_findings.py`

**Migration Details:**
- Revision ID: `'005_create_risk_findings'`
- Down revision: `'004_create_reference_clauses'`
- Create date: Use current timestamp

**Table Schema:**
```sql
CREATE TABLE risk_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    finding_type VARCHAR(20) NOT NULL,
    
    -- For risky clauses
    clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,
    
    -- For missing clauses  
    expected_clause_type VARCHAR(100),
    
    -- Common fields
    reason TEXT NOT NULL,
    triggering_rule_or_corpus TEXT NOT NULL,  -- MANDATORY
    severity VARCHAR(10) NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT valid_finding_type CHECK (finding_type IN ('risky_clause', 'missing_clause')),
    CONSTRAINT valid_severity CHECK (severity IN ('low', 'medium', 'high')),
    CONSTRAINT risky_clause_has_id CHECK (
        finding_type = 'missing_clause' OR clause_id IS NOT NULL
    ),
    CONSTRAINT missing_clause_has_type CHECK (
        finding_type = 'risky_clause' OR expected_clause_type IS NOT NULL
    )
)
```

**Indexes:**
```sql
CREATE INDEX idx_risk_findings_contract ON risk_findings(contract_id);
CREATE INDEX idx_risk_findings_severity ON risk_findings(severity);
CREATE INDEX idx_risk_findings_type ON risk_findings(finding_type);
CREATE INDEX idx_risk_findings_clause ON risk_findings(clause_id) WHERE clause_id IS NOT NULL;
```

**Downgrade:** `DROP TABLE IF EXISTS risk_findings`

---

### Task 3: Implement Core Risk Detection Logic
**File:** `backend/app/llm/detect_risk.py`

**Functions to Implement:**

**3.1: `async def detect_risks(contract_id: str, db: AsyncSession) -> RiskDetectionResult`**
- Main orchestration function
- Steps:
  1. Load contract via `_load_contract()` - validate status is "completed"
  2. Load clauses via `_load_clauses()` - only classified clauses (clause_type NOT NULL)
  3. If no clauses: return `_empty_result(contract_id)`
  4. Retrieve merged context via `_retrieve_merged_context_for_contract()`
  5. Build prompt via `build_risk_prompt(clauses_list, retrieved_context, contract_type)`
  6. Call LLM via `_call_llm_with_traceability_validation()`
  7. Persist via `_persist_findings()`
  8. Build result via `_build_result()`
  9. Return RiskDetectionResult

**3.2: `async def _load_contract(contract_id: str, db: AsyncSession) -> Contract`**
- Query contracts table for given contract_id
- Raise ValueError if not found
- Raise ValueError if processing_status != "completed"
- Return Contract object

**3.3: `async def _load_clauses(contract_id: str, db: AsyncSession) -> list[Clause]`**
- Query clauses table WHERE contract_id matches AND clause_type IS NOT NULL
- Order by position
- Return list of Clause objects

**3.4: `async def _retrieve_merged_context_for_contract(clauses, contract_type, state, db) -> str`**
- Loop through first 10 clauses (cap to avoid excessive API calls)
- For each clause:
  - Call `await search_legal_rules(clause_text=clause.clause_text, db=db, state=state, top_k=3)`
  - Call `await search_reference_corpus(clause_text=clause.clause_text, contract_type=contract_type, db=db, top_k=3)`
  - Append results to `all_legal_results` and `all_corpus_results` lists
- After loop:
  - Call `merge_result = merge_retrieval_results(all_legal_results, all_corpus_results)`
  - Call `return format_merged_context(merge_result)`
- Import from: `app.rag.merge_context import merge_retrieval_results, format_merged_context`
- Import from: `db.legal_kb.search import search_legal_rules`
- Import from: `db.reference_corpus.search import search_reference_corpus`

**3.5: `async def _call_llm_with_traceability_validation(messages, max_retries=2) -> RiskDetectionResponse`**
- Loop for max_retries attempts:
  - Call `response_text, tokens = await call_llm(messages)`
  - Parse JSON via `_parse_risk_response(response_text)`
  - Validate via `validated = RiskDetectionResponse(**parsed)`
  - Additional paranoid check via `_validate_all_findings_traceable(validated)`
  - If successful: return validated
  - On `json.JSONDecodeError`: log warning, add emphatic JSON instruction via `_add_emphatic_json_instruction()`, retry
  - On `ValueError` with "triggering_rule_or_corpus" in message: log TRACEABILITY VIOLATION error, add emphasis via `_add_traceability_emphasis()`, retry
  - On other exceptions: log error, re-raise if last attempt
- After all retries: raise RuntimeError with clear message about traceability violation

**3.6: `def _validate_all_findings_traceable(response: RiskDetectionResponse) -> None`**
- Loop through `response.risky_clauses`: check `triggering_rule_or_corpus` not empty/whitespace
- Loop through `response.missing_clauses`: check `triggering_rule_or_corpus` not empty/whitespace
- Raise ValueError with specific clause/type if validation fails
- Log debug message if all pass

**3.7: `def _add_traceability_emphasis(messages: list[dict]) -> list[dict]`**
- Append emphatic message to last user message:
  ```
  \n\n🚨 CRITICAL REQUIREMENT: Every finding MUST include 'triggering_rule_or_corpus' with the EXACT citation from the context above. Examples:\n- 'Model Tenancy Act 2021, Section 7(1)'\n- 'Standard practice - fair deposit terms'\n\nFindings without this field will be REJECTED. Copy the citation verbatim from the context.
  ```
- Return modified messages list

**3.8: `def _add_emphatic_json_instruction(messages: list[dict]) -> list[dict]`**
- Prepend to first user message:
  ```
  CRITICAL: Respond with ONLY valid JSON. No preamble, no markdown, no explanation. Just the JSON object.\n\n
  ```
- Return modified messages list

**3.9: `def _parse_risk_response(content: str) -> dict`**
- Strip markdown: `re.sub(r'^```json\s*', '', content)`
- Strip markdown: `re.sub(r'\s*```$', '', content)`
- Strip whitespace
- Parse via `json.loads(content)`
- Return dict

**3.10: `async def _persist_findings(contract_id, response, clauses, db) -> None`**
- Build clause_map: `{clause.clause_number: clause.id for clause in clauses}`
- Delete existing findings: `await db.execute(delete(RiskFinding).where(RiskFinding.contract_id == contract_id))`
- For each `risky` in `response.risky_clauses`:
  - Lookup `clause_uuid = clause_map.get(risky.clause_id)`
  - If not found: log warning, skip
  - Create RiskFinding with finding_type="risky_clause", clause_id=clause_uuid
  - Add to session
- For each `missing` in `response.missing_clauses`:
  - Create RiskFinding with finding_type="missing_clause", expected_clause_type=missing.expected_clause_type
  - Add to session
- Commit transaction

**3.11: `def _build_result(contract_id, response) -> RiskDetectionResult`**
- Count high/medium/low severities across both risky_clauses and missing_clauses
- Return RiskDetectionResult with all counts and timestamp

**3.12: `def _empty_result(contract_id) -> RiskDetectionResult`**
- Return RiskDetectionResult with all zeros and empty lists

**Imports Required:**
```python
import json
import re
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .llm_client import call_llm
from .models import RiskDetectionResponse, RiskDetectionResult, Severity
from app.rag.merge_context import merge_retrieval_results, format_merged_context
from app.rag.prompt_builder import build_risk_prompt
from db.legal_kb.search import search_legal_rules
from db.reference_corpus.search import search_reference_corpus
```

---

### Task 4: Extend Database Models with RiskFinding
**File:** `backend/app/db/models.py`

**Requirements:**
- Add `RiskFinding` SQLAlchemy model:
  - Table name: `"risk_findings"`
  - Columns matching migration schema (Task 2)
  - Relationships: `contract` (back_populates), `clause` (foreign_keys=[clause_id])
  - `__table_args__` with CHECK constraints matching migration

- Update `Contract` model:
  - Add relationship: `risk_findings = relationship("RiskFinding", back_populates="contract", cascade="all, delete-orphan")`

**Note:** Confirm existing `Contract` and `Clause` models exist in this file before adding relationships

---

### Task 5: Create Mock Risk Responses
**File:** `backend/tests/mocks/mock_risk_responses.py`

**Requirements:**
- Create 3 predefined mock responses as module-level constants:

**5.1: `VALID_RISK_RESPONSE` (dict)**
- Contains 2 risky_clauses, 1 missing_clause
- All have properly populated `triggering_rule_or_corpus` fields
- Mix of severity levels (high, medium, low)
- Valid JSON structure matching RiskDetectionResponse schema

**5.2: `MISSING_TRACEABILITY_RESPONSE` (dict)**
- Contains 1 risky_clause with `triggering_rule_or_corpus` field missing entirely OR empty string
- Purpose: Test traceability validation rejection

**5.3: `MALFORMED_JSON_RESPONSE` (str)**
- Invalid JSON string (e.g., missing closing brace, extra comma)
- Purpose: Test JSON parsing error handling

**5.4: `MARKDOWN_WRAPPED_RESPONSE` (str)**
- Valid JSON but wrapped in markdown code fence: ` ```json\n{...}\n``` `
- Purpose: Test markdown stripping

---

### Task 6: Implement Test Suite
**File:** `backend/tests/test_detect_risk.py`

**Setup:**
- Import `MockLLMClient` from `tests.mocks.mock_llm` (already exists from Stage 4)
- Import mock responses from `tests.mocks.mock_risk_responses`
- Use `pytest_asyncio` fixtures for database session
- Mock `call_llm()` to return predefined responses (no real API calls)

**Test Cases (18 total):**

**TC-1: test_full_detection_valid_response**
- Mock contract with 5 classified clauses
- Mock `call_llm` returns `VALID_RISK_RESPONSE`
- Call `detect_risks(contract_id, db)`
- Verify: RiskDetectionResult returned
- Verify: 2 risky + 1 missing = 3 total findings
- Verify: Severity counts correct
- Verify: 3 rows in risk_findings table

**TC-2: test_traceability_validation_missing_field_risky**
- Mock `call_llm` returns `MISSING_TRACEABILITY_RESPONSE` on first call
- Mock `call_llm` returns `VALID_RISK_RESPONSE` on retry
- Verify: First call rejected (ValueError or ValidationError)
- Verify: Retry triggered
- Verify: Second call accepted

**TC-3: test_traceability_validation_missing_field_missing_clause**
- Similar to TC-2 but with missing clause lacking traceability
- Verify retry logic works for missing_clauses too

**TC-4: test_traceability_validation_empty_string**
- Mock response with `triggering_rule_or_corpus = ""`
- Verify: Pydantic validator rejects with clear error message
- Verify: Retry triggered

**TC-5: test_traceability_validation_all_retries_fail**
- Mock `call_llm` returns untraceable response on ALL attempts (max_retries=2)
- Verify: RuntimeError raised
- Verify: Error message contains "traceability"
- Verify: No findings persisted to database

**TC-6: test_malformed_json_first_attempt**
- Mock `call_llm` returns `MARKDOWN_WRAPPED_RESPONSE`
- Verify: Markdown stripped successfully
- Verify: JSON parsed correctly

**TC-7: test_malformed_json_retry**
- Mock `call_llm` returns `MALFORMED_JSON_RESPONSE` on first call
- Mock `call_llm` returns valid JSON on retry
- Verify: Emphatic JSON instruction added
- Verify: Retry successful

**TC-8: test_empty_results_no_risks_found**
- Mock `call_llm` returns `{"risky_clauses": [], "missing_clauses": []}`
- Verify: Result shows total_risks=0, total_missing=0
- Verify: No database rows created

**TC-9: test_severity_scoring**
- Mock response with 2 high, 3 medium, 1 low severity findings
- Verify: high_severity_count=2, medium_severity_count=3, low_severity_count=1

**TC-10: test_invalid_clause_id_reference**
- Mock response references `clause_id="99"` which doesn't exist
- Verify: Warning logged
- Verify: That finding skipped (not persisted)
- Verify: Other valid findings still persisted

**TC-11: test_database_persistence_risky_clauses**
- Mock 2 risky clause findings
- Verify: 2 rows with finding_type='risky_clause'
- Verify: clause_id populated correctly (UUID match)
- Verify: expected_clause_type is NULL

**TC-12: test_database_persistence_missing_clauses**
- Mock 2 missing clause findings
- Verify: 2 rows with finding_type='missing_clause'
- Verify: expected_clause_type populated
- Verify: clause_id is NULL

**TC-13: test_database_persistence_idempotent_reruns**
- Run `detect_risks()` twice with same contract_id
- Verify: Old findings deleted before new ones inserted
- Verify: Only latest findings remain in database

**TC-14: test_merged_context_retrieval**
- Mock contract with clauses
- Mock `search_legal_rules` and `search_reference_corpus` return values
- Verify: Both functions called for each clause (up to 10)
- Verify: `merge_retrieval_results()` called with aggregated results
- Verify: `format_merged_context()` called
- Verify: Result passed to `build_risk_prompt()` as `retrieved_context` parameter

**TC-15: test_contract_not_found_error**
- Call `detect_risks(contract_id="nonexistent", db)`
- Verify: ValueError raised with "not found" message

**TC-16: test_contract_not_processed_error**
- Mock contract with processing_status="pending"
- Verify: ValueError raised with "not ready" message

**TC-17: test_no_clauses_to_analyze_empty_result**
- Mock contract with 0 clauses
- Verify: `_empty_result()` returned
- Verify: total_risks=0, total_missing=0

**TC-18: test_citation_format_flexibility**
- Mock response with various citation formats:
  - "Model Tenancy Act 2021, Section 7(1)"
  - "Standard practice - fair deposit terms"
  - "Maharashtra Rent Control Act 1999, Section 11(2) (Maharashtra)"
- Verify: All accepted (validator doesn't enforce format, just non-empty)

**Test Utilities:**
- Create helper to generate mock Contract/Clause objects
- Create helper to count database rows: `SELECT COUNT(*) FROM risk_findings WHERE contract_id = ?`

---

## Verification Steps

After completing all tasks:

1. **Run migration:**
   ```bash
   cd backend
   alembic upgrade head
   ```
   Verify `risk_findings` table created with constraints.

2. **Run test suite:**
   ```bash
   cd backend
   pytest tests/test_detect_risk.py -v
   ```
   Must show 18/18 passing.

3. **Verify Pydantic validation:**
   ```bash
   cd backend
   python -c "
   from app.llm.models import RiskyClauseFinding, Severity
   try:
       RiskyClauseFinding(clause_id='1', reason='Test reason here', triggering_rule_or_corpus='', severity=Severity.HIGH)
       print('ERROR: Empty string accepted!')
   except ValueError as e:
       print(f'✓ Validation working: {e}')
   "
   ```

4. **Verify imports compile:**
   ```bash
   cd backend
   python -c "from app.llm.detect_risk import detect_risks; print('✓ Imports OK')"
   ```

5. **Check database constraints:**
   ```sql
   SELECT conname, pg_get_constraintdef(oid)
   FROM pg_constraint
   WHERE conrelid = 'risk_findings'::regclass;
   ```
   Verify all CHECK constraints present.

---

## File Summary

**New Files Created:**
1. `backend/alembic/versions/005_create_risk_findings.py` — Migration for risk_findings table
2. `backend/app/llm/detect_risk.py` — Core risk detection logic (12 functions)
3. `backend/tests/mocks/mock_risk_responses.py` — Mock LLM responses for testing
4. `backend/tests/test_detect_risk.py` — 18 test cases (TC-1 through TC-18)

**Modified Files:**
5. `backend/app/llm/models.py` — Add Severity, RiskyClauseFinding, MissingClauseFinding, RiskDetectionResponse, RiskDetectionResult
6. `backend/app/db/models.py` — Add RiskFinding model, update Contract relationship

---

## Critical Notes

1. **Traceability is Non-Negotiable:**
   - Pydantic validators MUST reject empty `triggering_rule_or_corpus`
   - Retry logic MUST emphasize this requirement
   - Tests MUST verify rejection of untraceable findings
   - This is the most safety-critical part of the spec

2. **Context Parameter Name:**
   - `build_risk_prompt()` uses `retrieved_context` (not `legal_context`)
   - Confirmed in actual `prompt_builder.py` code

3. **Search Function Parameter Order:**
   - `search_legal_rules(clause_text, db, ...)` — db is 2nd param
   - `search_reference_corpus(clause_text, contract_type, db, ...)` — db is 3rd param
   - Don't mix up the order

4. **LLM Provider Abstraction:**
   - Use `call_llm()` directly — it routes to Gemini automatically
   - Do NOT import provider-specific modules
   - Provider controlled by LLM_PROVIDER env var

5. **Database Idempotency:**
   - DELETE existing findings before INSERT
   - Allows re-running risk detection on same contract
   - Important for iterative development/debugging

---

## Success Criteria

- [ ] Severity enum with low/medium/high values
- [ ] RiskyClauseFinding and MissingClauseFinding models with traceability validators
- [ ] RiskDetectionResponse and RiskDetectionResult models
- [ ] Migration 005 creates risk_findings table with all constraints
- [ ] RiskFinding SQLAlchemy model matches migration
- [ ] Contract model has risk_findings relationship
- [ ] detect_risks() orchestrates full pipeline correctly
- [ ] _call_llm_with_traceability_validation() implements retry logic
- [ ] _validate_all_findings_traceable() provides paranoid validation
- [ ] _add_traceability_emphasis() adds emphatic instruction
- [ ] _persist_findings() handles idempotent re-runs
- [ ] Empty string traceability rejected by Pydantic
- [ ] All 18 test cases pass
- [ ] Tests use MockLLMClient (zero real API calls)
- [ ] Malformed JSON handled gracefully
- [ ] Invalid clause_id logged but doesn't fail entire detection
- [ ] build_risk_prompt() called with retrieved_context parameter
- [ ] merge_retrieval_results() aggregates Stage 5A + 5B results
- [ ] format_merged_context() produces single formatted string

---

## Commit Strategy

Use Conventional Commits:
- `feat(llm): add risk detection Pydantic models with traceability validation` — Task 1
- `feat(db): add risk_findings table migration with constraints` — Task 2
- `feat(llm): implement detect_risks() with traceability enforcement` — Task 3
- `feat(db): add RiskFinding model and Contract relationship` — Task 4
- `test(llm): add mock risk responses for testing` — Task 5
- `test(llm): add 18 risk detection test cases (TC-1 to TC-18)` — Task 6
