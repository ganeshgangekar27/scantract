# Spec: Explanation Generation & Citation Formatting

## Overview
Build the explanation generation layer for ScanTract — Stage 8 of the core pipeline that transforms risk findings into plain-language explanations with properly formatted legal citations. This stage ensures users can understand technical findings without legal expertise, while maintaining strict citation traceability from Stage 7.

## Scope
- Plain-language explanation generation for each risk finding
- Citation string formatting from existing `triggering_rule_or_corpus` references
- Caching of generated explanations in database
- FastAPI endpoint for retrieving explanations
- Unit tests enforcing citation traceability

## Requirements

### Functional Requirements

**FR-1: Explanation Generation**
- Function: `generate_explanation(finding: RiskFinding) -> str`
- Generate 2-4 sentence plain-language explanation for each finding
- Tone: Clear, factual, no legal jargon
- Language restrictions:
  - ❌ No imperative language ("you should", "you must")
  - ❌ No legal advice ("we recommend", "consult a lawyer")
  - ✅ Use descriptive language ("this clause differs from...", "this provision exceeds...")
- Explain WHY the finding matters (legal/practical implications)
- LLM generates explanation based on finding details + context

**FR-2: Citation Formatting**
- Function: `format_citation(triggering_rule_or_corpus: str) -> str`
- Parse and format citation from Stage 7's traced reference
- NO LLM calls for citations (prevent hallucination)
- Deterministic formatting based on string patterns
- Examples:
  - Input: "Model Tenancy Act 2021, Section 7(1)"
  - Output: "[Legal] Model Tenancy Act 2021, §7(1)"
  - Input: "Standard practice - fair deposit terms"
  - Output: "[Reference] Standard practice - fair deposit terms"


**FR-3: Database Caching**
- Add columns to `risk_findings` table:
  - `explanation`: TEXT, nullable (cached plain-language explanation)
  - `formatted_citation`: TEXT, nullable (cached formatted citation)
  - `explanation_generated_at`: TIMESTAMP, nullable
- Generate explanations lazily (on first request)
- Cache in database to avoid redundant LLM calls
- Invalidate cache if finding changes (e.g., manual edits)

**FR-4: FastAPI Endpoint**
- Endpoint: `GET /api/contracts/{contract_id}/explanations`
- Returns all findings with explanations and citations
- Response format:
  ```json
  {
    "success": true,
    "data": {
      "contract_id": "uuid",
      "risky_clauses": [...],
      "missing_clauses": [...],
      "summary": {
        "total_risks": 5,
        "high_severity": 2,
        "medium_severity": 2,
        "low_severity": 1
      }
    },
    "error": null
  }
  ```
- Generate missing explanations on-the-fly if not cached
- Return cached explanations if available

**FR-5: Batch Generation**
- Function: `generate_all_explanations(contract_id) -> int`
- Generate explanations for all findings without explanations
- Process in batch for efficiency
- Return count of newly generated explanations
- Can be called as background task after Stage 7

**FR-6: Citation Validation**
- Every formatted citation must correspond to existing `triggering_rule_or_corpus`
- Validate during formatting (not LLM-generated)
- Log warning if citation cannot be formatted (malformed reference)
- Never expose orphan citations (without DB source)

**FR-7: Language Compliance**
- Prompt explicitly prohibits:
  - Legal advice ("you should hire a lawyer")
  - Imperative commands ("you must change this clause")
  - Technical jargon without explanation
- Instead, use:
  - Descriptive comparisons ("this clause differs from standard practice because...")
  - Factual statements ("this provision exceeds the legal limit of...")
  - Educational tone ("Indian rental law typically requires...")


### Non-Functional Requirements

**NFR-1: Performance**
- Single explanation generation: <3 seconds (LLM call)
- Batch generation (20 findings): <30 seconds
- Cached retrieval: <100ms (database only)
- Citation formatting: <1ms (deterministic, no API)

**NFR-2: Cache Effectiveness**
- 95%+ hit rate on repeated requests (same contract)
- Cache invalidation only on finding updates
- Lazy generation (generate on first access)

**NFR-3: Citation Accuracy**
- 100% of citations traceable to DB records
- 0% hallucinated citations (LLM never generates citations)
- Deterministic formatting (same input = same output)

