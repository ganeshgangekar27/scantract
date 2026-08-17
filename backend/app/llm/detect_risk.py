"""
Risk detection orchestration for Stage 7.

Identifies risky clauses and missing clauses by combining classified clauses
with merged context from legal KB and reference corpus, enforcing strict
traceability requirements for all findings.
"""

import json
import re
from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import logging

from .llm_client import call_llm
from .models import (
    RiskDetectionResponse,
    RiskDetectionResult,
    Severity,
    RiskyClauseFinding,
    MissingClauseFinding
)
from app.rag.merge_context import merge_retrieval_results, format_merged_context
from app.rag.prompt_builder import build_risk_prompt
from app.db.models import Contract, Clause
from db.legal_kb.search import search_legal_rules
from db.reference_corpus.search import search_reference_corpus

logger = logging.getLogger(__name__)


async def detect_risks(
    contract_id: str,
    db: AsyncSession
) -> RiskDetectionResult:
    """
    Main orchestration function for risk detection.
    
    Steps:
    1. Load contract and validate status
    2. Load classified clauses
    3. Retrieve and merge context from legal KB + reference corpus
    4. Build risk detection prompt
    5. Call LLM with traceability validation
    6. Persist findings to database
    7. Build and return result
    
    Args:
        contract_id: UUID of contract to analyze
        db: SQLAlchemy async session
    
    Returns:
        RiskDetectionResult with all findings and statistics
    
    Raises:
        ValueError: If contract not found or not ready for analysis
        RuntimeError: If all retries fail due to traceability violations
    """
    logger.info(f"Starting risk detection for contract {contract_id}")
    
    # Step 1: Load and validate contract
    contract = await _load_contract(contract_id, db)
    
    # Step 2: Load classified clauses
    clauses = await _load_clauses(contract_id, db)
    
    # Step 3: Handle empty case
    if not clauses:
        logger.warning(f"No clauses to analyze for contract {contract_id}")
        return _empty_result(contract_id)
    
    # Step 4: Retrieve merged context
    retrieved_context = await _retrieve_merged_context_for_contract(
        clauses=clauses,
        contract_type=contract.contract_type,
        state=getattr(contract, 'state', None),
        db=db
    )
    
    # Step 5: Build prompt
    clauses_list = [
        {
            "clause_id": clause.clause_id,
            "clause_type": clause.clause_type or "unknown",
            "clause_text": clause.text
        }
        for clause in clauses
    ]
    
    messages = build_risk_prompt(
        clauses_list=clauses_list,
        retrieved_context=retrieved_context,
        contract_type=contract.contract_type
    )
    
    # Step 6: Call LLM with traceability validation
    response = await _call_llm_with_traceability_validation(messages, max_retries=2)
    
    # Step 7: Persist findings
    await _persist_findings(contract_id, response, clauses, db)
    
    # Step 8: Build result
    result = _build_result(contract_id, response)
    
    logger.info(f"Risk detection completed for contract {contract_id}: {result.total_risks} risky, {result.total_missing} missing")
    
    return result


async def _load_contract(contract_id: str, db: AsyncSession) -> Contract:
    """
    Load contract from database and validate status.
    
    Args:
        contract_id: UUID of contract
        db: SQLAlchemy async session
    
    Returns:
        Contract object
    
    Raises:
        ValueError: If contract not found or not ready
    """
    result = await db.execute(
        select(Contract).where(Contract.id == int(contract_id))
    )
    contract = result.scalar_one_or_none()
    
    if contract is None:
        raise ValueError(f"Contract not found: {contract_id}")
    
    # Check processing status if field exists
    if hasattr(contract, 'processing_status'):
        if contract.processing_status != "completed":
            raise ValueError(
                f"Contract {contract_id} is not ready for risk detection. "
                f"Status: {contract.processing_status}"
            )
    
    return contract


async def _load_clauses(contract_id: str, db: AsyncSession) -> List[Clause]:
    """
    Load classified clauses from database.
    
    Only returns clauses that have been classified (clause_type is not NULL).
    
    Args:
        contract_id: UUID of contract
        db: SQLAlchemy async session
    
    Returns:
        List of Clause objects, ordered by position
    """
    result = await db.execute(
        select(Clause)
        .where(Clause.contract_id == int(contract_id))
        .where(Clause.clause_type.is_not(None))
        .order_by(Clause.position)
    )
    clauses = result.scalars().all()
    
    logger.info(f"Loaded {len(clauses)} classified clauses for contract {contract_id}")
    
    return list(clauses)


