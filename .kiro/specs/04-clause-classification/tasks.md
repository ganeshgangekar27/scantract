# Tasks: Clause Classification Implementation (Stage 4)

## Overview
Implement LLM-based clause classification for ScanTract contracts with provider abstraction (Claude/OpenAI), batch processing, error handling, and comprehensive testing.

**Critical Dependencies**:
- **Stage 3 (Prompt Templates)**: Imports `build_classification_prompt()` from `backend/app/rag/prompt_builder.py` - DO NOT reimplement prompt logic
- **Stages 5A/5B (Retrieval)**: NOT YET BUILT - All calls MUST use `retrieved_context=""` until retrieval stages exist

**Key Constraint**: No placeholder retrieval logic. Context stays empty string throughout this spec.

---

## Task 1: Create LLM Module Structure
**Files**: Multiple module files

**Actions**:
- Create `backend/app/llm/` directory
- Create `backend/app/llm/__init__.py` with module docstring
- Create `backend/app/llm/llm_client.py` (empty, populated in Task 5)
- Create `backend/app/llm/classify_clauses.py` (empty, populated in Task 6-7)
- Create `backend/app/llm/models.py` (empty, populated in Task 2)
- Create `backend/app/llm/providers/` directory
- Create `backend/app/llm/providers/__init__.py`
- Create `backend/app/llm/providers/claude.py` (empty, populated in Task 3)
- Create `backend/app/llm/providers/openai.py` (empty, populated in Task 4)

**Acceptance Criteria**:
- All directories created: `backend/app/llm/` and `backend/app/llm/providers/`
- All `__init__.py` files present
- Empty placeholder files for llm_client.py, classify_clauses.py, models.py, claude.py, openai.py
- Module is importable: `from app.llm import models` works

---

## Task 2: Implement Data Models
**File**: `backend/app/llm/models.py`

**Actions**:
- Add imports: `from pydantic import BaseModel, Field, field_validator; from typing import Literal; from datetime import datetime`
- Define `ClauseType` as Literal type with taxonomy:
  - `payment_terms`
  - `termination`
  - `liability`
  - `confidentiality`
  - `intellectual_property`
  - `dispute_resolution`
  - `term_duration`
  - `renewal`
  - `indemnification`
  - `warranties`
  - `force_majeure`
  - `other`

- Implement `ClauseClassification` Pydantic model:
  ```python
  class ClauseClassification(BaseModel):
      clause_type: ClauseType
      key_entities: list[str] = Field(default_factory=list)
      confidence: float = Field(ge=0.0, le=1.0)
      reasoning: str = ""
  ```
- Add `@field_validator("key_entities")` that caps list at 20 items (truncate if longer, log warning)

- Implement `ClassificationResult` model:
  ```python
  class ClassificationResult(BaseModel):
      clause_index: str
      classification: ClauseClassification | None = None
      error: str | None = None
      tokens_used: int = 0
  ```

**Acceptance Criteria**:
- `ClauseType` Literal includes all 12 types
- `ClauseClassification` has all 4 fields with correct types and constraints
- `confidence` validated between 0.0-1.0
- `key_entities` validator caps at 20, logs warning if truncated
- `ClassificationResult` handles both success and error cases
- All models use Pydantic v2 syntax
- Type hints complete and accurate

---

## Task 3: Implement Claude Provider
**File**: `backend/app/llm/providers/claude.py`

**Actions**:
- Add imports: `import os; from anthropic import Anthropic, RateLimitError, APIError; import logging`
- Implement `async def call_claude(messages: list[dict[str, str]]) -> tuple[str, int]:`
  - Read `CLAUDE_API_KEY` from environment, raise `ValueError` if missing
  - Read `CLAUDE_MODEL` from environment, default to `"claude-3-haiku-20240307"`
  - Create Anthropic client with API key
  - Call `client.messages.create()` with:
    - `model=model_name`
    - `max_tokens=2048`
    - `messages=messages`
  - Extract response text from `response.content[0].text`
  - Calculate tokens: `tokens_used = response.usage.input_tokens + response.usage.output_tokens`
  - Return tuple: `(response_text, tokens_used)`
  - Handle `RateLimitError`: log error, raise with clear message
  - Handle `APIError`: log error with details, raise RuntimeError with provider context