**NFR-4: Language Quality**
- Readability: 8th-10th grade reading level
- Clarity: No ambiguous or misleading statements
- Compliance: 100% adherence to no-advice rule

**NFR-5: Type Safety**
- All functions use type hints (Python 3.11+)
- Pydantic models for API responses
- Clear input/output contracts

## Technical Design

### Module Structure

**Location:** `backend/app/llm/`

```
backend/app/llm/
├── __init__.py
├── llm_client.py          # Universal LLM wrapper (from Stage 4)
├── classify_clauses.py    # Clause classification (from Stage 4)
├── detect_risk.py         # Risk detection (from Stage 7)
├── generate_explanations.py  # Explanation generation (NEW)
└── models.py              # Pydantic models (EXTENDED)
```

**API Routes:**
```
backend/app/api/routes/
├── __init__.py
├── contracts.py           # Upload endpoint (from Stage 2)
└── explanations.py        # Explanation endpoint (NEW)
```

### Data Models

**File: backend/app/llm/models.py (extended)**

```python
from pydantic import BaseModel, Field
from typing import Literal

class ExplanationResponse(BaseModel):
    """Single finding with explanation and citation."""
    finding_id: str
    finding_type: Literal["risky_clause", "missing_clause"]
    clause_id: str | None = None
    expected_clause_type: str | None = None
    reason: str
    severity: str
    explanation: str = Field(
        description="Plain-language explanation (2-4 sentences)"
    )
    formatted_citation: str = Field(
        description="Formatted legal citation from traced reference"
    )

class RiskyClauseExplanation(ExplanationResponse):
    """Risky clause with explanation."""
    finding_type: Literal["risky_clause"] = "risky_clause"
    clause_id: str
    clause_text: str
    clause_number: str

class MissingClauseExplanation(ExplanationResponse):
    """Missing clause with explanation."""
    finding_type: Literal["missing_clause"] = "missing_clause"
    expected_clause_type: str

class ContractExplanationsResponse(BaseModel):
    """Complete explanation response for a contract."""
    contract_id: str
    risky_clauses: list[RiskyClauseExplanation]
    missing_clauses: list[MissingClauseExplanation]
    summary: dict[str, int] = Field(
        description="Counts: total_risks, high_severity, medium_severity, low_severity"
    )
```


### Core Explanation Generation

**File: backend/app/llm/generate_explanations.py**

```python
"""
Explanation generation and citation formatting for ScanTract Stage 8.

Generates plain-language explanations for risk findings and formats
legal citations from traced references (no LLM hallucination).
"""

import re
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from .llm_client import call_llm
from .models import ExplanationResponse, ContractExplanationsResponse
from ..db.models import RiskFinding, Clause

logger = logging.getLogger(__name__)

async def generate_explanation(
    finding: RiskFinding,
    db: AsyncSession
) -> str:
    """
    Generate plain-language explanation for a risk finding.
    
    Args:
        finding: RiskFinding from database
        db: Database session
    
    Returns:
        Plain-language explanation (2-4 sentences)
    
    Note:
        Citation is NOT generated by LLM - formatted separately
        from existing triggering_rule_or_corpus field.
    """
    # Build prompt for explanation
    prompt = _build_explanation_prompt(finding)
    
    # Call LLM
    response = await call_llm(
        messages=[{"role": "user", "content": prompt}],
        response_format="text",
        max_tokens=200,
        temperature=0.3  # Slight creativity for readability
    )
    
    explanation = response["content"].strip()
    
    # Validate language compliance (no imperatives)
    if _contains_forbidden_language(explanation):
        logger.warning(
            f"Explanation for finding {finding.id} contains forbidden language, regenerating"
        )
        # Add emphasis and retry once
        prompt += (
            "\n\nREMINDER: Use only descriptive language like 'this clause differs from...' "
            "Do NOT use imperative language like 'you should' or 'you must'."
        )
        response = await call_llm(
            messages=[{"role": "user", "content": prompt}],
            response_format="text",
            max_tokens=200,
            temperature=0.3
        )
        explanation = response["content"].strip()
    
    # Cache in database
    await db.execute(
        update(RiskFinding)
        .where(RiskFinding.id == finding.id)
        .values(
            explanation=explanation,
            explanation_generated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    logger.info(f"Generated explanation for finding {finding.id}")
    
    return explanation

def _build_explanation_prompt(finding: RiskFinding) -> str:
    """
    Build prompt for explanation generation.
    
    Emphasizes plain language, no legal advice, descriptive tone.
    """
    finding_type = "risky clause" if finding.finding_type == "risky_clause" else "missing clause"
    
    prompt = f"""Generate a plain-language explanation for this {finding_type} finding.

Finding Details:
- Type: {finding_type}
- Reason: {finding.reason}
- Severity: {finding.severity}
- Legal/Reference Basis: {finding.triggering_rule_or_corpus}

Requirements:
1. Write 2-4 sentences in plain English (8th-10th grade reading level)
2. Explain WHY this matters (legal and practical implications)
3. Use ONLY descriptive language:
   ✓ "This clause differs from standard practice because..."
   ✓ "This provision exceeds the legal limit of..."
   ✓ "Indian rental law typically requires..."
4. DO NOT use:
   ✗ Imperative language: "you should", "you must", "we recommend"
   ✗ Legal advice: "consult a lawyer", "hire an attorney"
   ✗ Technical jargon without explanation
5. Be factual and educational, not prescriptive

Generate the explanation:"""
    
    return prompt
```


