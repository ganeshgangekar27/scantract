"""
Unit tests for clause classification (TC-4 through TC-12).

All tests use MockLLMClient - zero real API calls.
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import asyncio

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from tests.mocks.mock_llm import (
    MockLLMClient,
    MOCK_VALID_RESPONSE,
    MOCK_MALFORMED_JSON,
    MOCK_INVALID_JSON
)


# TC-4: Single Clause Success
@pytest.mark.asyncio
async def test_single_clause_success():
    """TC-4: Verify successful single clause classification."""
    from app.llm.classify_clauses import classify_clause
    
    mock_client = MockLLMClient(responses=[MOCK_VALID_RESPONSE])
    
    with patch('app.llm.classify_clauses.call_llm', new=mock_client.call):
        result = await classify_clause(
            clause_text="Tenant shall pay rent by 5th of month",
            clause_index="1.1",
            contract_type="rental",
            retrieved_context=""
        )
        
        assert result.classification is not None
        assert result.error is None
        assert result.classification.clause_type == "payment_terms"
        assert result.classification.confidence == 0.92
        assert result.tokens_used == 150
        assert mock_client.call_count == 1


# TC-5: Malformed JSON Retry Success
@pytest.mark.asyncio
async def test_malformed_json_retry_success():
    """TC-5: Verify retry succeeds after malformed JSON on first attempt."""
    from app.llm.classify_clauses import classify_clause
    
    # First call returns malformed, second returns valid
    mock_client = MockLLMClient(
        responses=[MOCK_MALFORMED_JSON, MOCK_VALID_RESPONSE]
    )
    
    with patch('app.llm.classify_clauses.call_llm', new=mock_client.call):
        result = await classify_clause(
            clause_text="Test clause",
            clause_index="2.1",
            contract_type="rental",
            retrieved_context=""
        )
        
        # Should succeed after retry
        assert result.classification is not None
        assert result.classification.clause_type == "payment_terms"
        assert mock_client.call_count == 2
        
        # Verify second call has emphatic instruction
        second_call_messages = mock_client.call_history[1]
        assert len(second_call_messages) > len(mock_client.call_history[0])
        assert "ONLY valid JSON" in second_call_messages[-1]["content"]


# TC-6: Parse Failure After Retry
@pytest.mark.asyncio
async def test_parse_failure_after_retry():
    """TC-6: Verify RuntimeError raised when both attempts fail."""
    from app.llm.classify_clauses import classify_clause
    
    # Both calls return invalid JSON
    mock_client = MockLLMClient(
        responses=[MOCK_INVALID_JSON, MOCK_INVALID_JSON]
    )
    
    with patch('app.llm.classify_clauses.call_llm', new=mock_client.call):
        with pytest.raises(RuntimeError) as exc_info:
            await classify_clause(
                clause_text="Test clause",
                clause_index="3.1",
                contract_type="rental",
                retrieved_context=""
            )
        
        assert "3.1" in str(exc_info.value)
        assert "after retry" in str(exc_info.value)
        assert mock_client.call_count == 2


# TC-7: Batch All Successful
@pytest.mark.asyncio
async def test_batch_all_successful():
    """TC-7: Verify all clauses classified successfully in batch."""
    from app.llm.classify_clauses import classify_all_clauses
    from app.db.models import Clause
    
    # Mock database and clauses
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    
    # Create 3 mock clauses
    clauses = [
        MagicMock(spec=Clause, text=f"Clause {i}", clause_id=str(i), position=i)
        for i in range(1, 4)
    ]
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = clauses
    mock_db.execute.return_value = mock_result
    
    # Mock LLM to always succeed
    mock_client = MockLLMClient(responses=[MOCK_VALID_RESPONSE])
    
    with patch('app.llm.classify_clauses.call_llm', new=mock_client.call):
        result = await classify_all_clauses(
            contract_id=1,
            contract_type="rental",
            db=mock_db
        )
        
        assert result["total"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0
        assert result["total_tokens"] == 450  # 150 * 3
        
        # Verify all clauses updated
        for clause in clauses:
            assert clause.clause_type == "payment_terms"
            assert clause.confidence == 0.92
            assert clause.classified_at is not None
            assert clause.classification_error is None
        
        # Verify commit called once
        assert mock_db.commit.called


# TC-8: Batch Partial Failure
@pytest.mark.asyncio
async def test_batch_partial_failure():
    """TC-8: Verify batch continues when some clauses fail."""
    from app.llm.classify_clauses import classify_all_clauses
    from app.db.models import Clause
    
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    
    # Create 3 mock clauses
    clauses = [
        MagicMock(spec=Clause, text=f"Clause {i}", clause_id=str(i), position=i)
        for i in range(1, 4)
    ]
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = clauses
    mock_db.execute.return_value = mock_result
    
    # First call fails, second and third succeed
    mock_client = MockLLMClient(
        responses=[MOCK_VALID_RESPONSE],
        fail_count=1
    )
    
    with patch('app.llm.classify_clauses.call_llm', new=mock_client.call):
        result = await classify_all_clauses(
            contract_id=1,
            contract_type="rental",
            db=mock_db
        )
        
        assert result["total"] == 3
        assert result["successful"] == 2
        assert result["failed"] == 1
        
        # First clause should have error
        assert clauses[0].classification_error is not None
        
        # Second and third should be classified
        assert clauses[1].clause_type == "payment_terms"
        assert clauses[2].clause_type == "payment_terms"


# TC-9: Concurrency Limit Respected
@pytest.mark.asyncio
async def test_concurrency_limit_respected():
    """TC-9: Verify semaphore limits concurrent LLM calls."""
    from app.llm.classify_clauses import classify_all_clauses
    from app.db.models import Clause
    
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    
    # Create 10 mock clauses
    clauses = [
        MagicMock(spec=Clause, text=f"Clause {i}", clause_id=str(i), position=i)
        for i in range(1, 11)
    ]
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = clauses
    mock_db.execute.return_value = mock_result
    
    # Track concurrent calls
    concurrent_calls = 0
    max_concurrent = 0
    lock = asyncio.Lock()
    
    async def tracked_call(messages):
        nonlocal concurrent_calls, max_concurrent
        async with lock:
            concurrent_calls += 1
            if concurrent_calls > max_concurrent:
                max_concurrent = concurrent_calls
        
        # Simulate work
        await asyncio.sleep(0.01)
        
        async with lock:
            concurrent_calls -= 1
        
        return (MOCK_VALID_RESPONSE, 150)
    
    with patch.dict(os.environ, {'LLM_CONCURRENCY_LIMIT': '3'}):
        with patch('app.llm.classify_clauses.call_llm', new=tracked_call):
            await classify_all_clauses(
                contract_id=1,
                contract_type="rental",
                db=mock_db
            )
            
            # Max concurrent should not exceed limit
            assert max_concurrent <= 3
            assert max_concurrent > 0  # Verify tracking worked


# TC-10: Schema Validation - Invalid Confidence
@pytest.mark.asyncio
async def test_schema_validation_invalid_confidence():
    """TC-10: Verify Pydantic rejects invalid confidence values."""
    from app.llm.models import ClauseClassification
    
    # confidence > 1.0 should fail
    with pytest.raises(Exception):  # Pydantic ValidationError
        ClauseClassification(
            clause_type="payment_terms",
            key_entities=["test"],
            confidence=1.5,  # Invalid
            reasoning="test"
        )
    
    # confidence < 0.0 should fail
    with pytest.raises(Exception):  # Pydantic ValidationError
        ClauseClassification(
            clause_type="payment_terms",
            key_entities=["test"],
            confidence=-0.1,  # Invalid
            reasoning="test"
        )


# TC-11: Schema Validation - Key Entities Cap
@pytest.mark.asyncio
async def test_schema_validation_key_entities_cap():
    """TC-11: Verify key_entities capped at 20 items."""
    from app.llm.models import ClauseClassification
    import logging
    
    # Create list with 25 entities
    entities = [f"entity_{i}" for i in range(25)]
    
    # Capture log warnings
    with patch.object(logging.getLogger('app.llm.models'), 'warning') as mock_warn:
        classification = ClauseClassification(
            clause_type="payment_terms",
            key_entities=entities,
            confidence=0.8,
            reasoning="test"
        )
        
        # Should be truncated to 20
        assert len(classification.key_entities) == 20
        assert classification.key_entities == entities[:20]
        
        # Should log warning
        assert mock_warn.called
        assert "truncating to 20" in str(mock_warn.call_args)


# TC-12: Token Tracking
@pytest.mark.asyncio
async def test_token_tracking():
    """TC-12: Verify token counts accumulated correctly."""
    from app.llm.classify_clauses import classify_all_clauses
    from app.db.models import Clause
    
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    
    # Create 3 clauses
    clauses = [
        MagicMock(spec=Clause, text=f"Clause {i}", clause_id=str(i), position=i)
        for i in range(1, 4)
    ]
    
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = clauses
    mock_db.execute.return_value = mock_result
    
    # Mock returns 150 tokens per call (default for MockLLMClient)
    mock_client = MockLLMClient(responses=[MOCK_VALID_RESPONSE])
    
    with patch('app.llm.classify_clauses.call_llm', new=mock_client.call):
        result = await classify_all_clauses(
            contract_id=1,
            contract_type="rental",
            db=mock_db
        )
        
        # Total should be 3 * 150 = 450
        assert result["total_tokens"] == 450


if __name__ == "__main__":
    print("Run with: pytest test_classify_clauses.py -v")
