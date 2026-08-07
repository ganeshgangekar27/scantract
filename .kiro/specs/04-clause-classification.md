# Spec: Clause Classification

## Overview
Build the LLM-powered clause classification system for ScanTract — Stage 4 of the core pipeline that analyzes individual contract clauses, categorizes them by type, extracts key entities, and assigns confidence scores. This layer abstracts LLM provider choice (Claude/GPT) and handles concurrent processing with rate limiting.

## Scope
- Universal LLM client wrapper supporting Claude API and OpenAI API
- Clause classification with structured JSON responses
- Concurrent batch processing with rate limit protection
- Retry logic for malformed responses
- Database persistence of classification results
- Unit tests with mocked LLM (no real API calls)

## Requirements

### Functional Requirements

**FR-1: LLM Client Abstraction**
- Module: `backend/app/llm/llm_client.py`
- Single unified interface: `async call_llm(messages, response_format="json") -> dict`
- Provider selection via `LLM_PROVIDER` env var ("claude" or "openai")
- Support both Claude Anthropic API and OpenAI API
- Handle API errors gracefully (rate limits, timeouts, invalid keys)

**FR-2: Clause Classification Function**
- Module: `backend/app/llm/classify_clauses.py`
- Function: `async classify_clause(clause_text, clause_index, contract_type, context="")`
- Uses `build_classification_prompt()` from Stage 3
- Calls `call_llm()` with messages
- Parses strict JSON response

**FR-3: Classification Response Schema**
- Strict JSON schema enforced:
  ```json
  {
    "clause_type": "string",
    "key_entities": ["string"],
    "confidence": 0.0-1.0
  }
  ```
- Clause types must be from predefined taxonomy:
  - "payment_terms", "termination", "liability", "confidentiality",
    "intellectual_property", "dispute_resolution", "term_duration",
    "renewal", "indemnification", "warranties", "force_majeure", "other"


**FR-4: JSON Enforcement**
- System instruction in prompt: "Respond with ONLY valid JSON. No preamble, no explanation, no markdown formatting."
- Strip common formatting artifacts (```json, ```, markdown)
- Validate JSON schema after parsing
- Log malformed responses (without clause content) for monitoring