### Citation Formatting (No LLM)

**File: backend/app/llm/generate_explanations.py (continued)**

```python
def format_citation(triggering_rule_or_corpus: str) -> str:
    """
    Format legal citation from traced reference.
    
    CRITICAL: This is deterministic formatting, NOT LLM generation.
    This prevents citation hallucination - we only format what
    Stage 7 already traced to the knowledge base.
    
    Args:
        triggering_rule_or_corpus: Raw reference from Stage 7
    
    Returns:
        Formatted citation string
    
    Examples:
        "Model Tenancy Act 2021, Section 7(1)" 
        → "[Legal] Model Tenancy Act 2021, §7(1)"
        
        "Maharashtra Rent Control Act 1999, Section 11(2) (Maharashtra)"
        → "[Legal] Maharashtra Rent Control Act 1999, §11(2) (Maharashtra)"
        
        "Standard practice - fair deposit terms"
        → "[Reference] Standard practice - fair deposit terms"
    """
    # Detect citation type
    if _is_legal_rule(triggering_rule_or_corpus):
        return _format_legal_citation(triggering_rule_or_corpus)
    else:
        return _format_corpus_citation(triggering_rule_or_corpus)

def _is_legal_rule(reference: str) -> bool:
    """Detect if reference is a legal rule (vs corpus example)."""
    # Legal rules contain "Act" and "Section"
    return "Act" in reference and "Section" in reference

def _format_legal_citation(reference: str) -> str:
    """
    Format legal rule citation.
    
    Pattern: "Act Name YEAR, Section X(Y)" → "[Legal] Act Name YEAR, §X(Y)"
    """
    # Replace "Section" with section symbol (§)
    formatted = reference.replace("Section ", "§")
    
    # Add [Legal] prefix
    return f"[Legal] {formatted}"

def _format_corpus_citation(reference: str) -> str:
    """
    Format reference corpus citation.
    
    Pattern: "Label - description" → "[Reference] Label - description"
    """
    return f"[Reference] {reference}"

def _contains_forbidden_language(text: str) -> bool:
    """
    Check if explanation contains forbidden imperative/advice language.
    
    Returns True if forbidden patterns detected.
    """
    forbidden_patterns = [
        r'\byou should\b',
        r'\byou must\b',
        r'\byou need to\b',
        r'\bwe recommend\b',
        r'\bconsult a lawyer\b',
        r'\bhire an attorney\b',
        r'\bseek legal advice\b'
    ]
    
    text_lower = text.lower()
    
    for pattern in forbidden_patterns:
        if re.search(pattern, text_lower):
            logger.warning(f"Forbidden pattern detected: {pattern}")
            return True
    
    return False
```


### Batch Generation

**File: backend/app/llm/generate_explanations.py (continued)**

