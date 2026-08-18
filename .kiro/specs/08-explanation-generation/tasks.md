# Stage 8: Explanation Generation - Implementation Tasks

## Critical Schema Corrections (BEFORE STARTING)

**VERIFIED DATABASE SCHEMA:**
- `contracts.id` → INTEGER (not UUID)
- `clauses.id` → INTEGER (not UUID)
- `risk_findings.id` → UUID (own primary key)
- `risk_findings.contract_id` → INTEGER (FK to contracts.id)
- `risk_findings.clause_id` → INTEGER (FK to clauses.id)

**LLM CLIENT:**
- Use `call_llm()` from `backend/app/llm/llm_client.py` (provider-agnostic)
- Currently routes to Gemini via `LLM_PROVIDER=gemini`
- Model: `GEMINI_MODEL=models/gemini-3.7-flash`
- DO NOT hardcode provider or model name

**CITATION FORMATTING:**
- `format_citation()` is DETERMINISTIC string parsing (no LLM call)
- Parses existing `triggering_rule_or_corpus` from Stage 7 database rows
- Adds prefixes: `[Legal]` for legal rules, `[Reference]` for corpus
- Does NOT generate new citations via LLM (prevents hallucination)

---

## Tasks

### Task 1: Extend backend/app/llm/models.py with Explanation Pydantic Models

**File:** `backend/app/llm/models.py`

**Add these models:**

1. `ExplanationResponse` (base model)
   - Fields: `finding_id` (str), `finding_type` (Literal), `clause_id` (int | None), `expected_clause_type` (str | None), `reason` (str), `severity` (str), `explanation` (str), `formatted_citation` (str)
   - All IDs must be compatible with INTEGER database schema

2. `RiskyClauseExplanation` (extends ExplanationResponse)
   - Fields: `finding_type` = "risky_clause", `clause_id` (int, required), `clause_text` (str), `clause_number` (str)
   - Note: `clause_id` is INTEGER, not UUID

3. `MissingClauseExplanation` (extends ExplanationResponse)
   - Fields: `finding_type` = "missing_clause", `expected_clause_type` (str, required)

4. `ContractExplanationsResponse`
   - Fields: `contract_id` (int), `risky_clauses` (list[RiskyClauseExplanation]), `missing_clauses` (list[MissingClauseExplanation]), `summary` (dict[str, int])
   - Note: `contract_id` is INTEGER, not UUID

**Success Criteria:**
- All models use type hints compatible with INTEGER schema (int not UUID for contract_id, clause_id)
- Pydantic validation enforces required fields
- Models match API response format from spec

---

### Task 2: Create Alembic Migration 006 Adding Explanation Caching Columns

**File:** `backend/alembic/versions/006_add_explanation_caching.py`

**Migration adds to `risk_findings` table:**
1. `explanation` → TEXT, nullable (cached plain-language explanation)
2. `formatted_citation` → TEXT, nullable (cached formatted citation)
3. `explanation_generated_at` → TIMESTAMP WITH TIME ZONE, nullable

**Indexes:**
- `idx_risk_findings_explanation_null` on `(contract_id)` WHERE `explanation IS NULL`
- `idx_risk_findings_citation` on `(triggering_rule_or_corpus)`

**CRITICAL:**
- Verify migration chains onto `005_create_risk_findings`
- Set `down_revision = '005_create_risk_findings'`
- Use `op.execute()` for raw SQL or `op.add_column()` for SQLAlchemy DDL
- DO NOT alter existing column types (contract_id and clause_id remain INTEGER)

**Success Criteria:**
- Migration runs without errors against live database
- Three nullable columns added to risk_findings
- Both indexes created
- Downgrade drops columns and indexes cleanly

---

### Task 3: Implement backend/app/llm/generate_explanations.py

**File:** `backend/app/llm/generate_explanations.py`

**Functions to implement:**

1. **`generate_explanation(finding: RiskFinding, db: AsyncSession) -> str`**
   - Build prompt using `_build_explanation_prompt(finding)`
   - Call `call_llm()` from `llm_client.py` (provider-agnostic, no hardcoding)
   - Validate response with `_contains_forbidden_language()`
   - If forbidden language detected: retry once with emphasis in prompt
   - Cache result in `risk_findings.explanation` and `explanation_generated_at`
   - Return explanation string

