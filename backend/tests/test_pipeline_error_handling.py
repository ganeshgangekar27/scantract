"""
Tests for pipeline error handling with friendly messages.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.document_processing.orchestrator import _run_classification_stage, _run_risk_detection_stage, _run_explanation_stage
from app.db.models import Contract, Clause, RiskFinding


@pytest.mark.asyncio
async def test_classification_rate_limit_error():
    """Classification stage with rate limit error stores friendly message."""
    # Mock database
    db = AsyncMock()
    
    # Mock contract
    contract = MagicMock(spec=Contract)
    contract.id = 1
    contract.pipeline_stage = 'segmented'
    
    # Mock classify_all_clauses to raise rate limit error
    rate_limit_error = RuntimeError(
        "OpenAI API rate limit exceeded: Error code: 429 - {'error': {'message': 'Rate limit exceeded: free-models-per-day'}}"
    )
    
    with patch('app.document_processing.orchestrator.classify_all_clauses', side_effect=rate_limit_error):
        with pytest.raises(RuntimeError):
            await _run_classification_stage(contract, db)
    
    # Verify contract state
    assert contract.pipeline_stage == 'failed'
    assert contract.failed_stage == 'classifying'
    assert contract.error_message == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."
    db.commit.assert_called()


@pytest.mark.asyncio
async def test_risk_detection_rate_limit_error():
    """Risk detection stage with rate limit error stores friendly message."""
    db = AsyncMock()
    
    contract = MagicMock(spec=Contract)
    contract.id = 2
    contract.pipeline_stage = 'classified'
    
    rate_limit_error = RuntimeError(
        "OpenAI API rate limit exceeded: Error code: 429"
    )
    
    with patch('app.document_processing.orchestrator.detect_risks', side_effect=rate_limit_error):
        with pytest.raises(RuntimeError):
            await _run_risk_detection_stage(contract, db)
    
    assert contract.pipeline_stage == 'failed'
    assert contract.failed_stage == 'detecting_risks'
    assert contract.error_message == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."


@pytest.mark.asyncio
async def test_explanation_generation_rate_limit_error():
    """Explanation generation stage with rate limit error stores friendly message."""
    db = AsyncMock()
    
    contract = MagicMock(spec=Contract)
    contract.id = 3
    contract.pipeline_stage = 'risks_detected'
    
    rate_limit_error = RuntimeError(
        "RuntimeError: rate limit exceeded for free-models-per-day"
    )
    
    with patch('app.document_processing.orchestrator.generate_all_explanations', side_effect=rate_limit_error):
        with pytest.raises(RuntimeError):
            await _run_explanation_stage(contract, db)
    
    assert contract.pipeline_stage == 'failed'
    assert contract.failed_stage == 'generating_explanations'
    assert contract.error_message == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."


@pytest.mark.asyncio
async def test_non_rate_limit_error_redacted():
    """Non-rate-limit errors are redacted and truncated."""
    db = AsyncMock()
    
    contract = MagicMock(spec=Contract)
    contract.id = 4
    contract.pipeline_stage = 'segmented'
    
    # Build key at runtime to avoid committing key-shaped literal
    key = "sk-or-v1-" + "testkey123456789"
    error_with_key = RuntimeError(f"Authentication failed with {key}")
    
    with patch('app.document_processing.orchestrator.classify_all_clauses', side_effect=error_with_key):
        with pytest.raises(RuntimeError):
            await _run_classification_stage(contract, db)
    
    assert contract.pipeline_stage == 'failed'
    assert contract.failed_stage == 'classifying'
    assert "[redacted]" in contract.error_message
    assert key not in contract.error_message
    assert "testkey123456789" not in contract.error_message


@pytest.mark.asyncio
async def test_classification_includes_first_error():
    """Classification failure includes first error for diagnosis."""
    db = AsyncMock()
    
    contract = MagicMock(spec=Contract)
    contract.id = 5
    contract.pipeline_stage = 'segmented'
    
    # Mock classify_all_clauses to return 0 successful with first_error
    stats = {
        "total": 5,
        "successful": 0,
        "failed": 5,
        "total_tokens": 0,
        "first_error": "RuntimeError: OpenAI API rate limit exceeded: Error code: 429"
    }
    
    with patch('app.document_processing.orchestrator.classify_all_clauses', return_value=stats):
        with pytest.raises(RuntimeError) as exc_info:
            await _run_classification_stage(contract, db)
    
    # Verify error message includes "Classification failed: " prefix
    error_str = str(exc_info.value)
    assert "Classification failed: 0/5 clauses classified" in error_str
    assert "first error:" in error_str.lower()
    
    # Verify friendly error stored
    assert contract.error_message == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."