```python
async def generate_all_explanations(
    contract_id: str,
    db: AsyncSession
) -> int:
    """
    Generate explanations for all findings without cached explanations.
    
    Args:
        contract_id: Contract UUID
        db: Database session
    
    Returns:
        Count of newly generated explanations
    """
    # Fetch findings without explanations
    result = await db.execute(
        select(RiskFinding)
        .where(RiskFinding.contract_id == contract_id)
        .where(RiskFinding.explanation.is_(None))
    )
    findings = result.scalars().all()
    
    if not findings:
        logger.info(f"All explanations already cached for contract {contract_id}")
        return 0
    
    logger.info(f"Generating {len(findings)} explanations for contract {contract_id}")
    
    # Generate explanations
    for finding in findings:
        try:
            await generate_explanation(finding, db)
        except Exception as e:
            logger.error(f"Failed to generate explanation for finding {finding.id}: {e}")
            # Continue with other findings
    
    # Count successful generations
    result = await db.execute(
        select(RiskFinding)
        .where(RiskFinding.contract_id == contract_id)
        .where(RiskFinding.explanation.isnot(None))
    )
    total_with_explanations = len(result.scalars().all())
    
    newly_generated = total_with_explanations - (len(findings) - len(findings))
    
    logger.info(f"Generated {newly_generated} new explanations")
    
    return newly_generated

async def get_contract_explanations(
    contract_id: str,
    db: AsyncSession,
    auto_generate: bool = True
) -> ContractExplanationsResponse:
    """
    Get all findings with explanations for a contract.
    
    Args:
        contract_id: Contract UUID
        db: Database session
        auto_generate: If True, generate missing explanations on-the-fly
    
    Returns:
        ContractExplanationsResponse with all findings
    """
    # Generate missing explanations if requested
    if auto_generate:
        await generate_all_explanations(contract_id, db)
    
    # Fetch all findings with explanations
    result = await db.execute(
        select(RiskFinding)
        .where(RiskFinding.contract_id == contract_id)
        .order_by(RiskFinding.severity.desc(), RiskFinding.created_at)
    )
    findings = result.scalars().all()
    
    # Separate by type and build responses
    risky_clauses = []
    missing_clauses = []
    
    for finding in findings:
        # Format citation (deterministic, no LLM)
        citation = format_citation(finding.triggering_rule_or_corpus)
        
        # Cache formatted citation if not already cached
        if not finding.formatted_citation or finding.formatted_citation != citation:
            await db.execute(
                update(RiskFinding)
                .where(RiskFinding.id == finding.id)
                .values(formatted_citation=citation)
            )
        
        if finding.finding_type == "risky_clause":
            # Fetch clause details
            clause = await _fetch_clause(finding.clause_id, db)
            
            risky_clauses.append(RiskyClauseExplanation(
                finding_id=str(finding.id),
                clause_id=str(finding.clause_id),
                clause_text=clause.clause_text if clause else "",
                clause_number=clause.clause_number if clause else "",
                reason=finding.reason,
                severity=finding.severity,
                explanation=finding.explanation or "Explanation pending...",
                formatted_citation=citation
            ))
        else:
            missing_clauses.append(MissingClauseExplanation(
                finding_id=str(finding.id),
                expected_clause_type=finding.expected_clause_type,
                reason=finding.reason,
                severity=finding.severity,
                explanation=finding.explanation or "Explanation pending...",
                formatted_citation=citation
            ))
    
    await db.commit()
    
    # Build summary
    summary = {
        "total_risks": len(risky_clauses),
        "total_missing": len(missing_clauses),
        "high_severity": sum(1 for f in findings if f.severity == "high"),
        "medium_severity": sum(1 for f in findings if f.severity == "medium"),
        "low_severity": sum(1 for f in findings if f.severity == "low")
    }
    
    return ContractExplanationsResponse(
        contract_id=contract_id,
        risky_clauses=risky_clauses,
        missing_clauses=missing_clauses,
        summary=summary
    )

async def _fetch_clause(clause_id: str | None, db: AsyncSession) -> Clause | None:
    """Fetch clause details for risky clause findings."""
    if not clause_id:
        return None
    
    result = await db.execute(
        select(Clause).where(Clause.id == clause_id)
    )
    return result.scalar_one_or_none()
```


### FastAPI Endpoint

**File: backend/app/api/routes/explanations.py**