2. **`format_citation(triggering_rule_or_corpus: str) -> str`**
   - DETERMINISTIC string formatting only (NO LLM call)
   - Detect legal rule pattern: contains "Act" and "Section"
   - Legal rule: replace "Section " with "§", prepend "[Legal] "
   - Corpus reference: prepend "[Reference] "
   - Examples:
     - "Model Tenancy Act 2021, Section 7(1)" → "[Legal] Model Tenancy Act 2021, §7(1)"
     - "Standard practice - fair deposit terms" → "[Reference] Standard practice - fair deposit terms"

3. **`generate_all_explanations(contract_id: int, db: AsyncSession) -> int`**
   - Fetch all RiskFinding rows WHERE `contract_id = contract_id` AND `explanation IS NULL`
   - Note: `contract_id` parameter is INTEGER
   - For each finding: call `generate_explanation()`
   - Continue on error (log but don't fail batch)
   - Return count of newly generated explanations

4. **`get_contract_explanations(contract_id: int, db: AsyncSession, auto_generate: bool = True) -> ContractExplanationsResponse`**
   - Note: `contract_id` parameter is INTEGER
   - If `auto_generate=True`: call `generate_all_explanations()` first
   - Fetch all RiskFinding rows WHERE `contract_id = contract_id`
   - For each finding:
     - Format citation with `format_citation(finding.triggering_rule_or_corpus)`
     - Cache formatted_citation if not already cached
     - For risky clauses: fetch Clause details (clause_id is INTEGER)
     - Build RiskyClauseExplanation or MissingClauseExplanation
   - Build summary dict (total_risks, total_missing, high/medium/low counts)
   - Return ContractExplanationsResponse

**Helper functions:**

5. **`_build_explanation_prompt(finding: RiskFinding) -> str`**
   - Construct prompt emphasizing plain language, no legal advice, descriptive tone
   - Include finding details: type, reason, severity, triggering_rule_or_corpus
   - Explicit requirements: 2-4 sentences, 8th-10th grade reading level
   - Forbidden: "you should", "you must", "we recommend", "consult a lawyer"

6. **`_contains_forbidden_language(text: str) -> bool`**
   - Regex patterns for forbidden phrases: `\byou should\b`, `\byou must\b`, `\bwe recommend\b`, `\bconsult a lawyer\b`, etc.
   - Return True if any pattern matches (case-insensitive)

7. **`_is_legal_rule(reference: str) -> bool`**
   - Detect if reference contains "Act" and "Section"
   - Used by `format_citation()` to route formatting logic

8. **`_format_legal_citation(reference: str) -> str`**
   - Replace "Section " with "§"
   - Prepend "[Legal] "

9. **`_format_corpus_citation(reference: str) -> str`**
   - Prepend "[Reference] "

10. **`_fetch_clause(clause_id: int | None, db: AsyncSession) -> Clause | None`**
    - Note: `clause_id` is INTEGER
    - Fetch Clause WHERE `id = clause_id`
    - Return None if clause_id is None or not found

**Success Criteria:**
- All functions use `call_llm()` (no hardcoded provider)
- `format_citation()` never calls LLM (deterministic string formatting)
- Forbidden language detection triggers retry (max 1 retry)
- All database queries use INTEGER for contract_id and clause_id
- Explanations cached in database to avoid redundant LLM calls
- Type hints match corrected schema (int not UUID for foreign keys)

---

### Task 4: Implement backend/app/api/routes/explanations.py

**File:** `backend/app/api/routes/explanations.py`

**Endpoints:**

1. **`GET /api/contracts/{contract_id}/explanations`**
   - Path parameter: `contract_id: int` (INTEGER, not UUID)
   - Query parameter: `auto_generate: bool = True`
   - Calls `get_contract_explanations(contract_id, db, auto_generate)`
   - Returns:
     ```json
     {
       "success": true,
       "data": {
         "contract_id": 1,
         "risky_clauses": [...],
         "missing_clauses": [...],
         "summary": {"total_risks": 3, "high_severity": 2, ...}
       },
       "error": null
     }
     ```
   - Error handling: 404 if contract not found, 500 on unexpected errors

2. **`POST /api/contracts/{contract_id}/explanations/regenerate`**
   - Path parameter: `contract_id: int` (INTEGER, not UUID)
   - Clear cached explanations: SET `explanation = NULL, explanation_generated_at = NULL` WHERE `contract_id = contract_id`
   - Call `generate_all_explanations(contract_id, db)`
   - Returns:
     ```json
     {
       "success": true,
       "data": {"regenerated_count": 5},
       "error": null
     }
     ```

**Success Criteria:**
- Path parameter type is `int` (matches INTEGER schema)
- API returns standard envelope format (`success`, `data`, `error`)
- Auto-generate flag controls lazy generation
- Regenerate endpoint clears cache before regenerating
- Error responses use appropriate HTTP status codes

---

### Task 5: Create backend/tests/mocks/mock_explanation_responses.py

**File:** `backend/tests/mocks/mock_explanation_responses.py`

**Constants to define:**

1. `VALID_EXPLANATION_PLAIN_LANGUAGE`
   - Example: "This clause specifies a security deposit of 4 months' rent, which exceeds the legal limit of 2 months under the Model Tenancy Act 2021. This creates potential financial burden for tenants and may be unenforceable in disputes."

2. `FORBIDDEN_LANGUAGE_EXPLANATION`
   - Example: "You should change this clause immediately. You must consult a lawyer to avoid legal issues. We recommend hiring an attorney."
   - Used to test forbidden language detection

3. `LEGAL_RULE_CITATION_RAW`
   - Example: "Model Tenancy Act 2021, Section 7(1)"

4. `LEGAL_RULE_CITATION_FORMATTED`
   - Example: "[Legal] Model Tenancy Act 2021, §7(1)"

5. `CORPUS_CITATION_RAW`
   - Example: "Standard practice - fair deposit terms"

6. `CORPUS_CITATION_FORMATTED`
   - Example: "[Reference] Standard practice - fair deposit terms"

7. `MULTI_FINDING_MOCK_RESPONSE`
   - Dict with risky_clauses and missing_clauses lists for testing batch operations

**Success Criteria:**
- At least one valid plain-language explanation
- At least one explanation with forbidden language
- Examples of both legal rule and corpus citation formats
- Constants usable in test fixtures

---

### Task 6: Implement backend/tests/test_generate_explanations.py

**File:** `backend/tests/test_generate_explanations.py`

**Test cases (18 total):**

**TC-1:** `test_generate_single_explanation`
- Mock finding with reason and triggering_rule_or_corpus
- Call `generate_explanation(finding, db)`
- Assert: Explanation is 2-4 sentences (validate length)
- Assert: No forbidden language
- Assert: Cached in database (`explanation` column populated)

**TC-2:** `test_format_citation_legal_rule`
- Input: "Model Tenancy Act 2021, Section 7(1)"
- Call `format_citation()`
- Assert: "[Legal] Model Tenancy Act 2021, §7(1)"
- Assert: `call_llm` NOT invoked (deterministic, no LLM)

**TC-3:** `test_format_citation_legal_rule_with_state`
- Input: "Maharashtra Rent Control Act 1999, Section 11(2) (Maharashtra)"
- Assert: "[Legal] Maharashtra Rent Control Act 1999, §11(2) (Maharashtra)"

**TC-4:** `test_format_citation_reference_corpus`
- Input: "Standard practice - fair deposit terms"
- Assert: "[Reference] Standard practice - fair deposit terms"

**TC-5:** `test_format_citation_multiple_formats`
- Test various citation formats from mock data
- Assert: All formatted without errors
- Assert: No LLM calls for any citation

**TC-6:** `test_forbidden_language_detection_present`
- Mock LLM returns: "You should change this clause immediately."
- Assert: `_contains_forbidden_language()` returns True
- Assert: Retry triggered (LLM called twice)

**TC-7:** `test_forbidden_language_detection_absent`
- Mock LLM returns: "This clause differs from standard practice..."
- Assert: `_contains_forbidden_language()` returns False
- Assert: Accepted without retry (LLM called once)

**TC-8:** `test_batch_generation_all_new`
- Create 5 findings with no explanations
- Call `generate_all_explanations(contract_id, db)`
- Assert: 5 explanations generated
- Assert: All cached in database

**TC-9:** `test_batch_generation_partial_cached`
- Create 5 findings, 3 already have explanations
- Call `generate_all_explanations(contract_id, db)`
- Assert: Only 2 new explanations generated
- Assert: Existing 3 unchanged

**TC-10:** `test_batch_generation_all_cached`
- Create 5 findings, all have explanations
- Call `generate_all_explanations(contract_id, db)`
- Assert: Returns 0 (no new generations)
- Assert: No LLM calls made

**TC-11:** `test_api_endpoint_first_request`
- GET `/api/contracts/{contract_id}/explanations?auto_generate=true`
- Findings have no cached explanations
- Assert: Explanations generated on-the-fly
- Assert: Response includes all findings with explanations
- Assert: Summary counts correct

**TC-12:** `test_api_endpoint_cached_request`
- GET `/api/contracts/{contract_id}/explanations?auto_generate=true`
- Findings already have cached explanations
- Assert: No LLM calls made
- Assert: Response includes cached explanations
- Assert: Fast response

**TC-13:** `test_api_endpoint_no_auto_generate`
- GET `/api/contracts/{contract_id}/explanations?auto_generate=false`
- Some findings missing explanations
- Assert: Returns "Explanation pending..." for missing
- Assert: No LLM calls made

**TC-14:** `test_citation_traceability`
- Fetch all findings for contract
- For each finding: assert `formatted_citation` corresponds to `triggering_rule_or_corpus`
- Assert: No orphan citations (every citation has DB source)

**TC-15:** `test_regenerate_endpoint`
- POST `/api/contracts/{contract_id}/explanations/regenerate`
- Assert: Existing explanations cleared (set to NULL)
- Assert: New explanations generated
- Assert: Count returned correctly

**TC-16:** `test_risky_clause_with_clause_details`
- Risky clause finding linked to clause (clause_id is INTEGER)
- Assert: Response includes `clause_text` and `clause_number`
- Assert: Clause fetched from database

**TC-17:** `test_missing_clause_details`
- Missing clause finding
- Assert: Response includes `expected_clause_type`
- Assert: `clause_id` is None

**TC-18:** `test_severity_ordering`
- Mix of high/medium/low severity findings
- Call `get_contract_explanations()`
- Assert: Response ordered by severity (high first)
- Assert: Summary counts by severity correct

**Testing Setup:**
- Use `MockLLMClient` (from existing mocks)
- Mock `call_llm()` to return predefined explanations
- Use AsyncMock for database operations
- Zero real Gemini API calls in unit tests
- Fixtures for RiskFinding, Clause, Contract with INTEGER IDs

**Success Criteria:**
- All 18 test cases pass
- No real LLM calls made (all mocked)
- Tests verify INTEGER schema (contract_id, clause_id)
- Tests verify `format_citation()` is deterministic (no LLM call)
- Tests verify forbidden language detection and retry logic
- Tests verify caching behavior (all-new, partial, all-cached)
- Tests verify API endpoint behavior and response format

---

## Execution Order

1. Task 1: Extend models.py (Pydantic models)
2. Task 2: Create migration 006 (database schema)
3. Task 3: Implement generate_explanations.py (core logic)
4. Task 4: Implement API routes (FastAPI endpoints)
5. Task 5: Create mock responses (test fixtures)
6. Task 6: Implement test_generate_explanations.py (18 test cases)

## Success Criteria Checklist

After completing all tasks, verify:

- [ ] `generate_explanation()` creates 2-4 sentence plain-language explanations via `call_llm()` (provider-agnostic)
- [ ] No forbidden language in generated explanations ("you should", "you must", legal advice)
- [ ] `format_citation()` formats citations deterministically (NO LLM call)
- [ ] Legal rules formatted as: `[Legal] Act Name, §Section`
- [ ] Corpus references formatted as: `[Reference] Label`
- [ ] Explanations cached in `risk_findings.explanation` column
- [ ] Citations cached in `risk_findings.formatted_citation` column
- [ ] GET `/api/contracts/{contract_id}/explanations` returns all findings with explanations
- [ ] Path parameter `contract_id` is INTEGER (not UUID)
- [ ] Auto-generate flag controls on-the-fly generation
- [ ] Cached explanations returned without LLM calls
- [ ] POST `/api/contracts/{contract_id}/explanations/regenerate` clears and regenerates
- [ ] Citation validation: 100% traceable to `triggering_rule_or_corpus` in DB
- [ ] No orphan citations (every citation has DB source)
- [ ] All 18 test cases pass with zero real API calls
- [ ] Migration 006 runs successfully and chains onto migration 005

## Notes

- **CRITICAL:** All contract_id and clause_id references must use INTEGER type (verified against live DB schema)
- **CRITICAL:** `format_citation()` is deterministic string parsing (NO LLM call to prevent hallucination)
- **CRITICAL:** Use `call_llm()` from `llm_client.py` (provider-agnostic, currently routes to Gemini)
- Explanations are generated lazily (on first request) and cached
- Forbidden language detection triggers max 1 retry with emphasis
- Batch generation continues on error (logs but doesn't fail entire batch)
- API follows standard envelope format: `{"success": bool, "data": {...}, "error": str | null}`