async def _retrieve_merged_context_for_contract(
    clauses: List[Clause],
    contract_type: str,
    state: str | None,
    db: AsyncSession
) -> str:
    """
    Retrieve and merge context from legal KB and reference corpus.
    
    Limits to first 10 clauses to avoid excessive API calls during embedding.
    For each clause:
    - Searches legal KB (Stage 5A)
    - Searches reference corpus (Stage 5B)
    - Aggregates all results
    - Merges and deduplicates (Stage 6)
    - Formats for prompt injection
    
    Args:
        clauses: List of Clause objects
        contract_type: "rental" or "freelance"
        state: State code (e.g., "MH") or None
        db: SQLAlchemy async session
    
    Returns:
        Formatted context string ready for prompt injection
    """
    # Limit to first 10 clauses
    limited_clauses = clauses[:10]
    logger.info(f"Retrieving context for {len(limited_clauses)} clauses (capped at 10)")
    
    all_legal_results = []
    all_corpus_results = []
    
    for clause in limited_clauses:
        # Search legal KB
        try:
            legal_results = await search_legal_rules(
                clause_text=clause.text,
                db=db,
                state=state,
                top_k=3
            )
            all_legal_results.extend(legal_results)
        except Exception as e:
            logger.error(f"Error searching legal rules for clause {clause.clause_id}: {e}")
        
        # Search reference corpus
        try:
            corpus_results = await search_reference_corpus(
                clause_text=clause.text,
                contract_type=contract_type,
                db=db,
                top_k=3
            )
            all_corpus_results.extend(corpus_results)
        except Exception as e:
            logger.error(f"Error searching reference corpus for clause {clause.clause_id}: {e}")
    
    # Merge and format
    merge_result = merge_retrieval_results(all_legal_results, all_corpus_results)
    formatted_context = format_merged_context(merge_result)
    
    logger.info(
        f"Retrieved context: {len(all_legal_results)} legal + {len(all_corpus_results)} corpus "
        f"= {len(merge_result.chunks)} merged chunks, {merge_result.total_tokens} tokens"
    )
    
    return formatted_context


async def _call_llm_with_traceability_validation(
    messages: list[dict],
    max_retries: int = 2
) -> RiskDetectionResponse:
    """
    Call LLM with retry logic for traceability validation failures.
    
    Attempts:
    1. Initial call
    2. On JSON error: add emphatic JSON instruction, retry
    3. On traceability error: add emphatic traceability instruction, retry
    4. On continued failure: raise RuntimeError
    
    Args:
        messages: LangChain-compatible message array
        max_retries: Maximum number of retry attempts
    
    Returns:
        Validated RiskDetectionResponse
    
    Raises:
        RuntimeError: If all retries exhausted with traceability violations
    """
    attempt = 0
    last_error = None
    
    while attempt <= max_retries:
        try:
            logger.info(f"LLM call attempt {attempt + 1}/{max_retries + 1}")
            
            # Call LLM
            response_text, tokens = await call_llm(messages)
            
            # Parse JSON
            parsed = _parse_risk_response(response_text)
            
            # Validate via Pydantic
            validated = RiskDetectionResponse(**parsed)
            
            # Paranoid check beyond Pydantic
            _validate_all_findings_traceable(validated)
            
            logger.info(f"LLM response validated successfully on attempt {attempt + 1}")
            return validated
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing error on attempt {attempt + 1}: {e}")
            last_error = e
            
            if attempt < max_retries:
                messages = _add_emphatic_json_instruction(messages)
                attempt += 1
            else:
                break
                
        except ValueError as e:
            error_msg = str(e)
            
            # Check if it's a traceability violation
            if "triggering_rule_or_corpus" in error_msg:
                logger.error(f"🚨 TRACEABILITY VIOLATION on attempt {attempt + 1}: {e}")
                last_error = e
                
                if attempt < max_retries:
                    messages = _add_traceability_emphasis(messages)
                    attempt += 1
                else:
                    break
            else:
                # Other validation error - re-raise immediately
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
            last_error = e
            
            if attempt >= max_retries:
                raise
            
            attempt += 1
    
    # All retries exhausted
    raise RuntimeError(
        f"Risk detection failed after {max_retries + 1} attempts. "
        f"All findings must include valid 'triggering_rule_or_corpus' citations. "
        f"Last error: {last_error}"
    )


def _validate_all_findings_traceable(response: RiskDetectionResponse) -> None:
    """
    Paranoid validation that all findings have non-empty traceability.
    
    This is redundant with Pydantic validation but provides an extra safety layer.
    
    Args:
        response: RiskDetectionResponse to validate
    
    Raises:
        ValueError: If any finding lacks traceability
    """
    for idx, risky in enumerate(response.risky_clauses):
        if not risky.triggering_rule_or_corpus or not risky.triggering_rule_or_corpus.strip():
            raise ValueError(
                f"Risky clause finding #{idx + 1} (clause_id={risky.clause_id}) "
                f"has empty triggering_rule_or_corpus"
            )
    
    for idx, missing in enumerate(response.missing_clauses):
        if not missing.triggering_rule_or_corpus or not missing.triggering_rule_or_corpus.strip():
            raise ValueError(
                f"Missing clause finding #{idx + 1} (type={missing.expected_clause_type}) "
                f"has empty triggering_rule_or_corpus"
            )
    
    logger.debug("All findings passed traceability validation")