```python
"""
API endpoints for explanation generation and retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_db
from ...llm.generate_explanations import get_contract_explanations
from ...llm.models import ContractExplanationsResponse

router = APIRouter(prefix="/api/contracts", tags=["explanations"])

@router.get("/{contract_id}/explanations")
async def get_explanations(
    contract_id: str,
    auto_generate: bool = True,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get all risk findings with explanations for a contract.
    
    Args:
        contract_id: Contract UUID
        auto_generate: Generate missing explanations on-the-fly (default: True)
        db: Database session
    
    Returns:
        {
            "success": true,
            "data": {
                "contract_id": "...",
                "risky_clauses": [...],
                "missing_clauses": [...],
                "summary": {...}
            },
            "error": null
        }
    
    Notes:
        - Explanations are cached after first generation
        - Citations are deterministically formatted (never LLM-generated)
        - All citations traceable to Stage 7 findings
    """
    try:
        result = await get_contract_explanations(
            contract_id=contract_id,
            db=db,
            auto_generate=auto_generate
        )
        
        return {
            "success": True,
            "data": result.model_dump(),
            "error": None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to get explanations for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{contract_id}/explanations/regenerate")
async def regenerate_explanations(
    contract_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Regenerate all explanations for a contract.
    
    Clears cached explanations and regenerates from scratch.
    Useful if explanation quality needs improvement.
    
    Args:
        contract_id: Contract UUID
        db: Database session
    
    Returns:
        {
            "success": true,
            "data": {"regenerated_count": 5},
            "error": null
        }
    """
    try:
        # Clear cached explanations
        await db.execute(
            update(RiskFinding)
            .where(RiskFinding.contract_id == contract_id)
            .values(explanation=None, explanation_generated_at=None)
        )
        await db.commit()
        
        # Regenerate all
        from ...llm.generate_explanations import generate_all_explanations
        count = await generate_all_explanations(contract_id, db)
        
        return {
            "success": True,
            "data": {"regenerated_count": count},
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Failed to regenerate explanations for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```


### Database Schema Updates

**Alembic Migration:** `backend/alembic/versions/006_add_explanation_caching.py`

```sql
-- Add explanation caching columns to risk_findings
ALTER TABLE risk_findings ADD COLUMN explanation TEXT;
ALTER TABLE risk_findings ADD COLUMN formatted_citation TEXT;
ALTER TABLE risk_findings ADD COLUMN explanation_generated_at TIMESTAMP WITH TIME ZONE;

-- Index for cache hit queries
CREATE INDEX idx_risk_findings_explanation_null 
ON risk_findings(contract_id) 
WHERE explanation IS NULL;

-- Index for citation validation queries
CREATE INDEX idx_risk_findings_citation 
ON risk_findings(triggering_rule_or_corpus);
```

**Updated SQLAlchemy Model:**

```python
class RiskFinding(Base):
    __tablename__ = "risk_findings"
    
    # ... existing fields ...
    
    # Explanation caching (added)
    explanation = Column(Text, nullable=True)
    formatted_citation = Column(Text, nullable=True)
    explanation_generated_at = Column(DateTime(timezone=True), nullable=True)
```

## Test Plan

### Test Strategy

**Mock LLM Client:**
- Return predefined plain-language explanations
- Test with/without forbidden language
- No LLM calls for citations (deterministic formatting)

### Test Cases

**Test File:** `backend/tests/test_generate_explanations.py`

**TC-1: Single Explanation Generation**
- Mock finding with reason and traced reference
- Call generate_explanation()
- Verify: Explanation is 2-4 sentences
- Verify: No forbidden language ("you should", etc.)
- Verify: Cached in database (explanation column populated)

**TC-2: Citation Formatting - Legal Rule**
- Input: "Model Tenancy Act 2021, Section 7(1)"
- Call format_citation()
- Verify: "[Legal] Model Tenancy Act 2021, §7(1)"
- Verify: No LLM call made (deterministic)

**TC-3: Citation Formatting - Legal Rule with State**
- Input: "Maharashtra Rent Control Act 1999, Section 11(2) (Maharashtra)"
- Verify: "[Legal] Maharashtra Rent Control Act 1999, §11(2) (Maharashtra)"

**TC-4: Citation Formatting - Reference Corpus**
- Input: "Standard practice - fair deposit terms"
- Verify: "[Reference] Standard practice - fair deposit terms"

**TC-5: Citation Formatting - Multiple Formats**
- Test various formats from Stage 7
- Verify all formatted without errors
- Verify no LLM calls for any citation