**FR-5: Error Handling & Retry Logic**
- If JSON parsing fails: retry once with emphatic JSON-only instruction
- If retry fails: mark clause as "classification_failed" (don't fail entire contract)
- Store error in `clauses.classification_error` column
- Continue processing remaining clauses
- If LLM API fails (timeout, rate limit): retry with exponential backoff (max 3 retries)

**FR-6: Batch Concurrent Processing**
- Function: `async classify_all_clauses(contract_id, clauses, contract_type)`
- Process clauses concurrently using `asyncio.Semaphore`
- Concurrency limit: 5 simultaneous LLM calls (configurable via env var)
- Prevents rate limit violations
- Progress tracking: log every 10 clauses processed

**FR-7: Database Persistence**
- Update `clauses` table with classification results:
  - `clause_type`: str
  - `key_entities`: JSON array
  - `confidence`: float
  - `classification_error`: str (nullable, populated if failed)
  - `classified_at`: timestamp
- Batch database updates (don't commit after each clause)

**FR-8: API Key Management**
- Claude API key: `CLAUDE_API_KEY` env var
- OpenAI API key: `OPENAI_API_KEY` env var
- Validate API key exists for selected provider at startup
- Never log API keys

### Non-Functional Requirements

**NFR-1: Performance**
- Classify 100 clauses in <60 seconds (with concurrency=5)
- Single classification completes in <3 seconds average
- Concurrent processing prevents blocking

**NFR-2: Cost Efficiency**
- Track token usage per call (log for monitoring)
- Use appropriate model tier (Claude Haiku/GPT-3.5 for classification)
- Batch processing reduces overhead


**NFR-3: Type Safety**
- All functions use type hints (Python 3.11+)
- Pydantic models for classification results
- Strict schema validation

**NFR-4: Reliability**
- Individual clause failure doesn't fail entire contract
- Retry logic handles transient failures
- Clear error messages for debugging

**NFR-5: Security**
- API keys loaded from environment only
- Clause content not logged in plaintext
- API responses validated before persistence

## Technical Design

### Module Structure

**Location:** `backend/app/llm/`

```
backend/app/llm/
├── __init__.py
├── llm_client.py          # Universal LLM wrapper
├── classify_clauses.py    # Clause classification logic
├── models.py              # Pydantic models for responses
└── providers/
    ├── __init__.py
    ├── claude.py          # Claude API implementation
    └── openai.py          # OpenAI API implementation
```

### LLM Client Design

**File: backend/app/llm/llm_client.py**

```python
from enum import Enum
from typing import Any

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    OPENAI = "openai"

async def call_llm(
    messages: list[dict[str, str]],
    response_format: str = "json",
    max_tokens: int = 1000,
    temperature: float = 0.0
) -> dict[str, Any]:
    """
    Universal LLM client supporting Claude and OpenAI.
    
    Args:
        messages: List of message dicts with "role" and "content"
        response_format: "json" or "text" (enforces JSON output)
        max_tokens: Max tokens in response
        temperature: LLM temperature (0.0 = deterministic)
    
    Returns:
        {
            "content": str,  # Raw LLM response
            "provider": str,
            "model": str,
            "usage": {"prompt_tokens": int, "completion_tokens": int}
        }
    
    Raises:
        ValueError: If provider not configured or invalid
        RuntimeError: If API call fails after retries
    """
    provider = _get_provider()
    
    if provider == LLMProvider.CLAUDE:
        from .providers.claude import call_claude
        return await call_claude(messages, response_format, max_tokens, temperature)
    elif provider == LLMProvider.OPENAI:
        from .providers.openai import call_openai
        return await call_openai(messages, response_format, max_tokens, temperature)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
```


### Provider Implementations

**File: backend/app/llm/providers/claude.py**

```python
import os
import anthropic
from typing import Any

async def call_claude(
    messages: list[dict[str, str]],
    response_format: str,
    max_tokens: int,
    temperature: float
) -> dict[str, Any]:
    """Call Claude API via Anthropic SDK."""
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError("CLAUDE_API_KEY not configured")
    
    client = anthropic.AsyncAnthropic(api_key=api_key)
    
    # Add JSON enforcement to system message if needed
    if response_format == "json":
        system_msg = "Respond with ONLY valid JSON. No preamble, no markdown, no explanation."
        # Prepend to first message or add as system parameter
    
    # Use Claude Haiku for cost efficiency
    model = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")
    
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            system=system_msg if response_format == "json" else None
        )
        
        return {
            "content": response.content[0].text,
            "provider": "claude",
            "model": model,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens
            }
        }
    except anthropic.RateLimitError as e:
        raise RuntimeError(f"Claude rate limit exceeded: {e}")
    except anthropic.APIError as e:
        raise RuntimeError(f"Claude API error: {e}")
```

**File: backend/app/llm/providers/openai.py**

```python
import os
from openai import AsyncOpenAI
from typing import Any

async def call_openai(
    messages: list[dict[str, str]],
    response_format: str,
    max_tokens: int,
    temperature: float
) -> dict[str, Any]:
    """Call OpenAI API."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not configured")
    
    client = AsyncOpenAI(api_key=api_key)
    
    # Add JSON enforcement to system message
    if response_format == "json":
        messages = [
            {"role": "system", "content": "Respond with ONLY valid JSON. No preamble, no markdown."},
            *messages
        ]
    
    # Use GPT-3.5 Turbo for cost efficiency
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"} if response_format == "json" else None
        )
        
        return {
            "content": response.choices[0].message.content,
            "provider": "openai",
            "model": model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}")
```


### Classification Models

**File: backend/app/llm/models.py**

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal

# Valid clause types
ClauseType = Literal[
    "payment_terms",
    "termination",
    "liability",
    "confidentiality",
    "intellectual_property",
    "dispute_resolution",
    "term_duration",
    "renewal",
    "indemnification",
    "warranties",
    "force_majeure",
    "other"
]

class ClauseClassification(BaseModel):
    """LLM response schema for clause classification."""
    clause_type: ClauseType
    key_entities: list[str] = Field(
        description="List of key entities mentioned (names, dates, amounts, etc.)"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0"
    )
    
    @field_validator("key_entities")
    @classmethod
    def validate_entities(cls, v: list[str]) -> list[str]:
        """Ensure entities list is reasonable."""
        if len(v) > 20:  # Sanity check
            return v[:20]
        return v

class ClassificationResult(BaseModel):
    """Internal result including metadata."""
    clause_id: str
    classification: ClauseClassification
    tokens_used: int
    processing_time_ms: int
```


### Clause Classification Logic

**File: backend/app/llm/classify_clauses.py**

```python
import asyncio
import json
import re
from typing import Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from .llm_client import call_llm
from .models import ClauseClassification, ClassificationResult
from ..rag.prompt_builder import build_classification_prompt
from ..db.models import Clause

async def classify_clause(
    clause_text: str,
    clause_index: str,
    contract_type: str,
    retrieved_context: str = ""
) -> ClauseClassification:
    """
    Classify a single clause using LLM.
    
    Args:
        clause_text: The clause content
        clause_index: Clause identifier (e.g., "1.1")
        contract_type: "rental" or "freelance"
        retrieved_context: RAG context (empty for now, filled in stage 5)
    
    Returns:
        ClauseClassification with type, entities, confidence
    
    Raises:
        RuntimeError: If classification fails after retry
    """
    # Build prompt using template from stage 3
    messages = build_classification_prompt(
        clause_text=clause_text,
        clause_index=clause_index,
        contract_type=contract_type,
        retrieved_context=retrieved_context
    )
    
    # Try classification
    try:
        response = await call_llm(messages, response_format="json")
        parsed = _parse_classification_response(response["content"])
        return parsed
    except (json.JSONDecodeError, ValueError) as e:
        # Retry with emphatic instruction
        logger.warning(f"Malformed JSON for clause {clause_index}, retrying")
        retry_messages = _add_emphatic_json_instruction(messages)
        
        try:
            response = await call_llm(retry_messages, response_format="json")
            parsed = _parse_classification_response(response["content"])
            return parsed
        except Exception as retry_error:
            raise RuntimeError(
                f"Classification failed after retry for clause {clause_index}: {retry_error}"
            )

def _parse_classification_response(content: str) -> ClauseClassification:
    """Parse and validate LLM JSON response."""
    # Strip common markdown artifacts
    content = re.sub(r'^```json\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    content = content.strip()
    
    # Parse JSON
    data = json.loads(content)
    
    # Validate with Pydantic
    return ClauseClassification(**data)
```


def _add_emphatic_json_instruction(messages: list[dict]) -> list[dict]:
    """Add emphatic JSON-only instruction for retry."""
    emphatic = (
        "CRITICAL: You MUST respond with ONLY valid JSON. "
        "No text before or after. No markdown. No explanation. "
        "Just the JSON object."
    )
    
    # Prepend to first user message
    new_messages = messages.copy()
    if new_messages and new_messages[0]["role"] == "user":
        new_messages[0]["content"] = emphatic + "\n\n" + new_messages[0]["content"]
    
    return new_messages

async def classify_all_clauses(
    contract_id: str,
    contract_type: str,
    db: AsyncSession
) -> dict[str, Any]:
    """
    Classify all clauses for a contract concurrently.
    
    Args:
        contract_id: Contract UUID
        contract_type: "rental" or "freelance"
        db: Database session
    
    Returns:
        {
            "total": int,
            "successful": int,
            "failed": int,
            "total_tokens": int
        }
    """
    # Fetch clauses from DB
    result = await db.execute(
        select(Clause)
        .where(Clause.contract_id == contract_id)
        .order_by(Clause.position)
    )
    clauses = result.scalars().all()
    
    if not clauses:
        return {"total": 0, "successful": 0, "failed": 0, "total_tokens": 0}
    
    # Concurrency limit (prevent rate limit issues)
    concurrency_limit = int(os.getenv("LLM_CONCURRENCY_LIMIT", "5"))
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    total_tokens = 0
    successful = 0
    failed = 0
    
    async def classify_and_store(clause: Clause) -> None:
        """Classify single clause and store result."""
        nonlocal total_tokens, successful, failed
        
        async with semaphore:
            try:
                start_time = datetime.utcnow()
                
                classification = await classify_clause(
                    clause_text=clause.clause_text,
                    clause_index=clause.clause_number,
                    contract_type=contract_type,
                    retrieved_context=""  # Filled in stage 5
                )
                
                processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                # Update database
                clause.clause_type = classification.clause_type
                clause.key_entities = classification.key_entities
                clause.confidence = classification.confidence
                clause.classified_at = datetime.utcnow()
                
                successful += 1
                
                logger.debug(
                    f"Classified clause {clause.clause_number}: {classification.clause_type}"
                )
                
            except Exception as e:
                # Mark as failed but continue
                clause.classification_error = str(e)
                failed += 1
                logger.error(f"Failed to classify clause {clause.clause_number}: {e}")
    
    # Process all clauses concurrently
    tasks = [classify_and_store(clause) for clause in clauses]
    await asyncio.gather(*tasks)
    
    # Commit all updates in single transaction
    await db.commit()
    
    logger.info(
        f"Classification complete for contract {contract_id}: "
        f"{successful} successful, {failed} failed"
    )
    
    return {
        "total": len(clauses),
        "successful": successful,
        "failed": failed,
        "total_tokens": total_tokens
    }
```


### Database Schema Updates

**Alembic Migration:** `backend/alembic/versions/002_add_classification_fields.py`

```sql
-- Add classification fields to clauses table
ALTER TABLE clauses ADD COLUMN clause_type VARCHAR(50);
ALTER TABLE clauses ADD COLUMN key_entities JSONB;
ALTER TABLE clauses ADD COLUMN confidence FLOAT;
ALTER TABLE clauses ADD COLUMN classification_error TEXT;
ALTER TABLE clauses ADD COLUMN classified_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_clauses_type ON clauses(clause_type);
CREATE INDEX idx_clauses_confidence ON clauses(confidence);
```

**Updated SQLAlchemy Model:**

```python
class Clause(Base):
    __tablename__ = "clauses"
    
    # ... existing fields ...
    
    # Classification fields (added)
    clause_type = Column(String(50), nullable=True)
    key_entities = Column(JSONB, nullable=True)
    confidence = Column(Float, nullable=True)
    classification_error = Column(Text, nullable=True)
    classified_at = Column(DateTime(timezone=True), nullable=True)
```

## Environment Variables

**Required (.env):**
```bash
# LLM Provider Selection
LLM_PROVIDER=claude  # or "openai"

# Claude Configuration
CLAUDE_API_KEY=sk-ant-xxx
CLAUDE_MODEL=claude-3-haiku-20240307  # Cost-efficient model

# OpenAI Configuration
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-3.5-turbo  # Cost-efficient model

# Performance Tuning
LLM_CONCURRENCY_LIMIT=5  # Max concurrent LLM calls
LLM_MAX_RETRIES=3        # Max retries for transient failures
LLM_TIMEOUT_SECONDS=30   # Request timeout
```


## Test Plan

### Test Strategy

**Mock LLM Client:**
- Create `backend/tests/mocks/mock_llm.py`
- Returns predefined JSON responses
- No real API calls during tests
- Simulate success, malformed JSON, and API errors

### Test Cases

**Test File:** `backend/tests/test_llm_client.py`

**TC-1: LLM Client - Provider Selection**
- Set `LLM_PROVIDER=claude`, verify Claude client used
- Set `LLM_PROVIDER=openai`, verify OpenAI client used
- Set invalid provider, verify ValueError raised

**TC-2: LLM Client - Missing API Key**
- Unset `CLAUDE_API_KEY`, verify ValueError on Claude call
- Unset `OPENAI_API_KEY`, verify ValueError on OpenAI call

**TC-3: LLM Client - JSON Response Format**
- Request `response_format="json"`
- Verify system message includes JSON instruction
- Verify response contains content and usage stats

**Test File:** `backend/tests/test_classify_clauses.py`

**TC-4: Single Clause Classification - Success**
- Mock LLM returns valid JSON with all required fields
- Verify ClauseClassification parsed correctly
- Verify clause_type in allowed taxonomy
- Verify confidence between 0.0 and 1.0

**TC-5: Single Clause Classification - Malformed JSON (First Try)**
- Mock LLM returns JSON with markdown artifacts: ```json {...} ```
- Verify markdown stripped successfully
- Verify classification succeeds

**TC-6: Single Clause Classification - Malformed JSON (Retry)**
- Mock LLM returns invalid JSON on first call
- Returns valid JSON on retry
- Verify retry logic triggered
- Verify emphatic instruction added
- Verify classification succeeds


**TC-7: Single Clause Classification - Failure After Retry**
- Mock LLM returns invalid JSON on both attempts
- Verify RuntimeError raised
- Verify error message includes clause_index

**TC-8: Batch Classification - All Successful**
- Create contract with 10 clauses in test DB
- Mock all LLM calls to return valid JSON
- Call `classify_all_clauses()`
- Verify all 10 clauses classified
- Verify database updated with clause_type, key_entities, confidence
- Verify result: {"successful": 10, "failed": 0}

**TC-9: Batch Classification - Partial Failure**
- Create contract with 10 clauses
- Mock LLM: 8 succeed, 2 fail
- Call `classify_all_clauses()`
- Verify 8 clauses classified successfully
- Verify 2 clauses have `classification_error` populated
- Verify result: {"successful": 8, "failed": 2}
- Verify processing continues despite failures

**TC-10: Batch Classification - Concurrency Limit**
- Create contract with 20 clauses
- Set `LLM_CONCURRENCY_LIMIT=5`
- Track concurrent LLM calls
- Verify max 5 calls happen simultaneously
- Verify all clauses eventually processed

**TC-11: Response Schema Validation**
- Mock LLM returns JSON with invalid clause_type (not in taxonomy)
- Verify Pydantic validation error raised
- Mock LLM returns confidence=1.5 (>1.0)
- Verify Pydantic validation error raised

**TC-12: Token Usage Tracking**
- Mock LLM returns usage stats: {"prompt_tokens": 100, "completion_tokens": 50}
- Classify single clause
- Verify token counts logged/tracked


### Mock Implementation

**File: backend/tests/mocks/mock_llm.py**

```python
from typing import Any

class MockLLMClient:
    """Mock LLM client for testing without real API calls."""
    
    def __init__(self, responses: list[dict] = None, fail_count: int = 0):
        """
        Args:
            responses: List of mock responses to return in order
            fail_count: Number of calls that should fail before succeeding
        """
        self.responses = responses or []
        self.fail_count = fail_count
        self.call_count = 0
    
    async def call_llm(
        self,
        messages: list[dict],
        response_format: str = "json",
        **kwargs
    ) -> dict[str, Any]:
        """Mock LLM call."""
        self.call_count += 1
        
        # Simulate failures
        if self.call_count <= self.fail_count:
            raise RuntimeError("Simulated API failure")
        
        # Return next response
        if self.responses:
            response = self.responses.pop(0)
            return {
                "content": response["content"],
                "provider": "mock",
                "model": "mock-model",
                "usage": response.get("usage", {
                    "prompt_tokens": 100,
                    "completion_tokens": 50
                })
            }
        
        # Default successful response
        return {
            "content": '{"clause_type": "other", "key_entities": [], "confidence": 0.5}',
            "provider": "mock",
            "model": "mock-model",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

# Predefined mock responses
MOCK_VALID_RESPONSE = {
    "content": '{"clause_type": "payment_terms", "key_entities": ["$1000", "monthly"], "confidence": 0.95}'
}

MOCK_MALFORMED_JSON = {
    "content": '```json\n{"clause_type": "payment_terms", "key_entities": [], "confidence": 0.9}\n```'
}

MOCK_INVALID_JSON = {
    "content": 'This is not JSON at all'
}
```


## Dependencies

**Python Packages (backend/requirements.txt):**
```
# LLM SDKs
anthropic>=0.25.0     # Claude API
openai>=1.30.0        # OpenAI API

# Async utilities
asyncio-throttle>=1.0.0  # Rate limiting
tenacity>=8.2.0          # Retry logic with backoff

# Already included from previous specs:
# sqlalchemy, pydantic, langchain, etc.
```

## Integration with Pipeline

**Updated Processing Flow:**

After Stage 2 (Document Processing) completes:

```python
async def process_contract(contract_id: UUID, file_path: str, db: AsyncSession):
    """Extended pipeline including classification."""
    
    # Stage 2: Extract and segment (existing)
    # ... extraction code ...
    
    # Stage 4: Classify clauses (new)
    from app.llm.classify_clauses import classify_all_clauses
    
    classification_result = await classify_all_clauses(
        contract_id=str(contract_id),
        contract_type=detect_contract_type(normalized_text),  # Helper function
        db=db
    )
    
    logger.info(
        f"Classification complete: {classification_result['successful']} successful, "
        f"{classification_result['failed']} failed"
    )
    
    # Continue to Stage 5 (RAG lookup)...
```


## Files to Create/Modify

### New Files

**LLM Module:**
1. `backend/app/llm/__init__.py`
2. `backend/app/llm/llm_client.py` - Universal LLM wrapper
3. `backend/app/llm/classify_clauses.py` - Classification logic
4. `backend/app/llm/models.py` - Pydantic models
5. `backend/app/llm/providers/__init__.py`
6. `backend/app/llm/providers/claude.py` - Claude API implementation
7. `backend/app/llm/providers/openai.py` - OpenAI API implementation

**Database:**
8. `backend/alembic/versions/002_add_classification_fields.py` - Migration

**Tests:**
9. `backend/tests/test_llm_client.py` - LLM client tests
10. `backend/tests/test_classify_clauses.py` - Classification tests
11. `backend/tests/mocks/mock_llm.py` - Mock LLM for tests

### Modified Files

12. `backend/app/db/models.py` - Add classification fields to Clause model
13. `backend/app/document_processing/pipeline.py` - Integrate classification step
14. `backend/requirements.txt` - Add anthropic, openai packages
15. `backend/.env.example` - Document LLM env vars

## Error Handling Strategy

**Error Categories:**

1. **Transient Errors (Retry):**
   - API rate limits (429)
   - Timeouts
   - Network errors
   - Action: Exponential backoff, max 3 retries

2. **Malformed Response (Retry Once):**
   - Invalid JSON
   - Missing required fields
   - Action: Single retry with emphatic instruction

3. **Configuration Errors (Fail Fast):**
   - Missing API key
   - Invalid provider selection
   - Action: Raise ValueError at startup

4. **Individual Clause Failure (Continue):**
   - Classification fails after retries
   - Action: Mark clause as failed, continue with others

5. **Complete Contract Failure (Escalate):**
   - All clauses fail
   - Database errors
   - Action: Set contract status to "classification_failed"


## Performance Optimization

**Concurrency Strategy:**
- Process 5 clauses simultaneously by default
- Configurable via `LLM_CONCURRENCY_LIMIT`
- Balance: avoid rate limits vs maximize throughput

**Cost Optimization:**
- Use cost-efficient models (Haiku, GPT-3.5)
- Temperature=0.0 for deterministic, faster responses
- Cache prompt templates to reduce repeated formatting

**Token Usage Tracking:**
```python
# Log token usage per contract for monitoring
logger.info(
    f"Contract {contract_id} classification: "
    f"{total_tokens} tokens used, "
    f"estimated cost: ${total_tokens * 0.00001:.4f}"
)
```

## Security Considerations

**SC-1: API Key Protection**
- Keys stored in environment only, never in code
- Never log API keys or include in error messages
- Validate key format before first API call

**SC-2: Content Privacy**
- Clause text sent to external LLM APIs (Claude/OpenAI)
- User must consent to this in terms of service
- Consider on-premise LLM option for sensitive contracts (future)

**SC-3: Response Validation**
- Strictly validate LLM responses with Pydantic
- Reject responses with unexpected fields
- Prevent injection attacks via schema enforcement

**SC-4: Rate Limit Protection**
- Concurrency limits prevent account suspension
- Exponential backoff on rate limit errors
- Monitor API usage to stay within quotas


## Design Tradeoffs

### Concurrent vs Sequential Processing

**Chosen: Concurrent with Semaphore**

**Pros:**
- 5-10x faster for multi-clause contracts
- Better user experience (faster results)
- Efficient use of async capabilities

**Cons:**
- More complex error handling
- Risk of rate limit violations (mitigated by semaphore)
- Higher memory usage during processing

**Alternative Considered:** Sequential processing
- Simpler but 5-10x slower
- Not acceptable for 50+ clause contracts

### JSON Response Format

**Chosen: Structured JSON with Pydantic validation**

**Pros:**
- Type-safe, validated responses
- Easy to parse and store in database
- Claude and OpenAI both support JSON mode

**Cons:**
- Requires retry logic for malformed JSON
- LLM may include markdown formatting (mitigated by stripping)

**Alternative Considered:** Free-text parsing
- More flexible but unreliable
- Would require complex regex/NLP parsing

### Single LLM Client vs Provider-Specific Modules

**Chosen: Single client with provider abstraction**

**Pros:**
- Easy to swap providers via env var
- Consistent interface across codebase
- Isolates provider-specific logic

**Cons:**
- Slightly more complex initial implementation
- Must maintain compatibility across providers

**Future Extension:** Add support for:
- Azure OpenAI
- Local models (Ollama, LLaMA)
- Custom fine-tuned models


## Out of Scope

**Explicitly NOT included in this spec:**
- RAG context retrieval (stages 5A/5B) - separate spec
- Risk detection LLM calls (stage 7) - separate spec
- Fine-tuning custom classification models
- Prompt optimization or A/B testing
- User feedback loop for improving classifications
- Caching of classification results for similar clauses
- Support for languages other than English
- Streaming LLM responses
- Multi-model ensemble classification

## Success Criteria

- [ ] LLM client abstracts Claude and OpenAI APIs
- [ ] Provider selected via `LLM_PROVIDER` env var
- [ ] `call_llm()` returns structured response with content and usage
- [ ] `classify_clause()` parses JSON response into ClauseClassification
- [ ] Malformed JSON triggers single retry with emphatic instruction
- [ ] JSON markdown artifacts (```json) stripped successfully
- [ ] `classify_all_clauses()` processes clauses concurrently
- [ ] Concurrency limited to 5 simultaneous calls (configurable)
- [ ] Individual clause failures don't fail entire contract
- [ ] Classification results persisted to `clauses` table
- [ ] Database updated with clause_type, key_entities, confidence
- [ ] All 12 test cases pass with mocked LLM
- [ ] No real API calls during tests
- [ ] Token usage tracked and logged
- [ ] API keys never logged or exposed in errors

## Notes

- This spec covers Stage 4 (Clause Classification) of the ScanTract pipeline
- Stage 3 (Prompt Templating) provides `build_classification_prompt()`
- Stages 5A/5B (RAG Retrieval) will fill the `retrieved_context` parameter
- Stage 7 (Risk Detection) will use similar LLM client for different prompts
- Use Conventional Commits: `feat:` for new features, `test:` for tests

## References

- Claude API docs: https://docs.anthropic.com/claude/reference/
- OpenAI API docs: https://platform.openai.com/docs/api-reference
- LangChain prompts: https://python.langchain.com/docs/modules/model_io/prompts/
- Pydantic validation: https://docs.pydantic.dev/latest/