**Acceptance Criteria**:
- Function signature: `async def call_claude(messages: list[dict[str, str]]) -> tuple[str, int]`
- Reads `CLAUDE_API_KEY` and `CLAUDE_MODEL` env vars
- Defaults to claude-3-haiku-20240307 if CLAUDE_MODEL not set
- Returns (response_text, total_tokens)
- Raises ValueError for missing API key
- Handles RateLimitError and APIError with clear messages
- Logs errors at ERROR level

---

## Task 4: Implement OpenAI Provider
**File**: `backend/app/llm/providers/openai.py`

**Actions**:
- Add imports: `import os; from openai import AsyncOpenAI, RateLimitError, APIError; import logging`
- Implement `async def call_openai(messages: list[dict[str, str]]) -> tuple[str, int]:`
  - Read `OPENAI_API_KEY` from environment, raise `ValueError` if missing
  - Read `OPENAI_MODEL` from environment, default to `"gpt-3.5-turbo"`
  - Create AsyncOpenAI client with API key
  - Call `await client.chat.completions.create()` with:
    - `model=model_name`
    - `messages=messages`
    - `response_format={"type": "json_object"}` (enforces JSON output)
    - `max_tokens=2048`
  - Extract response text from `response.choices[0].message.content`
  - Calculate tokens: `tokens_used = response.usage.total_tokens`
  - Return tuple: `(response_text, tokens_used)`
  - Handle `RateLimitError`: log error, raise with clear message
  - Handle `APIError`: log error, raise RuntimeError with provider context

**Acceptance Criteria**:
- Function signature: `async def call_openai(messages: list[dict[str, str]]) -> tuple[str, int]`
- Uses AsyncOpenAI (async client)
- Reads `OPENAI_API_KEY` and `OPENAI_MODEL` env vars
- Defaults to gpt-3.5-turbo if OPENAI_MODEL not set
- Uses `response_format={"type": "json_object"}` for JSON enforcement
- Returns (response_text, total_tokens)
- Raises ValueError for missing API key
- Handles RateLimitError and APIError
- Logs errors at ERROR level

---

## Task 5: Implement LLM Client Dispatcher
**File**: `backend/app/llm/llm_client.py`

**Actions**:
- Add imports: `import os; from enum import Enum; from app.llm.providers.claude import call_claude; from app.llm.providers.openai import call_openai`
- Define `LLMProvider` enum:
  ```python
  class LLMProvider(str, Enum):
      CLAUDE = "claude"
      OPENAI = "openai"
  ```

- Implement `async def call_llm(messages: list[dict[str, str]]) -> tuple[str, int]:`
  - Read `LLM_PROVIDER` env var (required)
  - Convert to lowercase, match against LLMProvider enum
  - If "claude": return `await call_claude(messages)`
  - If "openai": return `await call_openai(messages)`
  - Else: raise `ValueError(f"Unsupported LLM provider: {provider}. Supported: claude, openai")`

**Acceptance Criteria**:
- `LLMProvider` enum has CLAUDE and OPENAI members
- `call_llm()` reads `LLM_PROVIDER` env var
- Dispatches to correct provider based on env var value
- Raises clear ValueError for unsupported/missing provider
- Returns (response_text, tokens_used) tuple from selected provider
- Async function signature

---

## Task 6: Implement Single Clause Classification
**File**: `backend/app/llm/classify_clauses.py`

**Actions**:
- Add imports:
  ```python
  import json
  import logging
  from app.rag.prompt_builder import build_classification_prompt
  from app.llm.llm_client import call_llm
  from app.llm.models import ClauseClassification, ClassificationResult
  ```

