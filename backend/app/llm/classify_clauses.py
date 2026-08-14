"""
Clause classification logic using LLM.

Handles single clause classification and batch processing with error handling and retry logic.
"""

import json
import logging
from app.rag.prompt_builder import build_classification_prompt
from app.llm.llm_client import call_llm
from app.llm.models import ClauseClassification, ClassificationResult

logger = logging.getLogger(__name__)


def _parse_classification_response(response_text: str) -> dict:
    """
    Parse LLM response, stripping markdown artifacts.
    
    Args:
        response_text: Raw LLM response
    
    Returns:
        Parsed JSON as dict
    
    Raises:
        ValueError: If JSON is invalid
    """
    # Strip markdown code fences
    cleaned_text = response_text.strip()
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text[7:]
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text[3:]
    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3]
    
    cleaned_text = cleaned_text.strip()
    
    # Parse JSON
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}") from e


def _add_emphatic_json_instruction(messages: list[dict]) -> list[dict]:
    """
    Add emphatic instruction for strict JSON output.
    
    Args:
        messages: Original message list
    
    Returns:
        Modified message list with additional instruction
    """
    return messages + [{
        "role": "user",
        "content": "Respond with ONLY valid JSON. No markdown, no explanation."
    }]


async def classify_clause(
    clause_text: str,
    clause_index: str,
    contract_type: str,
    retrieved_context: str = ""
) -> ClassificationResult:

    """
    Classify a single contract clause using LLM.
    
    CRITICAL: retrieved_context defaults to "" and MUST stay empty until Stages 5A/5B exist.
    No retrieval logic should be added here.
    
    Args:
        clause_text: The clause content to classify
        clause_index: Clause identifier (e.g., "1.1", "para_5")
        contract_type: "rental" or "freelance"
        retrieved_context: RAG context (empty string until Stages 5A/5B built)
    
    Returns:
        ClassificationResult with classification or error
    """
    try:
        # Build prompt using Stage 3 prompt builder
        messages = build_classification_prompt(
            clause_text=clause_text,
            clause_index=clause_index,
            contract_type=contract_type,
            retrieved_context=retrieved_context
        )
        
        # Call LLM
        response_text, tokens_used = await call_llm(messages)
        
        # Parse response
        try:
            parsed_dict = _parse_classification_response(response_text)
            classification = ClauseClassification(**parsed_dict)
            
            return ClassificationResult(
                clause_index=clause_index,
                classification=classification,
                tokens_used=tokens_used
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            # Retry once with emphatic instruction
            logger.warning(
                f"Malformed response for clause {clause_index}, "
                f"retrying with emphatic instruction: {e}"
            )
            
            # Add emphatic instruction and retry
            retry_messages = _add_emphatic_json_instruction(messages)
            retry_response, retry_tokens = await call_llm(retry_messages)
            
            try:
                retry_parsed = _parse_classification_response(retry_response)
                retry_classification = ClauseClassification(**retry_parsed)
                
                return ClassificationResult(
                    clause_index=clause_index,
                    classification=retry_classification,
                    tokens_used=tokens_used + retry_tokens
                )
                
            except (json.JSONDecodeError, ValueError) as retry_error:
                # Both attempts failed
                raise RuntimeError(
                    f"Failed to classify clause {clause_index} after retry: {retry_error}"
                ) from retry_error
    
    except Exception as e:
        # Return error in result for non-parse exceptions
        logger.error(f"Error classifying clause {clause_index}: {e}")
        return ClassificationResult(
            clause_index=clause_index,
            error=str(e)
        )



import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone


async def classify_all_clauses(
    contract_id: int,
    contract_type: str,
    db: AsyncSession
) -> dict:
    """
    Classify all clauses in a contract with concurrency control.
    
    CRITICAL: Passes retrieved_context="" explicitly (no retrieval until Stages 5A/5B).
    
    Args:
        contract_id: ID of contract to classify
        contract_type: "rental" or "freelance"
        db: Database session
    
    Returns:
        Summary dict with total/successful/failed/total_tokens counts
    """
    # Import Clause model here to avoid circular imports
    from app.db.models import Clause
    
    # Read concurrency limit from env
    concurrency_limit = int(os.getenv("LLM_CONCURRENCY_LIMIT", "5"))
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    # Fetch clauses ordered by position
    query = select(Clause).where(
        Clause.contract_id == contract_id
    ).order_by(Clause.position)
    result = await db.execute(query)
    clauses = result.scalars().all()
    
    # Track statistics
    successful_count = 0
    failed_count = 0
    total_tokens = 0
    
    async def classify_and_store(clause: Clause) -> tuple[bool, int]:
        """Inner function to classify and update a single clause."""
        nonlocal successful_count, failed_count, total_tokens
        
        async with semaphore:
            # Classify clause with EMPTY context (no retrieval until 5A/5B)
            result = await classify_clause(
                clause_text=clause.text,
                clause_index=clause.clause_id,
                contract_type=contract_type,
                retrieved_context=""  # CRITICAL: explicit empty string
            )
            
            if result.classification:
                # Success - update clause fields
                clause.clause_type = result.classification.clause_type
                clause.key_entities = result.classification.key_entities
                clause.confidence = result.classification.confidence
                clause.classified_at = datetime.now(timezone.utc)
                clause.classification_error = None
                
                return (True, result.tokens_used)
            else:
                # Error - store error message
                clause.classification_error = result.error
                clause.classified_at = datetime.now(timezone.utc)
                
                logger.error(
                    f"Failed to classify clause {clause.clause_id}: {result.error}"
                )
                
                return (False, result.tokens_used)
    
    # Run all classifications concurrently (limited by semaphore)
    results = await asyncio.gather(
        *[classify_and_store(c) for c in clauses],
        return_exceptions=False
    )
    
    # Calculate statistics
    for success, tokens in results:
        if success:
            successful_count += 1
        else:
            failed_count += 1
        total_tokens += tokens
    
    # Commit all changes once
    await db.commit()
    
    logger.info(
        f"Classified {len(clauses)} clauses for contract {contract_id}: "
        f"{successful_count} successful, {failed_count} failed, "
        f"{total_tokens} total tokens"
    )
    
    return {
        "total": len(clauses),
        "successful": successful_count,
        "failed": failed_count,
        "total_tokens": total_tokens
    }
