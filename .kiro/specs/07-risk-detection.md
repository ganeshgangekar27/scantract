# Spec: Risk & Missing Clause Detection

## Overview
Build the risk detection layer for ScanTract — Stage 7 of the core pipeline that analyzes classified clauses with merged context from legal rules and reference corpus, identifies risky clauses, detects missing clauses, assigns severity scores, and ensures every finding is traceable to a specific legal rule or reference example.

## Scope
- Risk detection function analyzing full contract with merged context
- LLM-powered analysis using Stage 3 risk prompt template
- Strict JSON response schema with mandatory traceability fields
- Validation and retry logic for untraceable findings
- Database persistence of risk findings
- Unit tests with mocked LLM enforcing traceability requirement

## Requirements

### Functional Requirements

**FR-1: Risk Detection Function**
- Function: `detect_risks(contract_id, db) -> RiskDetectionResult`
- Load all classified clauses for contract from database
- Retrieve merged context from Stage 6 (legal rules + reference corpus)
- Build risk prompt using Stage 3's `build_risk_prompt()`
- Call LLM with strict JSON response format
- Parse and validate response
- Persist findings to database

**FR-2: LLM Response Schema**
- Strict JSON output required:
  ```json
  {
    "risky_clauses": [
      {
        "clause_id": "string",
        "reason": "string",
        "triggering_rule_or_corpus": "string",
        "severity": "low" | "medium" | "high"
      }
    ],
    "missing_clauses": [
      {
        "expected_clause_type": "string",
        "why_expected": "string",
        "triggering_rule_or_corpus": "string",
        "severity": "low" | "medium" | "high"
      }
    ]
  }
  ```


**FR-3: Traceability Requirement (CRITICAL)**
- **EVERY** risky_clause entry MUST have non-empty `triggering_rule_or_corpus`
- **EVERY** missing_clause entry MUST have non-empty `triggering_rule_or_corpus`
- This field must reference a specific source from Stage 6 merged context
- Examples:
  - "Model Tenancy Act 2021, Section 7(1)"
  - "Standard practice - fair deposit terms"