**TC-6: Forbidden Language Detection - Present**
- Mock LLM returns: "You should change this clause immediately."
- Verify: _contains_forbidden_language() returns True
- Verify: Retry triggered with emphasis

**TC-7: Forbidden Language Detection - Absent**
- Mock LLM returns: "This clause differs from standard practice..."
- Verify: _contains_forbidden_language() returns False
- Verify: Accepted without retry

**TC-8: Batch Generation - All New**
- Contract with 5 findings, none have explanations
- Call generate_all_explanations()
- Verify: 5 explanations generated
- Verify: All cached in database

**TC-9: Batch Generation - Partial Cached**
- Contract with 5 findings, 3 already have explanations
- Call generate_all_explanations()
- Verify: Only 2 new explanations generated
- Verify: Existing 3 unchanged

**TC-10: Batch Generation - All Cached**
- Contract with 5 findings, all have explanations
- Call generate_all_explanations()
- Verify: Returns 0 (no new generations)
- Verify: No LLM calls made

**TC-11: API Endpoint - First Request**
- GET /api/contracts/{id}/explanations (auto_generate=true)
- Findings have no cached explanations
- Verify: Explanations generated on-the-fly
- Verify: Response includes all findings with explanations
- Verify: Summary counts correct

**TC-12: API Endpoint - Cached Request**
- GET /api/contracts/{id}/explanations (auto_generate=true)
- Findings already have cached explanations
- Verify: No LLM calls made
- Verify: Response includes cached explanations
- Verify: Fast response (<100ms)

**TC-13: API Endpoint - No Auto-Generate**
- GET /api/contracts/{id}/explanations (auto_generate=false)
- Some findings missing explanations
- Verify: Returns "Explanation pending..." for missing
- Verify: No LLM calls made

**TC-14: Citation Traceability**
- Fetch all findings for contract
- Verify: Each formatted_citation corresponds to existing triggering_rule_or_corpus
- Verify: No orphan citations (every citation has DB source)

**TC-15: Regenerate Endpoint**
- POST /api/contracts/{id}/explanations/regenerate
- Verify: Existing explanations cleared
- Verify: New explanations generated
- Verify: Count returned correctly

**TC-16: Risky Clause with Clause Details**
- Risky clause finding linked to clause
- Verify: Response includes clause_text and clause_number
- Verify: Clause fetched from database

**TC-17: Missing Clause Details**
- Missing clause finding
- Verify: Response includes expected_clause_type
- Verify: No clause_id (NULL for missing clauses)

**TC-18: Severity Ordering**
- Mix of high/medium/low severity findings
- Verify: Response ordered by severity (high first)
- Verify: Summary counts by severity correct


## Out of Scope

**Explicitly NOT included in this spec:**
- Stage 9 (Final UI response formatting) - separate spec
- User feedback on explanations (thumbs up/down)
- Explanation editing by users
- Multi-language explanations (only English)
- Audio/video explanations
- Explanation quality scoring
- A/B testing of explanation styles
- Custom explanation templates per user
- Explanation history/versioning

## Success Criteria

- [ ] `generate_explanation()` creates 2-4 sentence plain-language explanations
- [ ] No forbidden language ("you should", "you must", legal advice)
- [ ] Explanations readable at 8th-10th grade level
- [ ] `format_citation()` formats citations deterministically (no LLM)
- [ ] Legal rules formatted as: "[Legal] Act Name, §Section"
- [ ] Corpus references formatted as: "[Reference] Label"
- [ ] Explanations cached in `risk_findings.explanation` column
- [ ] Citations cached in `risk_findings.formatted_citation` column
- [ ] GET /api/contracts/{id}/explanations returns all findings with explanations
- [ ] Auto-generate flag controls on-the-fly generation
- [ ] Cached explanations returned without LLM calls
- [ ] POST /api/contracts/{id}/explanations/regenerate clears and regenerates
- [ ] Citation validation: 100% traceable to DB records
- [ ] No orphan citations (every citation has DB source)
- [ ] All 18 test cases pass
- [ ] Cache hit rate >95% on repeated requests
- [ ] Cached retrieval <100ms

## Notes