- Implement helper `_parse_classification_response(response_text: str) -> dict:`
  - Strip markdown code fences: remove ```json and ``` artifacts
  - Parse JSON: `json.loads(cleaned_text)`
  - Return parsed dict
  - Raise ValueError if JSON invalid

- Implement helper `_add_emphatic_json_instruction(messages: list[dict]) -> list[dict]:`
  - Append additional message: `{"role": "user", "content": "Respond with ONLY valid JSON. No markdown, no explanation."}`
  - Return modified messages list

- Implement `async def classify_clause(clause_text: str, clause_index: str, contract_type: str, retrieved_context: str = "") -> ClassificationResult:`
  - **CRITICAL**: `retrieved_context` defaults to `""` and MUST stay empty until Stages 5A/5B exist
  - Call `build_classification_prompt(clause_text, clause_index, contract_type, retrieved_context)`
  - Call `await call_llm(messages)`
  - Parse response with `_parse_classification_response()`
  - Validate with `ClauseClassification(**parsed_dict)`
  - Return `ClassificationResult(clause_index=clause_index, classification=result, tokens_used=tokens)`
  - On `JSONDecodeError` or `ValueError`:
    - Log warning: "Malformed response for clause {clause_index}, retrying with emphatic instruction"
    - Retry once with `_add_emphatic_json_instruction(messages)`
    - Parse retry response
    - If retry also fails: raise `RuntimeError(f"Failed to classify clause {clause_index} after retry: {error}")`
  - On other exceptions: return `ClassificationResult(clause_index=clause_index, error=str(exception))`

**Acceptance Criteria**:
- Function signature: `async def classify_clause(...) -> ClassificationResult`
- **Uses `retrieved_context=""` by default (NO retrieval logic)**
- Imports `build_classification_prompt()` from Stage 3 (does NOT reimplement)
- Strips ```json/``` markdown artifacts before parsing
- Retries once with emphatic instruction on parse failure
- Raises RuntimeError with clause_index in message if retry fails
- Returns error in ClassificationResult for non-parse exceptions
- Logs warnings for malformed responses

---

## Task 7: Implement Batch Classification
**File**: `backend/app/llm/classify_clauses.py` (continued)

**Actions**:
- Add imports: `import asyncio; from sqlalchemy.ext.asyncio import AsyncSession; from sqlalchemy import select, update; from datetime import datetime, timezone`
- Import Clause model: `from app.db.models import Clause`

- Implement `async def classify_all_clauses(contract_id: int, contract_type: str, db: AsyncSession) -> dict:`
  - Read `LLM_CONCURRENCY_LIMIT` env var, default to 5, convert to int
  - Create semaphore: `semaphore = asyncio.Semaphore(concurrency_limit)`
  
  - Fetch clauses: 
    ```python
    query = select(Clause).where(Clause.contract_id == contract_id).order_by(Clause.position)
    result = await db.execute(query)
    clauses = result.scalars().all()
    ```
  
  - Define inner `async def classify_and_store(clause: Clause) -> tuple[bool, int]:`
    - Acquire semaphore
    - Call `classify_clause(clause.text, clause.clause_id, contract_type, retrieved_context="")`
    - **CRITICAL**: Pass `retrieved_context=""` explicitly (no retrieval until 5A/5B)
    - On success:
      - Update clause: `clause.clause_type = result.classification.clause_type`
      - `clause.key_entities = result.classification.key_entities`
      - `clause.confidence = result.classification.confidence`
      - `clause.classified_at = datetime.now(timezone.utc)`
      - `clause.classification_error = None`
      - Return `(True, result.tokens_used)`
    - On error:
      - Update clause: `clause.classification_error = result.error`
      - `clause.classified_at = datetime.now(timezone.utc)`
      - Log error
      - Return `(False, result.tokens_used)`
    - Release semaphore in finally block
  
  - Run tasks: `results = await asyncio.gather(*[classify_and_store(c) for c in clauses])`
  - Commit once: `await db.commit()`
  - Calculate stats: count successful, failed, sum tokens
  - Return dict:
    ```python
    {
        "total": len(clauses),
        "successful": success_count,
        "failed": failed_count,
        "total_tokens": sum_tokens
    }
    ```