def _add_traceability_emphasis(messages: list[dict]) -> list[dict]:
    """
    Add emphatic traceability instruction to messages.
    
    Appends to the last user message to emphasize the requirement.
    
    Args:
        messages: LangChain message array
    
    Returns:
        Modified message array
    """
    emphasis = (
        "\n\n🚨 CRITICAL REQUIREMENT: Every finding MUST include 'triggering_rule_or_corpus' "
        "with the EXACT citation from the context above. Examples:\n"
        "- 'Model Tenancy Act 2021, Section 7(1)'\n"
        "- 'Standard practice - fair deposit terms'\n\n"
        "Findings without this field will be REJECTED. Copy the citation verbatim from the context."
    )
    
    # Append to last user message
    if messages and messages[-1]["role"] == "user":
        messages[-1]["content"] += emphasis
    else:
        messages.append({"role": "user", "content": emphasis})
    
    logger.info("Added traceability emphasis to prompt")
    
    return messages


def _add_emphatic_json_instruction(messages: list[dict]) -> list[dict]:
    """
    Add emphatic JSON-only instruction to messages.
    
    Prepends to the first user message to emphasize valid JSON requirement.
    
    Args:
        messages: LangChain message array
    
    Returns:
        Modified message array
    """
    emphasis = (
        "CRITICAL: Respond with ONLY valid JSON. "
        "No preamble, no markdown, no explanation. Just the JSON object.\n\n"
    )
    
    # Prepend to first message
    if messages:
        messages[0]["content"] = emphasis + messages[0]["content"]
    
    logger.info("Added JSON instruction emphasis to prompt")
    
    return messages


def _parse_risk_response(content: str) -> dict:
    """
    Parse LLM response to JSON, handling markdown wrapping.
    
    Strips markdown code fences if present before parsing.
    
    Args:
        content: Raw LLM response text
    
    Returns:
        Parsed JSON dict
    
    Raises:
        json.JSONDecodeError: If content is not valid JSON
    """
    # Strip markdown code fences
    content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
    content = content.strip()
    
    # Parse JSON
    return json.loads(content)


async def _persist_findings(
    contract_id: str,
    response: RiskDetectionResponse,
    clauses: List[Clause],
    db: AsyncSession
) -> None:
    """
    Persist findings to database with idempotent re-runs.
    
    Deletes existing findings for this contract before inserting new ones.
    This allows re-running risk detection on the same contract.
    
    Args:
        contract_id: UUID of contract
        response: Validated RiskDetectionResponse from LLM
        clauses: List of Clause objects for clause_id mapping
        db: SQLAlchemy async session
    """
    # Import here to avoid circular dependency
    from app.db.models import RiskFinding
    
    # Build clause_id to UUID mapping
    clause_map = {clause.clause_id: clause.id for clause in clauses}
    
    # Delete existing findings (idempotent re-runs)
    await db.execute(
        delete(RiskFinding).where(RiskFinding.contract_id == int(contract_id))
    )
    
    logger.info(f"Deleted existing findings for contract {contract_id}")
    
    # Insert risky clause findings
    for risky in response.risky_clauses:
        clause_uuid = clause_map.get(risky.clause_id)
        
        if clause_uuid is None:
            logger.warning(
                f"Clause ID '{risky.clause_id}' not found in contract {contract_id}, skipping"
            )
            continue
        
        finding = RiskFinding(
            contract_id=int(contract_id),
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
            contract_id=int(contract_id),
            finding_type="missing_clause",
            expected_clause_type=missing.expected_clause_type,
            reason=missing.why_expected,
            triggering_rule_or_corpus=missing.triggering_rule_or_corpus,
            severity=missing.severity.value
        )
        db.add(finding)
    
    await db.commit()
    
    logger.info(
        f"Persisted {len(response.risky_clauses)} risky + {len(response.missing_clauses)} missing "
        f"findings for contract {contract_id}"
    )


def _build_result(
    contract_id: str,
    response: RiskDetectionResponse
) -> RiskDetectionResult:
    """
    Build RiskDetectionResult with severity counts.
    
    Args:
        contract_id: UUID of contract
        response: Validated RiskDetectionResponse from LLM
    
    Returns:
        Complete RiskDetectionResult
    """
    # Count severities across both finding types
    high_count = 0
    medium_count = 0
    low_count = 0
    
    for finding in response.risky_clauses:
        if finding.severity == Severity.HIGH:
            high_count += 1
        elif finding.severity == Severity.MEDIUM:
            medium_count += 1
        elif finding.severity == Severity.LOW:
            low_count += 1
    
    for finding in response.missing_clauses:
        if finding.severity == Severity.HIGH:
            high_count += 1
        elif finding.severity == Severity.MEDIUM:
            medium_count += 1
        elif finding.severity == Severity.LOW:
            low_count += 1
    
    return RiskDetectionResult(
        contract_id=contract_id,
        risky_clauses=response.risky_clauses,
        missing_clauses=response.missing_clauses,
        total_risks=len(response.risky_clauses),
        total_missing=len(response.missing_clauses),
        high_severity_count=high_count,
        medium_severity_count=medium_count,
        low_severity_count=low_count,
        processed_at=datetime.utcnow().isoformat()
    )


def _empty_result(contract_id: str) -> RiskDetectionResult:
    """
    Build empty RiskDetectionResult for contracts with no clauses.
    
    Args:
        contract_id: UUID of contract
    
    Returns:
        RiskDetectionResult with all zeros and empty lists
    """
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