- This spec covers Stage 8 (Explanation Generation) of the ScanTract pipeline
- Stage 7 (Risk Detection) provides traced references (no re-fetching)
- Stage 9 (Final UI Response) will consume explanations for frontend
- Citation formatting is DETERMINISTIC (no LLM = no hallucination)
- Caching is critical for performance and cost
- Use Conventional Commits: `feat:` for explanation logic, `test:` for tests

## References

- Plain language guidelines: https://www.plainlanguage.gov/
- Readability scoring: https://en.wikipedia.org/wiki/Flesch–Kincaid_readability_tests
- Legal citation formats: https://en.wikipedia.org/wiki/Legal_citation
- FastAPI response models: https://fastapi.tiangolo.com/tutorial/response-model/


## Files to Create/Modify

### New Files

**Module:**
1. `backend/app/llm/generate_explanations.py` - Explanation generation logic

**API:**
2. `backend/app/api/routes/explanations.py` - FastAPI endpoints

**Database:**
3. `backend/alembic/versions/006_add_explanation_caching.py` - Migration

**Tests:**
4. `backend/tests/test_generate_explanations.py` - Unit tests (18 test cases)
5. `backend/tests/test_api_explanations.py` - API endpoint tests

### Modified Files

6. `backend/app/llm/models.py` - Add explanation models
7. `backend/app/db/models.py` - Add caching columns to RiskFinding
8. `backend/app/main.py` - Register explanations router
9. `backend/README.md` - Document explanation endpoint

## Dependencies

**No New Dependencies Required** - reuses existing packages from previous stages.

## Environment Variables

**All Required Variables Already Configured** - no new environment variables needed.

## Performance Benchmarks

**Target Performance:**
- Single explanation generation: <3 seconds (LLM call)
- Batch generation (20 findings): <30 seconds (parallel possible)
- Citation formatting: <1ms (deterministic regex)
- Cached retrieval: <100ms (database only)
- API endpoint (cached): <150ms total

**Cost Analysis:**
- Explanation: ~150 tokens per call (cheap)
- Citation: 0 tokens (deterministic, no API)
- Estimated cost: $0.001 per explanation (GPT-3.5 Turbo)

**Cache Effectiveness:**
- Expected cache hit rate: 95%+ on repeated requests
- Cache miss only on: first request, regeneration, finding updates
- Typical user: views explanations 3-5 times → 80% savings

## Design Tradeoffs

### LLM for Explanations, Not for Citations

**Chosen: LLM generates explanations, citations are deterministic**

**Rationale:**
- Explanations need variability and context (LLM excels)
- Citations are factual references (LLM prone to hallucination)
- Stage 7 already traced citations to DB (just format them)

**Why This Works:**
- Best of both worlds: readable explanations + accurate citations
- Zero risk of citation hallucination
- Deterministic citations enable validation

### Caching Strategy

**Chosen: Database columns, not separate cache**

**Pros:**
- Transactional consistency (explanation + finding updated together)
- Simple invalidation (just clear column)
- No separate cache layer to manage
- Persistent across restarts

**Cons:**
- Database writes on every generation
- Slightly slower than in-memory cache (but <100ms is fine)

**Alternative Considered:** Redis cache
- Faster but adds complexity
- Risk of cache/DB inconsistency
- Not worth it for <100ms requirement

### Language Validation

**Chosen: Regex-based forbidden pattern detection + retry**

**Pros:**
- Fast (<1ms)
- Catches most violations
- Simple to maintain

**Cons:**
- False positives possible (rare)
- Doesn't catch semantic advice (e.g., "changing this clause would be prudent")

**Mitigation:** Prompt engineering (clear instructions) + regex safety net


## Integration with Pipeline

**Complete Pipeline Flow (Stages 1-8):**

