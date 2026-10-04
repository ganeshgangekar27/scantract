"""
Test plain_text parameter wiring through the call chain.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock, ANY
import os


@pytest.mark.asyncio
async def test_generate_explanation_passes_plain_text_true():
    """generate_explanation should pass plain_text=True to call_llm."""
    from app.llm.generate_explanations import generate_explanation
    from app.db.models import RiskFinding
    
    # Create mock finding
    finding = MagicMock(spec=RiskFinding)
    finding.id = "test-id"
    finding.finding_type = "risky_clause"
    finding.reason = "test reason"
    finding.severity = "high"
    finding.triggering_rule_or_corpus = "test rule"
    
    # Mock call_llm
    with patch('app.llm.generate_explanations.call_llm') as mock_call_llm:
        mock_call_llm.return_value = ("This is a valid explanation text that is long enough", 100)
        
        # Mock db session
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        
        await generate_explanation(finding, mock_db)
        
        # Verify call_llm was called with plain_text=True
        assert mock_call_llm.called
        call_args = mock_call_llm.call_args
        assert call_args.kwargs.get('plain_text') == True, "Expected plain_text=True kwarg"


@pytest.mark.asyncio
async def test_call_llm_forwards_plain_text_to_openai():
    """call_llm with LLM_PROVIDER=openai should forward plain_text to call_openai."""
    from app.llm.llm_client import call_llm
    
    with patch.dict(os.environ, {'LLM_PROVIDER': 'openai'}):
        with patch('app.llm.llm_client.call_openai') as mock_openai:
            mock_openai.return_value = ("response", 100)
            
            await call_llm([{"role": "user", "content": "test"}], plain_text=True)
            
            # Verify call_openai received plain_text=True
            assert mock_openai.called
            call_args = mock_openai.call_args
            assert call_args.kwargs.get('plain_text') == True


@pytest.mark.asyncio
async def test_call_llm_plain_text_with_claude_no_error():
    """call_llm with LLM_PROVIDER=claude and plain_text=True should not raise TypeError."""
    from app.llm.llm_client import call_llm
    
    with patch.dict(os.environ, {'LLM_PROVIDER': 'claude'}):
        with patch('app.llm.llm_client.call_claude') as mock_claude:
            mock_claude.return_value = ("response", 100)
            
            # Should not raise TypeError
            await call_llm([{"role": "user", "content": "test"}], plain_text=True)
            
            assert mock_claude.called


@pytest.mark.asyncio
async def test_call_llm_plain_text_with_gemini_no_error():
    """call_llm with LLM_PROVIDER=gemini and plain_text=True should not raise TypeError."""
    from app.llm.llm_client import call_llm
    
    with patch.dict(os.environ, {'LLM_PROVIDER': 'gemini'}):
        with patch('app.llm.llm_client.call_gemini') as mock_gemini:
            mock_gemini.return_value = ("response", 100)
            
            # Should not raise TypeError
            await call_llm([{"role": "user", "content": "test"}], plain_text=True)
            
            assert mock_gemini.called


def test_classification_does_not_pass_plain_text():
    """Verify classification code does not pass plain_text parameter."""
    import inspect
    from app.llm import classify_clauses
    
    source = inspect.getsource(classify_clauses)
    
    # Find all call_llm invocations
    import re
    call_llm_calls = re.findall(r'await call_llm\([^)]+\)', source)
    
    # None should contain plain_text=True
    for call in call_llm_calls:
        assert 'plain_text' not in call or 'plain_text=False' in call, \
            f"Classification should not use plain_text=True: {call}"


def test_risk_detection_does_not_pass_plain_text():
    """Verify risk detection code does not pass plain_text parameter."""
    import inspect
    from app.llm import detect_risk
    
    source = inspect.getsource(detect_risk)
    
    # Find all call_llm invocations
    import re
    call_llm_calls = re.findall(r'await call_llm\([^)]+\)', source)
    
    # None should contain plain_text=True
    for call in call_llm_calls:
        assert 'plain_text' not in call or 'plain_text=False' in call, \
            f"Risk detection should not use plain_text=True: {call}"