**Acceptance Criteria**:
- Function signature: `async def classify_all_clauses(contract_id: int, contract_type: str, db: AsyncSession) -> dict`
- Fetches clauses ordered by position
- Respects `LLM_CONCURRENCY_LIMIT` env var (default 5)
- Uses asyncio.Semaphore to limit concurrent LLM calls
- **Passes `retrieved_context=""` to classify_clause() (MUST be explicit)**
- Updates clause fields on success: clause_type, key_entities, confidence, classified_at
- Updates classification_error on failure
- Commits once after all classifications complete
- Returns summary dict with total/successful/failed/total_tokens
- Logs individual classification errors

---

## Task 8: Create Classification Fields Migration
**File**: `backend/db/migrations/versions/002_add_classification_fields.py`

**Actions**:
- Create Alembic migration file with revision ID "002"
- Add columns to `clauses` table:
  - `clause_type` VARCHAR(50), nullable=True
  - `key_entities` JSONB, nullable=True
  - `confidence` FLOAT, nullable=True
  - `classification_error` TEXT, nullable=True
  - `classified_at` TIMESTAMP WITH TIME ZONE, nullable=True
- Create indexes:
  - Index on `clause_type` for filtering by type
  - Index on `confidence` for sorting/filtering by confidence
- Downgrade should drop indexes and columns

**Acceptance Criteria**:
- Migration file follows Alembic naming: `002_add_classification_fields.py`
- Adds all 5 columns with correct types
- `key_entities` uses JSONB type (PostgreSQL)
- Creates 2 indexes (clause_type, confidence)
- Includes downgrade logic to remove changes
- Migration is reversible

---

## Task 9: Update Clause Model
**File**: `backend/app/db/models.py`

**Actions**:
- Add import: `from sqlalchemy.dialects.postgresql import JSONB`
- Update `Clause` SQLAlchemy model with new columns:
  ```python
  clause_type = Column(String(50), nullable=True, index=True)
  key_entities = Column(JSONB, nullable=True)
  confidence = Column(Float, nullable=True, index=True)
  classification_error = Column(Text, nullable=True)
  classified_at = Column(DateTime(timezone=True), nullable=True)
  ```

**Acceptance Criteria**:
- All 5 new columns added to Clause model
- Column types match migration: String(50), JSONB, Float, Text, DateTime(timezone=True)
- Indexes declared on clause_type and confidence
- Columns nullable=True (classification is optional)
- JSONB import from sqlalchemy.dialects.postgresql

---

## Task 10: Create Mock LLM Client
**File**: `backend/tests/mocks/mock_llm.py`

**Actions**:
- Create `backend/tests/mocks/` directory
- Create `backend/tests/mocks/__init__.py`
- Implement `MockLLMClient` class:
  ```python
  class MockLLMClient:
      def __init__(self, responses: list[str] = None, fail_count: int = 0):
          self.responses = responses or []
          self.fail_count = fail_count
          self.call_count = 0
          self.call_history = []
      
      async def call(self, messages: list[dict]) -> tuple[str, int]:
          self.call_count += 1
          self.call_history.append(messages)
          
          if self.call_count <= self.fail_count:
              raise ValueError("Simulated LLM failure")
          
          response_text = self.responses[(self.call_count - self.fail_count - 1) % len(self.responses)]
          return (response_text, 150)  # Mock token count
  ```

- Define predefined response constants:
  ```python
  MOCK_VALID_RESPONSE = json.dumps({
      "clause_type": "payment_terms",
      "key_entities": ["tenant", "rent", "5th"],
      "confidence": 0.92,
      "reasoning": "Clear payment terms"
  })
  
  MOCK_MALFORMED_JSON = "```json\n" + MOCK_VALID_RESPONSE + "\n```"
  
  MOCK_INVALID_JSON = "This is not JSON at all"
  ```