- If LLM returns entry without this field: reject response and retry once
- If retry fails: log error and mark finding as "unverified" (don't save to DB)
- This requirement is NON-NEGOTIABLE per product rules (no untraceable flags)

**FR-4: Severity Scoring**
- Three levels: "low", "medium", "high"
- Severity based on:
  - Legal compliance: violations = high, deviations = medium
  - Standard practice: significant deviation = medium, minor = low
  - Financial impact: large amounts = high, moderate = medium
  - Rights impact: fundamental rights = high, procedural = low
- LLM determines severity based on context and reasoning

**FR-5: Database Persistence**
- Table: `risk_findings`
- Link to contract via `contract_id`
- Store both risky clauses and missing clauses
- Include full traceability chain (clause_id → rule/corpus → finding)
- Timestamp all findings

**FR-6: Error Handling**
- Handle malformed JSON (retry once with emphatic instruction)
- Handle missing traceability fields (reject and retry)
- Handle invalid severity values (reject and retry)
- Handle invalid clause_id references (log warning but continue)
- If all retries exhausted: mark contract risk detection as "failed"

**FR-7: Prompt Construction**
- Use Stage 3's `build_risk_prompt()` template
- Include:
  - Full list of classified clauses with their types
  - Merged context from Stage 6 (legal rules + corpus examples)
  - Contract type (rental/freelance)
  - Instructions: no legal advice, always cite sources, use severity scores


### Non-Functional Requirements

**NFR-1: Performance**
- Risk detection for 50-clause contract: <60 seconds
- Single LLM call per contract (not per clause)
- Database writes batched (single transaction)

**NFR-2: Accuracy**
- Traceability validation catches 100% of omissions
- Severity scoring consistent with legal importance
- False positive rate acceptable (user reviews findings)

**NFR-3: Reliability**
- Retry logic handles transient LLM failures
- Individual untraceable findings don't fail entire contract
- Partial results saved (e.g., risky clauses even if missing clauses fail)

**NFR-4: Type Safety**
- All functions use type hints (Python 3.11+)
- Pydantic models for risk findings
- Strict enum for severity levels

**NFR-5: Traceability Audit**
- Every finding traceable to source in logs
- Audit trail for debugging citation issues
- Untraceable findings logged with warning

## Technical Design

### Module Structure

**Location:** `backend/app/llm/`

```
backend/app/llm/
├── __init__.py
├── llm_client.py          # Universal LLM wrapper (from Stage 4)
├── classify_clauses.py    # Clause classification (from Stage 4)
├── detect_risk.py         # Risk detection (NEW)
└── models.py              # Pydantic models (EXTENDED)
```

### Data Models

**File: backend/app/llm/models.py (extended)**

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from enum import Enum

class Severity(str, Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class RiskyClauseFinding(BaseModel):
    """A risky clause identified by the LLM."""
    clause_id: str = Field(description="Clause identifier from contract")
    reason: str = Field(min_length=10, description="Explanation of why clause is risky")
    triggering_rule_or_corpus: str = Field(
        min_length=1,
        description="REQUIRED: Specific legal rule or corpus reference that triggered this flag"
    )
    severity: Severity
    
    @field_validator("triggering_rule_or_corpus")
    @classmethod
    def validate_traceability(cls, v: str) -> str:
        """Ensure traceability field is not empty."""
        if not v or v.strip() == "":
            raise ValueError("triggering_rule_or_corpus cannot be empty - traceability is mandatory")
        return v.strip()

class MissingClauseFinding(BaseModel):
    """A missing clause identified by the LLM."""
    expected_clause_type: str = Field(description="Type of clause that should be present")
    why_expected: str = Field(min_length=10, description="Explanation of why clause is expected")
    triggering_rule_or_corpus: str = Field(
        min_length=1,
        description="REQUIRED: Specific legal rule or corpus reference that triggered this flag"
    )
    severity: Severity
    
    @field_validator("triggering_rule_or_corpus")
    @classmethod
    def validate_traceability(cls, v: str) -> str:
        """Ensure traceability field is not empty."""
        if not v or v.strip() == "":
            raise ValueError("triggering_rule_or_corpus cannot be empty - traceability is mandatory")
        return v.strip()
```


**File: backend/app/llm/models.py (continued)**

```python
class RiskDetectionResponse(BaseModel):
    """LLM response schema for risk detection."""
    risky_clauses: list[RiskyClauseFinding] = Field(default_factory=list)
    missing_clauses: list[MissingClauseFinding] = Field(default_factory=list)
    
    @field_validator("risky_clauses", "missing_clauses")
    @classmethod
    def validate_findings_not_empty(cls, v: list) -> list:
        """At least one type of finding should be present (or explicitly empty)."""
        # This allows empty lists but validates structure
        return v

class RiskDetectionResult(BaseModel):
    """Complete result of risk detection for a contract."""
    contract_id: str
    risky_clauses: list[RiskyClauseFinding]
    missing_clauses: list[MissingClauseFinding]
    total_risks: int
    total_missing: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int
    processed_at: str  # ISO timestamp
    
    def summary(self) -> str:
        """Human-readable summary."""
        return (
            f"Risk Detection: {self.total_risks} risky clauses, "
            f"{self.total_missing} missing clauses "
            f"(High: {self.high_severity_count}, Med: {self.medium_severity_count}, Low: {self.low_severity_count})"
        )
```

### Database Schema

**Alembic Migration:** `backend/alembic/versions/005_create_risk_findings.py`

```sql
-- Create risk_findings table
CREATE TABLE risk_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    finding_type VARCHAR(20) NOT NULL,  -- 'risky_clause' or 'missing_clause'
    
    -- For risky clauses
    clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,
    
    -- For missing clauses
    expected_clause_type VARCHAR(100),
    
    -- Common fields
    reason TEXT NOT NULL,
    triggering_rule_or_corpus TEXT NOT NULL,  -- MANDATORY per product rules
    severity VARCHAR(10) NOT NULL,  -- 'low', 'medium', 'high'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_finding_type CHECK (finding_type IN ('risky_clause', 'missing_clause')),
    CONSTRAINT valid_severity CHECK (severity IN ('low', 'medium', 'high')),
    CONSTRAINT risky_clause_has_id CHECK (
        finding_type = 'missing_clause' OR clause_id IS NOT NULL
    ),
    CONSTRAINT missing_clause_has_type CHECK (
        finding_type = 'risky_clause' OR expected_clause_type IS NOT NULL
    )
);

-- Indexes for performance
CREATE INDEX idx_risk_findings_contract ON risk_findings(contract_id);
CREATE INDEX idx_risk_findings_severity ON risk_findings(severity);
CREATE INDEX idx_risk_findings_type ON risk_findings(finding_type);
CREATE INDEX idx_risk_findings_clause ON risk_findings(clause_id) WHERE clause_id IS NOT NULL;
```


**SQLAlchemy Model (backend/app/db/models.py - extended):**

```python
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

class RiskFinding(Base):
    __tablename__ = "risk_findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    finding_type = Column(String(20), nullable=False)  # 'risky_clause' or 'missing_clause'
    
    # For risky clauses
    clause_id = Column(UUID(as_uuid=True), ForeignKey("clauses.id", ondelete="SET NULL"), nullable=True)
    
    # For missing clauses
    expected_clause_type = Column(String(100), nullable=True)
    
    # Common fields
    reason = Column(Text, nullable=False)
    triggering_rule_or_corpus = Column(Text, nullable=False)
    severity = Column(String(10), nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="risk_findings")
    clause = relationship("Clause", foreign_keys=[clause_id])
    
    __table_args__ = (
        CheckConstraint(
            "finding_type IN ('risky_clause', 'missing_clause')",
            name="valid_finding_type"
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="valid_severity"
        ),
        CheckConstraint(
            "finding_type = 'missing_clause' OR clause_id IS NOT NULL",
            name="risky_clause_has_id"
        ),
        CheckConstraint(
            "finding_type = 'risky_clause' OR expected_clause_type IS NOT NULL",
            name="missing_clause_has_type"
        ),
    )

# Update Contract model to include relationship
class Contract(Base):
    # ... existing fields ...
    risk_findings = relationship("RiskFinding", back_populates="contract", cascade="all, delete-orphan")
```


### Core Risk Detection Logic

**File: backend/app/llm/detect_risk.py**

```python
"""
Risk and missing clause detection for ScanTract Stage 7.

Analyzes contracts with merged legal + corpus context,
identifies risky clauses and missing clauses, ensures
traceability for all findings.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .llm_client import call_llm
from .models import RiskDetectionResponse, RiskDetectionResult, Severity
from ..db.models import Contract, Clause, RiskFinding
from ..rag.merge_context import merge_retrieval_results, format_merged_context
from ..rag.prompt_builder import build_risk_prompt
from ..db.legal_kb.search import search_legal_rules
from ..db.reference_corpus.search import search_reference_corpus

logger = logging.getLogger(__name__)

async def detect_risks(
    contract_id: str,
    db: AsyncSession
) -> RiskDetectionResult:
    """
    Detect risky and missing clauses for a contract.
    
    Args:
        contract_id: Contract UUID
        db: Database session
    
    Returns:
        RiskDetectionResult with all findings
    
    Raises:
        ValueError: If contract not found or not processed
        RuntimeError: If risk detection fails after retries
    """
    # Step 1: Load contract and clauses
    contract = await _load_contract(contract_id, db)
    clauses = await _load_clauses(contract_id, db)
    
    if not clauses:
        logger.warning(f"Contract {contract_id} has no clauses to analyze")
        return _empty_result(contract_id)
    
    logger.info(f"Analyzing {len(clauses)} clauses for contract {contract_id}")
    
    # Step 2: Retrieve merged context (Stage 5A + 5B + Stage 6)
    # Note: For comprehensive analysis, we retrieve context based on all clauses
    merged_context = await _retrieve_merged_context_for_contract(
        clauses=clauses,
        contract_type=contract.contract_type,
        state=contract.state,
        db=db
    )
    
    # Step 3: Build risk detection prompt
    prompt_messages = build_risk_prompt(
        clauses_list=[
            {
                "clause_id": c.clause_number,
                "clause_type": c.clause_type or "unknown",
                "clause_text": c.clause_text
            }
            for c in clauses
        ],
        legal_context=merged_context,
        contract_type=contract.contract_type
    )
    
    # Step 4: Call LLM with retry logic
    response = await _call_llm_with_traceability_validation(prompt_messages)
    
    # Step 5: Persist findings to database
    await _persist_findings(contract_id, response, clauses, db)
    
    # Step 6: Build result summary
    result = _build_result(contract_id, response)
    
    logger.info(f"Risk detection complete: {result.summary()}")
    
    return result
```


### Traceability Validation & Retry Logic

**File: backend/app/llm/detect_risk.py (continued)**

```python
async def _call_llm_with_traceability_validation(
    messages: list[dict],
    max_retries: int = 2
) -> RiskDetectionResponse:
    """
    Call LLM with strict validation of traceability requirement.
    
    Retries if:
    - JSON is malformed
    - Required fields missing
    - triggering_rule_or_corpus is empty (CRITICAL)
    
    Args:
        messages: Prompt messages
        max_retries: Maximum retry attempts
    
    Returns:
        Validated RiskDetectionResponse
    
    Raises:
        RuntimeError: If validation fails after all retries
    """
    for attempt in range(max_retries):
        try:
            # Call LLM
            response = await call_llm(
                messages=messages,
                response_format="json",
                max_tokens=2000,
                temperature=0.0
            )
            
            # Parse JSON
            parsed = _parse_risk_response(response["content"])
            
            # Validate with Pydantic (includes traceability validation)
            validated = RiskDetectionResponse(**parsed)
            
            # Additional traceability check (paranoid validation)
            _validate_all_findings_traceable(validated)
            
            logger.info(
                f"Risk detection successful: {len(validated.risky_clauses)} risky, "
                f"{len(validated.missing_clauses)} missing"
            )
            
            return validated
            
        except json.JSONDecodeError as e:
            logger.warning(f"Attempt {attempt + 1}: Malformed JSON - {e}")
            if attempt < max_retries - 1:
                messages = _add_emphatic_json_instruction(messages)
            else:
                raise RuntimeError(f"Risk detection failed: malformed JSON after {max_retries} attempts")
        
        except ValueError as e:
            # Pydantic validation error (likely missing traceability)
            logger.warning(f"Attempt {attempt + 1}: Validation error - {e}")
            if "triggering_rule_or_corpus" in str(e):
                logger.error("TRACEABILITY VIOLATION: LLM returned finding without citation")
                if attempt < max_retries - 1:
                    messages = _add_traceability_emphasis(messages)
                else:
                    raise RuntimeError(
                        f"Risk detection failed: LLM unable to provide traceable findings "
                        f"after {max_retries} attempts. This violates product requirements."
                    )
            else:
                raise RuntimeError(f"Risk detection validation failed: {e}")
        
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}: Unexpected error - {e}")
            if attempt >= max_retries - 1:
                raise RuntimeError(f"Risk detection failed: {e}")
    
    raise RuntimeError("Risk detection failed after all retries")

def _validate_all_findings_traceable(response: RiskDetectionResponse) -> None:
    """
    Paranoid validation: ensure ALL findings have non-empty traceability.
    
    This is redundant with Pydantic validation but provides extra safety
    for our critical traceability requirement.
    """
    for risky in response.risky_clauses:
        if not risky.triggering_rule_or_corpus or risky.triggering_rule_or_corpus.strip() == "":
            raise ValueError(
                f"Risky clause '{risky.clause_id}' missing triggering_rule_or_corpus"
            )
    
    for missing in response.missing_clauses:
        if not missing.triggering_rule_or_corpus or missing.triggering_rule_or_corpus.strip() == "":
            raise ValueError(
                f"Missing clause '{missing.expected_clause_type}' missing triggering_rule_or_corpus"
            )
    
    logger.debug(
        f"Traceability validation passed: {len(response.risky_clauses) + len(response.missing_clauses)} findings"
    )

def _add_traceability_emphasis(messages: list[dict]) -> list[dict]:
    """Add emphatic instruction about traceability requirement."""
    emphasis = (
        "\n\n🚨 CRITICAL REQUIREMENT: Every finding MUST include 'triggering_rule_or_corpus' "
        "with the EXACT citation from the context above. Examples:\n"
        "- 'Model Tenancy Act 2021, Section 7(1)'\n"
        "- 'Standard practice - fair deposit terms'\n\n"
        "Findings without this field will be REJECTED. Copy the citation verbatim from the context."
    )
    
    new_messages = messages.copy()
    if new_messages and new_messages[-1]["role"] == "user":
        new_messages[-1]["content"] += emphasis
    
    return new_messages
```


### Helper Functions

**File: backend/app/llm/detect_risk.py (continued)**

```python
async def _load_contract(contract_id: str, db: AsyncSession) -> Contract:
    """Load contract from database."""
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")
    
    if contract.processing_status != "completed":
        raise ValueError(
            f"Contract {contract_id} not ready for risk detection "
            f"(status: {contract.processing_status})"
        )
    
    return contract

async def _load_clauses(contract_id: str, db: AsyncSession) -> list[Clause]:
    """Load classified clauses for contract."""
    result = await db.execute(
        select(Clause)
        .where(Clause.contract_id == contract_id)
        .where(Clause.clause_type.isnot(None))  # Only classified clauses
        .order_by(Clause.position)
    )
    return result.scalars().all()

async def _retrieve_merged_context_for_contract(
    clauses: list[Clause],
    contract_type: str,
    state: str | None,
    db: AsyncSession
) -> str:
    """
    Retrieve and merge context for entire contract.
    
    Strategy: Search based on all clause texts, then merge and dedupe.
    This gives comprehensive context for the full contract analysis.
    """
    from ..rag.merge_context import merge_retrieval_results, format_merged_context
    
    # Aggregate searches (could optimize with batching in future)
    all_legal_results = []
    all_corpus_results = []
    
    for clause in clauses[:10]:  # Limit to first 10 to avoid excessive API calls
        # Stage 5A: Legal rules
        legal_results = await search_legal_rules(
            clause_text=clause.clause_text,
            state=state,
            top_k=3,  # Fewer per clause since we're aggregating
            db=db
        )
        all_legal_results.extend(legal_results)
        
        # Stage 5B: Reference corpus
        corpus_results = await search_reference_corpus(
            clause_text=clause.clause_text,
            contract_type=contract_type,
            top_k=3,
            db=db
        )
        all_corpus_results.extend(corpus_results)
    
    # Stage 6: Merge and deduplicate
    merge_result = merge_retrieval_results(all_legal_results, all_corpus_results)
    
    # Format for prompt
    return format_merged_context(merge_result)

def _parse_risk_response(content: str) -> dict:
    """Parse LLM JSON response, stripping markdown if present."""
    # Strip markdown artifacts
    content = re.sub(r'^```json\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    content = content.strip()
    
    return json.loads(content)

def _add_emphatic_json_instruction(messages: list[dict]) -> list[dict]:
    """Add emphatic JSON-only instruction."""
    emphatic = (
        "CRITICAL: Respond with ONLY valid JSON. No preamble, no markdown, no explanation. "
        "Just the JSON object."
    )
    
    new_messages = messages.copy()
    if new_messages and new_messages[0]["role"] == "user":
        new_messages[0]["content"] = emphatic + "\n\n" + new_messages[0]["content"]
    
    return new_messages
```


### Database Persistence

**File: backend/app/llm/detect_risk.py (continued)**

```python
async def _persist_findings(
    contract_id: str,
    response: RiskDetectionResponse,
    clauses: list[Clause],
    db: AsyncSession
) -> None:
    """
    Persist risk findings to database.
    
    Maps clause_id (string) to actual Clause UUID for risky clauses.
    """
    # Build clause lookup map (clause_number -> UUID)
    clause_map = {c.clause_number: c.id for c in clauses}
    
    # Delete existing findings (idempotent re-runs)
    await db.execute(
        delete(RiskFinding).where(RiskFinding.contract_id == contract_id)
    )
    
    # Insert risky clause findings
    for risky in response.risky_clauses:
        clause_uuid = clause_map.get(risky.clause_id)
        
        if not clause_uuid:
            logger.warning(
                f"Clause ID '{risky.clause_id}' not found in contract {contract_id}, skipping"
            )
            continue
        
        finding = RiskFinding(
            contract_id=contract_id,
            finding_type="risky_clause",
            clause_id=clause_uuid,
            reason=risky.reason,
            triggering_rule_or_corpus=risky.triggering_rule_or_corpus,
            severity=risky.severity.value
        )
        db.add(finding)
    
    # Insert missing clause findings
    for missing in response.missing_clauses:
        finding = RiskFinding(
            contract_id=contract_id,
            finding_type="missing_clause",
            expected_clause_type=missing.expected_clause_type,
            reason=missing.why_expected,
            triggering_rule_or_corpus=missing.triggering_rule_or_corpus,
            severity=missing.severity.value
        )
        db.add(finding)
    
    await db.commit()
    
    logger.info(
        f"Persisted {len(response.risky_clauses)} risky and "
        f"{len(response.missing_clauses)} missing clause findings"
    )

def _build_result(
    contract_id: str,
    response: RiskDetectionResponse
) -> RiskDetectionResult:
    """Build result summary with statistics."""
    # Count severities
    high = sum(
        1 for f in response.risky_clauses if f.severity == Severity.HIGH
    ) + sum(
        1 for f in response.missing_clauses if f.severity == Severity.HIGH
    )
    
    medium = sum(
        1 for f in response.risky_clauses if f.severity == Severity.MEDIUM
    ) + sum(
        1 for f in response.missing_clauses if f.severity == Severity.MEDIUM
    )
    
    low = sum(
        1 for f in response.risky_clauses if f.severity == Severity.LOW
    ) + sum(
        1 for f in response.missing_clauses if f.severity == Severity.LOW
    )
    
    return RiskDetectionResult(
        contract_id=contract_id,
        risky_clauses=response.risky_clauses,
        missing_clauses=response.missing_clauses,
        total_risks=len(response.risky_clauses),
        total_missing=len(response.missing_clauses),
        high_severity_count=high,
        medium_severity_count=medium,
        low_severity_count=low,
        processed_at=datetime.utcnow().isoformat()
    )

def _empty_result(contract_id: str) -> RiskDetectionResult:
    """Return empty result (no clauses to analyze)."""
    return RiskDetectionResult(
        contract_id=contract_id,
        risky_clauses=[],
        missing_clauses=[],
        total_risks=0,
        total_missing=0,
        high_severity_count=0,
        medium_severity_count=0,
        low_severity_count=0,
        processed_at=datetime.utcnow().isoformat()
    )
```


## Test Plan

### Test Strategy

**Mock LLM Client:**
- Create test responses with/without traceability fields
- Simulate malformed JSON
- Test validation and retry logic

### Test Cases

**Test File:** `backend/tests/test_detect_risk.py`

**TC-1: Full Detection - Valid Response**
- Mock contract with 5 classified clauses
- Mock LLM returns valid response with 2 risky + 1 missing
- All findings have traceability fields populated
- Verify: 3 findings persisted to database
- Verify: Severity counts correct

**TC-2: Traceability Validation - Missing Field (Risky Clause)**
- Mock LLM returns risky clause WITHOUT triggering_rule_or_corpus
- Verify: Pydantic ValidationError raised
- Verify: Retry triggered with emphasis message
- Mock retry returns valid response
- Verify: Valid response accepted

**TC-3: Traceability Validation - Missing Field (Missing Clause)**
- Mock LLM returns missing clause WITHOUT triggering_rule_or_corpus
- Verify: Pydantic ValidationError raised
- Verify: Retry triggered

**TC-4: Traceability Validation - Empty String**
- Mock LLM returns triggering_rule_or_corpus = ""
- Verify: Validation fails (empty not allowed)
- Verify: Retry triggered

**TC-5: Traceability Validation - All Retries Fail**
- Mock LLM returns untraceable finding on all attempts
- Verify: RuntimeError raised
- Verify: Error message mentions traceability violation
- Verify: No findings persisted to database

**TC-6: Malformed JSON - First Attempt**
- Mock LLM returns JSON with markdown: ```json {...} ```
- Verify: Markdown stripped successfully
- Verify: Response parsed and validated

**TC-7: Malformed JSON - Retry**
- Mock LLM returns invalid JSON on first attempt
- Mock retry returns valid JSON
- Verify: Emphatic JSON instruction added to retry
- Verify: Valid response accepted

**TC-8: Empty Results - No Risks Found**
- Mock LLM returns empty risky_clauses and empty missing_clauses
- Verify: Response accepted (explicitly no risks)
- Verify: Result shows 0 risks, 0 missing
- Verify: Database has no findings for this contract

**TC-9: Severity Scoring**
- Mock response with mix of low/medium/high severities
- Verify: Severity counts calculated correctly
- Verify: Database stores severity values correctly

**TC-10: Invalid Clause ID Reference**
- Mock response references clause_id that doesn't exist
- Verify: Warning logged
- Verify: Finding skipped (not persisted)
- Verify: Other valid findings still persisted

**TC-11: Database Persistence - Risky Clauses**
- Mock 2 risky clause findings
- Verify: 2 rows in risk_findings table
- Verify: finding_type = 'risky_clause'
- Verify: clause_id populated correctly
- Verify: All fields match LLM response

**TC-12: Database Persistence - Missing Clauses**
- Mock 2 missing clause findings
- Verify: 2 rows in risk_findings table
- Verify: finding_type = 'missing_clause'
- Verify: expected_clause_type populated
- Verify: clause_id is NULL

**TC-13: Database Persistence - Idempotent Re-runs**
- Run detect_risks() twice for same contract
- Verify: Old findings deleted before new inserted
- Verify: Only latest findings in database

**TC-14: Merged Context Retrieval**
- Mock contract with clauses
- Mock legal + corpus search results
- Verify: merge_retrieval_results() called
- Verify: Formatted context passed to prompt

**TC-15: Contract Not Found**
- Call detect_risks() with invalid contract_id
- Verify: ValueError raised
- Verify: Error message mentions "not found"

**TC-16: Contract Not Processed**
- Contract exists but processing_status = "uploaded"
- Verify: ValueError raised
- Verify: Error message mentions "not ready"

**TC-17: No Clauses to Analyze**
- Contract processed but has no classified clauses
- Verify: Empty result returned gracefully
- Verify: No LLM call made

**TC-18: Traceability Field Format**
- Mock response with various citation formats
- Verify: All accepted (no format validation, just non-empty)
- Examples:
  - "Model Tenancy Act 2021, Section 7(1)"
  - "Standard practice"
  - "Reference Example: Fair terms"


## Dependencies

**Python Packages:**
```
# Already included from previous specs:
# sqlalchemy, asyncpg, pydantic, openai/anthropic (llm_client)
```

**No New Dependencies Required** - reuses existing packages.

## Environment Variables

**All Required Variables Already Configured:**
```bash
# From Stage 4
LLM_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# From Stage 6
MAX_CONTEXT_TOKENS=4000
DEDUPLICATION_THRESHOLD=0.95

# Database (from Stage 2)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scantract
```

## Integration with Pipeline

**Updated Complete Pipeline Flow:**

```python
async def process_contract_full_pipeline(
    contract_id: UUID,
    file_path: str,
    db: AsyncSession
) -> dict:
    """
    Complete ScanTract pipeline: Stages 1-7.
    """
    try:
        # Stage 2: Document processing
        extraction_result = await extract_and_segment(file_path)
        
        # Store clauses
        await store_contract_and_clauses(contract_id, extraction_result, db)
        
        # Stage 4: Classify clauses
        classification_result = await classify_all_clauses(
            contract_id=str(contract_id),
            contract_type=detect_contract_type(extraction_result),
            db=db
        )
        
        # Stage 7: Risk detection (includes 5A, 5B, 6 internally)
        risk_result = await detect_risks(
            contract_id=str(contract_id),
            db=db
        )
        
        # Update contract status
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(
                processing_status="risk_analysis_complete",
                processing_completed_at=datetime.utcnow()
            )
        )
        await db.commit()
        
        return {
            "contract_id": str(contract_id),
            "status": "complete",
            "classification": classification_result,
            "risks": risk_result
        }
        
    except Exception as e:
        logger.error(f"Pipeline failed for contract {contract_id}: {e}")
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(processing_status="failed", error_message=str(e))
        )
        await db.commit()
        raise
```


## Files to Create/Modify

### New Files

**Module:**
1. `backend/app/llm/detect_risk.py` - Risk detection logic

**Database:**
2. `backend/alembic/versions/005_create_risk_findings.py` - Migration

**Tests:**
3. `backend/tests/test_detect_risk.py` - Unit tests (18 test cases)
4. `backend/tests/mocks/mock_risk_responses.py` - Mock LLM responses

### Modified Files

5. `backend/app/llm/models.py` - Add risk detection models
6. `backend/app/db/models.py` - Add RiskFinding model, update Contract relationship
7. `backend/app/rag/prompt_builder.py` - Add build_risk_prompt() (from Stage 3 spec)
8. `backend/rag/prompts/risk_detection.txt` - Risk prompt template (from Stage 3 spec)
9. `backend/README.md` - Document risk detection in pipeline

## Performance Benchmarks

**Target Performance:**
- Risk detection (50 clauses): <60 seconds total
  - Context retrieval: <20 seconds
  - LLM call: <30 seconds
  - Database writes: <5 seconds
- Single contract analysis: 1 LLM call (not per-clause)
- Retry overhead: +10 seconds per retry

**Cost Optimization:**
- Single LLM call per contract (efficient)
- Aggregate context retrieval (avoid redundant searches)
- Temperature=0.0 for deterministic results

## Design Tradeoffs

### Single LLM Call vs Per-Clause Calls

**Chosen: Single LLM call for entire contract**

**Pros:**
- More context for better analysis
- Can identify missing clauses (requires full contract view)
- Cost-efficient (1 call vs 50+ calls)
- Faster (parallel vs sequential)

**Cons:**
- Larger context window required
- All-or-nothing (if LLM fails, lose everything)
- Harder to debug individual clause issues

**Mitigation:** Context trimming (Stage 6) ensures we fit in window

### Traceability Validation Strategy

**Chosen: Strict validation with retry**

**Why:**
- Product requirement: no untraceable findings
- User trust depends on verifiable sources
- Better to retry than show unverified risks

**Alternative Considered:** Accept findings, mark as "unverified"
- Violates product rules
- Confuses users
- Defeats purpose of KB-backed analysis

### Severity Levels

**Chosen: Three levels (low/medium/high)**

**Rationale:**
- Simple for users to understand
- Maps to priority (high = urgent, low = informational)
- Avoids over-granularity (5 levels would be confusing)

**Criteria:**
- High: Legal violations, fundamental rights issues, large financial impact
- Medium: Deviations from standard practice, moderate impact
- Low: Minor procedural issues, informational notes


## Out of Scope

**Explicitly NOT included in this spec:**
- Stage 8 (Plain-language explanation generation) - separate spec
- Stage 9 (Citation generation and formatting) - separate spec
- User feedback on findings (accept/reject/adjust)
- Risk scoring algorithms (numerical risk scores)
- Comparative risk analysis (contract A vs B)
- Historical risk trends
- Risk remediation suggestions
- Auto-correction of risky clauses
- Batch contract analysis
- Real-time risk detection during drafting

## Success Criteria

- [ ] `detect_risks()` analyzes full contract with merged context
- [ ] Risk prompt built using Stage 3's `build_risk_prompt()`
- [ ] LLM returns strict JSON with risky_clauses and missing_clauses arrays
- [ ] Every finding has non-empty `triggering_rule_or_corpus` field
- [ ] Pydantic validation enforces traceability requirement
- [ ] Retry triggered if traceability missing (max 2 retries)
- [ ] RuntimeError raised if all retries fail
- [ ] Severity levels: low, medium, high
- [ ] Findings persisted to `risk_findings` table
- [ ] Both risky clauses and missing clauses stored
- [ ] Invalid clause_id references logged but don't fail entire process
- [ ] Idempotent re-runs (old findings deleted before new inserted)
- [ ] Empty results handled gracefully (no risks found)
- [ ] All 18 test cases pass with mocked LLM
- [ ] Traceability validation catches 100% of omissions
- [ ] Single LLM call per contract (efficient)

## Notes

- This spec covers Stage 7 (Risk Detection) of the ScanTract pipeline
- Stage 6 (Merge Context) provides input
- Stage 8 (Explanation Generation) will use findings for output
- Traceability requirement is CRITICAL - no exceptions
- Use Conventional Commits: `feat:` for risk detection, `test:` for tests

## References

- Pydantic validation: https://docs.pydantic.dev/latest/concepts/validators/
- SQLAlchemy check constraints: https://docs.sqlalchemy.org/en/20/core/constraints.html
- LangChain prompts: https://python.langchain.com/docs/modules/model_io/prompts/


## Appendix: Example Risk Detection

**Input Contract:**
```
Rental Agreement

1. Security Deposit
The tenant shall pay a security deposit of 5 months' rent.

2. Termination Notice
Either party may terminate with 7 days written notice.

3. Rent Payment
Rent is due on the 1st of each month.

[Note: Missing maintenance clause]
```

**Merged Context (Stage 6 output):**
```
## Retrieved Context

[Legal Rule: Model Tenancy Act 2021, Section 7(1)]
The security deposit shall not exceed two months' rent for residential properties.

[Legal Rule: Model Tenancy Act 2021, Section 21(1)]
The landlord shall give written notice of at least three months before terminating the tenancy.

[Reference Example: Standard practice - fair deposit terms]
The security deposit shall be equivalent to two months' rent. The landlord shall return the deposit within 30 days...

[Reference Example: Balanced termination - adequate notice]
Either party may terminate this agreement by providing written notice of at least three months...
```

**LLM Response (JSON):**
```json
{
  "risky_clauses": [
    {
      "clause_id": "1",
      "reason": "The security deposit of 5 months' rent significantly exceeds the legal maximum of 2 months' rent for residential properties. This clause is unenforceable and exposes the landlord to legal liability.",
      "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 7(1)",
      "severity": "high"
    },
    {
      "clause_id": "2",
      "reason": "The 7-day termination notice period is substantially shorter than the legally required 3 months. This provides insufficient time for the tenant to find alternative housing and may be challenged as unfair.",
      "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 21(1)",
      "severity": "high"
    }
  ],
  "missing_clauses": [
    {
      "expected_clause_type": "maintenance_obligations",
      "why_expected": "The contract does not specify which party is responsible for structural repairs and routine maintenance. Indian rental law requires clarity on maintenance obligations to avoid disputes. The landlord is typically responsible for structural repairs per legal standards.",
      "triggering_rule_or_corpus": "Model Tenancy Act 2021, Section 13(1)",
      "severity": "medium"
    },
    {
      "expected_clause_type": "security_deposit_refund",
      "why_expected": "While the contract specifies the deposit amount, it does not mention the refund timeline or deduction terms. Standard practice and legal requirements mandate clear refund terms within 30 days of tenancy termination.",
      "triggering_rule_or_corpus": "Standard practice - fair deposit terms",
      "severity": "low"
    }
  ]
}
```

**Persisted to Database:**

```sql
-- risk_findings table
id | contract_id | finding_type | clause_id | expected_clause_type | reason | triggering_rule_or_corpus | severity
---|-------------|--------------|-----------|---------------------|---------|--------------------------|----------
1  | contract-1  | risky_clause | clause-1  | NULL                | The security deposit of 5 months... | Model Tenancy Act 2021, Section 7(1) | high
2  | contract-1  | risky_clause | clause-2  | NULL                | The 7-day termination notice... | Model Tenancy Act 2021, Section 21(1) | high
3  | contract-1  | missing_clause | NULL    | maintenance_obligations | The contract does not specify... | Model Tenancy Act 2021, Section 13(1) | medium
4  | contract-1  | missing_clause | NULL    | security_deposit_refund | While the contract specifies... | Standard practice - fair deposit terms | low
```

**Result Summary:**
```
Risk Detection: 2 risky clauses, 2 missing clauses (High: 2, Med: 1, Low: 1)
```

**Traceability Audit:**
- ✅ Risky clause 1: Traceable to "Model Tenancy Act 2021, Section 7(1)"
- ✅ Risky clause 2: Traceable to "Model Tenancy Act 2021, Section 21(1)"
- ✅ Missing clause 1: Traceable to "Model Tenancy Act 2021, Section 13(1)"
- ✅ Missing clause 2: Traceable to "Standard practice - fair deposit terms"

All findings meet traceability requirement ✅