```python
async def full_contract_analysis_pipeline(
    contract_id: UUID,
    file_path: str,
    db: AsyncSession
) -> dict:
    """
    Complete ScanTract pipeline: Upload → Analysis → Explanations.
    """
    try:
        # Stage 2: Document processing
        extraction_result = await extract_and_segment(file_path)
        await store_contract_and_clauses(contract_id, extraction_result, db)
        
        # Stage 4: Classify clauses
        await classify_all_clauses(
            contract_id=str(contract_id),
            contract_type=detect_contract_type(extraction_result),
            db=db
        )
        
        # Stage 7: Risk detection (includes 5A, 5B, 6 internally)
        risk_result = await detect_risks(contract_id=str(contract_id), db=db)
        
        # Stage 8: Generate explanations (can be async/background)
        explanation_count = await generate_all_explanations(
            contract_id=str(contract_id),
            db=db
        )
        
        # Update contract status
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(
                processing_status="complete",
                processing_completed_at=datetime.utcnow()
            )
        )
        await db.commit()
        
        return {
            "contract_id": str(contract_id),
            "status": "complete",
            "risks": risk_result,
            "explanations_generated": explanation_count
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

**Frontend Usage:**

```typescript
// 1. Upload contract
const uploadResponse = await uploadContract(file);
const contractId = uploadResponse.data.contract_id;

// 2. Poll for processing status
await pollUntilComplete(contractId);

// 3. Fetch explanations (auto-generated if not cached)
const explanationsResponse = await fetch(
  `/api/contracts/${contractId}/explanations?auto_generate=true`
);

// 4. Display to user
const { risky_clauses, missing_clauses, summary } = explanationsResponse.data;
displayResults(risky_clauses, missing_clauses, summary);
```


## Appendix: Example Explanations

**Example 1: Risky Clause (High Severity)**

**Finding:**
- Clause: "The tenant shall pay a security deposit of 5 months' rent."
- Reason: "Exceeds legal maximum of 2 months' rent"
- Traced Reference: "Model Tenancy Act 2021, Section 7(1)"
- Severity: high

**Generated Explanation:**
> "This security deposit requirement of 5 months' rent significantly exceeds the legal maximum established under Indian rental law. The Model Tenancy Act 2021 caps security deposits at 2 months' rent for residential properties to protect tenants from excessive financial burdens. A deposit of this magnitude may be challenged as unenforceable and could expose the landlord to legal liability."

**Formatted Citation:**
> "[Legal] Model Tenancy Act 2021, §7(1)"

---

**Example 2: Risky Clause (Medium Severity)**

**Finding:**
- Clause: "Rent increases by 15% annually."
- Reason: "Exceeds typical 8% annual increase limit"
- Traced Reference: "Standard practice - fair rent control"
- Severity: medium

**Generated Explanation:**
> "This annual rent increase of 15% is substantially higher than the standard practice of 8% recommended by the Model Tenancy Act. While not necessarily illegal in all jurisdictions, such a steep increase may be viewed as excessive and could lead to disputes. Standard rental agreements typically cap annual increases at 8-10% to ensure predictability for both parties."

**Formatted Citation:**
> "[Reference] Standard practice - fair rent control"

---

**Example 3: Missing Clause (Medium Severity)**

**Finding:**
- Expected Type: "maintenance_obligations"
- Reason: "Contract does not specify structural repair responsibilities"
- Traced Reference: "Model Tenancy Act 2021, Section 13(1)"
- Severity: medium

**Generated Explanation:**
> "This contract lacks clear guidance on who is responsible for structural repairs like roof damage, plumbing issues, or foundation problems. Indian rental law typically assigns these obligations to the landlord while the tenant handles day-to-day maintenance. Without this clarity, disputes may arise over repair costs and responsibilities, potentially leading to delayed maintenance and tenant-landlord conflicts."

**Formatted Citation:**
> "[Legal] Model Tenancy Act 2021, §13(1)"

---

**Example 4: Missing Clause (Low Severity)**

**Finding:**
- Expected Type: "rent_receipt_provision"
- Reason: "No mention of rent receipt requirements"
- Traced Reference: "Standard practice - documentation requirements"
- Severity: low

**Generated Explanation:**
> "This contract does not mention the landlord's obligation to provide rent receipts, which is considered standard practice in rental agreements. While rent receipts are not always legally mandated, they serve as important proof of payment for both tax purposes and dispute resolution. Adding a receipt provision helps maintain clear financial records and protects both parties."

**Formatted Citation:**
> "[Reference] Standard practice - documentation requirements"

---

**Key Observations:**
- All explanations 2-4 sentences ✓
- No imperative language ("you should") ✓
- Descriptive tone ("differs from", "exceeds") ✓
- Plain language (8th-10th grade level) ✓
- Citations formatted from traced references ✓
- No LLM-generated citations ✓