**Acceptance Criteria**:
- `MockLLMClient` class with configurable responses and fail_count
- Tracks call_count and call_history for test assertions
- Returns (response_text, 150) tuple
- Simulates failure for first `fail_count` calls
- Three predefined constants: MOCK_VALID_RESPONSE, MOCK_MALFORMED_JSON, MOCK_INVALID_JSON
- No real API calls ever made

---

## Task 11: Write LLM Client Tests
**File**: `backend/tests/test_llm_client.py`

**Actions**:
- Test TC-1: Provider Selection
  - Mock both call_claude and call_openai
  - Set LLM_PROVIDER="claude", call call_llm(), assert call_claude was called
  - Set LLM_PROVIDER="openai", call call_llm(), assert call_openai was called
  - Set LLM_PROVIDER="invalid", assert raises ValueError with "Unsupported LLM provider"

- Test TC-2: Missing API Key
  - Mock environment without CLAUDE_API_KEY
  - Attempt call_claude(), assert raises ValueError with "CLAUDE_API_KEY"
  - Mock environment without OPENAI_API_KEY
  - Attempt call_openai(), assert raises ValueError with "OPENAI_API_KEY"

- Test TC-3: JSON Response Format
  - Mock OpenAI client to verify response_format={"type": "json_object"} passed
  - Call call_openai(), assert response_format parameter is set correctly

**Acceptance Criteria**:
- All 3 test cases implemented
- Uses mocking (unittest.mock or pytest-mock)
- No real API calls
- Tests cover provider selection, missing keys, JSON format enforcement
- Clear assertions with helpful error messages

---

## Task 12: Write Classification Tests
**File**: `backend/tests/test_classify_clauses.py`

**Actions**:
- Import MockLLMClient and constants from mocks.mock_llm
- Mock call_llm to use MockLLMClient throughout

- Test TC-4: Single Clause Success
  - Mock call_llm to return MOCK_VALID_RESPONSE
  - Call classify_clause() with test clause
  - Assert ClassificationResult has classification (not error)
  - Assert clause_type="payment_terms", confidence=0.92
  - Assert tokens_used=150

- Test TC-5: Malformed JSON Retry Success
  - Mock call_llm to return MOCK_MALFORMED_JSON first, then MOCK_VALID_RESPONSE on retry
  - Call classify_clause()
  - Assert 2 LLM calls made (original + retry)
  - Assert second call has emphatic JSON instruction appended
  - Assert final result is successful

- Test TC-6: Parse Failure After Retry
  - Mock call_llm to return MOCK_INVALID_JSON twice
  - Call classify_clause()
  - Assert raises RuntimeError with clause_index in message
  - Assert message includes "after retry"

- Test TC-7: Batch All Successful
  - Mock database with 3 test clauses
  - Mock call_llm to always return MOCK_VALID_RESPONSE
  - Call classify_all_clauses(contract_id=1, contract_type="rental", db=mock_db)
  - Assert result: {"total": 3, "successful": 3, "failed": 0, "total_tokens": 450}
  - Assert all 3 clauses updated with clause_type, confidence, classified_at
  - Assert classification_error is None for all

- Test TC-8: Batch Partial Failure
  - Mock database with 3 clauses
  - Mock call_llm: fail for 1st clause (exception), succeed for 2nd and 3rd
  - Call classify_all_clauses()
  - Assert result: {"total": 3, "successful": 2, "failed": 1, ...}
  - Assert failed clause has classification_error set
  - Assert successful clauses have clause_type set

- Test TC-9: Concurrency Limit Respected
  - Mock database with 10 clauses
  - Set LLM_CONCURRENCY_LIMIT=3
  - Track concurrent LLM calls (max concurrent should be ≤3)
  - Call classify_all_clauses()
  - Assert concurrency never exceeds 3 simultaneous calls

- Test TC-10: Schema Validation - Invalid Confidence
  - Mock call_llm to return JSON with confidence=1.5 (out of range)
  - Call classify_clause()
  - Assert Pydantic validation fails
  - Assert ClassificationResult has error field populated

