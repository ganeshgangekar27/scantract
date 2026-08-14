"""
Unit tests for LLM client dispatcher (TC-1 through TC-3).

Tests verify provider selection, API key validation, and configuration.
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


# TC-1: Provider Selection
@pytest.mark.asyncio
async def test_provider_selection_claude():
    """TC-1a: Verify call_llm routes to Claude when LLM_PROVIDER=claude."""
    from app.llm.llm_client import call_llm
    
    with patch('app.llm.llm_client.call_claude', new_callable=AsyncMock) as mock_claude:
        with patch.dict(os.environ, {'LLM_PROVIDER': 'claude'}):
            mock_claude.return_value = ("test response", 100)
            
            result = await call_llm([{"role": "user", "content": "test"}])
            
            assert mock_claude.called
            assert result == ("test response", 100)


@pytest.mark.asyncio
async def test_provider_selection_openai():
    """TC-1b: Verify call_llm routes to OpenAI when LLM_PROVIDER=openai."""
    from app.llm.llm_client import call_llm
    
    with patch('app.llm.llm_client.call_openai', new_callable=AsyncMock) as mock_openai:
        with patch.dict(os.environ, {'LLM_PROVIDER': 'openai'}):
            mock_openai.return_value = ("test response", 100)
            
            result = await call_llm([{"role": "user", "content": "test"}])
            
            assert mock_openai.called
            assert result == ("test response", 100)


@pytest.mark.asyncio
async def test_provider_selection_gemini():
    """TC-1c: Verify call_llm routes to Gemini when LLM_PROVIDER=gemini."""
    from app.llm.llm_client import call_llm
    
    with patch('app.llm.llm_client.call_gemini', new_callable=AsyncMock) as mock_gemini:
        with patch.dict(os.environ, {'LLM_PROVIDER': 'gemini'}):
            mock_gemini.return_value = ("test response", 100)
            
            result = await call_llm([{"role": "user", "content": "test"}])
            
            assert mock_gemini.called
            assert result == ("test response", 100)


@pytest.mark.asyncio
async def test_provider_selection_invalid():
    """TC-1d: Verify ValueError raised for unsupported provider."""
    from app.llm.llm_client import call_llm
    
    with patch.dict(os.environ, {'LLM_PROVIDER': 'invalid_provider'}):
        with pytest.raises(ValueError) as exc_info:
            await call_llm([{"role": "user", "content": "test"}])
        
        assert "Unsupported LLM provider" in str(exc_info.value)
        assert "invalid_provider" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provider_selection_missing():
    """TC-1e: Verify ValueError raised when LLM_PROVIDER not set."""
    from app.llm.llm_client import call_llm
    
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            await call_llm([{"role": "user", "content": "test"}])
        
        assert "LLM_PROVIDER" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()


# TC-2: Missing API Key
@pytest.mark.asyncio
async def test_missing_claude_api_key():
    """TC-2a: Verify ValueError when CLAUDE_API_KEY not set."""
    from app.llm.providers.claude import call_claude
    
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            await call_claude([{"role": "user", "content": "test"}])
        
        assert "CLAUDE_API_KEY" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_missing_openai_api_key():
    """TC-2b: Verify ValueError when OPENAI_API_KEY not set."""
    from app.llm.providers.openai import call_openai
    
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            await call_openai([{"role": "user", "content": "test"}])
        
        assert "OPENAI_API_KEY" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_missing_gemini_api_key():
    """TC-2c: Verify ValueError when GEMINI_API_KEY not set."""
    from app.llm.providers.gemini import call_gemini
    
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            await call_gemini([{"role": "user", "content": "test"}])
        
        assert "GEMINI_API_KEY" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()


# TC-3: JSON Response Format
@pytest.mark.asyncio
async def test_openai_json_format_enforcement():
    """TC-3: Verify OpenAI uses response_format=json_object."""
    from app.llm.providers.openai import call_openai
    
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"test": "response"}'
    mock_response.usage.total_tokens = 100
    
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        with patch('app.llm.providers.openai.AsyncOpenAI', return_value=mock_client):
            await call_openai([{"role": "user", "content": "test"}])
            
            # Verify response_format was passed
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs['response_format'] == {"type": "json_object"}


if __name__ == "__main__":
    print("Run with: pytest test_llm_client.py -v")