- Test TC-11: Schema Validation - Key Entities Cap
  - Mock call_llm to return JSON with 25 key_entities
  - Call classify_clause()
  - Assert key_entities truncated to 20
  - Assert warning logged about truncation

- Test TC-12: Token Tracking
  - Mock call_llm to return varying token counts (100, 200, 150)
  - Call classify_all_clauses() with 3 clauses
  - Assert total_tokens in result equals sum (450)

**Acceptance Criteria**:
- All 9 classification tests implemented (TC-4 through TC-12)
- All tests use MockLLMClient (zero real API calls)
- Tests cover success, retry, failure, batch processing, concurrency, validation
- Database interactions mocked appropriately
- Tests are async (use pytest-asyncio)
- Clear test names and assertions

---

## Verification Checklist

Before marking Stage 4 complete, verify:

- [ ] Module structure: backend/app/llm/ with all files
- [ ] Models defined: ClauseType Literal (12 types), ClauseClassification, ClassificationResult
- [ ] Providers: call_claude() and call_openai() with error handling
- [ ] Dispatcher: call_llm() reads LLM_PROVIDER and routes correctly
- [ ] Single classification: classify_clause() with retry logic
- [ ] Batch classification: classify_all_clauses() with semaphore concurrency
- [ ] Migration: 002_add_classification_fields.py adds 5 columns + indexes
- [ ] Model updated: Clause has all 5 new fields
- [ ] Mock client: MockLLMClient with configurable responses
- [ ] Tests: 3 llm_client tests + 9 classify_clauses tests = 12 total
- [ ] Zero real API calls in tests (all mocked)
- [ ] **CRITICAL**: retrieved_context="" throughout (no retrieval logic)
- [ ] **CRITICAL**: Imports build_classification_prompt() from Stage 3 (no duplication)

---

## Dependencies

**Upstream (must be complete before starting)**:
- Stage 3 (Prompt Templates): Provides build_classification_prompt()
- Database infrastructure: Clauses table exists, async session available

**Downstream (blocks these stages)**:
- Stage 5A (Legal Rules KB): Will provide legal context for retrieved_context parameter
- Stage 5B (Reference Corpus): Will provide corpus context for retrieved_context parameter
- Stage 7 (Risk Detection): Uses classify_all_clauses() as prerequisite

**Critical Notes**:
- Stage 4 MUST work with empty retrieved_context="" until 5A/5B are built
- Do not implement placeholder retrieval logic - it will be replaced when 5A/5B exist
- classify_all_clauses() explicitly passes retrieved_context="" to classify_clause()
- Tests verify correct behavior with empty context

---

## Environment Variables Required

- `LLM_PROVIDER`: "claude" or "openai" (required)
- `CLAUDE_API_KEY`: Anthropic API key (required if using Claude)
- `CLAUDE_MODEL`: Model name (optional, defaults to claude-3-haiku-20240307)
- `OPENAI_API_KEY`: OpenAI API key (required if using OpenAI)
- `OPENAI_MODEL`: Model name (optional, defaults to gpt-3.5-turbo)
- `LLM_CONCURRENCY_LIMIT`: Max concurrent LLM calls (optional, defaults to 5)

---

## File Paths Summary

**Implementation Files** (8 files):
1. `backend/app/llm/__init__.py`
2. `backend/app/llm/models.py`
3. `backend/app/llm/providers/__init__.py`
4. `backend/app/llm/providers/claude.py`
5. `backend/app/llm/providers/openai.py`
6. `backend/app/llm/llm_client.py`
7. `backend/app/llm/classify_clauses.py`
8. `backend/app/db/models.py` (update existing)

**Database Files** (1 file):
9. `backend/db/migrations/versions/002_add_classification_fields.py`

**Test Files** (3 files):
10. `backend/tests/mocks/__init__.py`
11. `backend/tests/mocks/mock_llm.py`
12. `backend/tests/test_llm_client.py`
13. `backend/tests/test_classify_clauses.py`

**Total**: 13 files (7 new implementation, 1 migration, 1 model update, 4 test files)
