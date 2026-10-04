"""
Test response_format control per LLM call type.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_explanation_call_uses_plain_text():
    """Explanation generation should NOT use response_format=json_object."""
    from app.llm.providers.openai import call_openai
    
    with patch('app.llm.providers.openai.os.getenv') as mock_getenv:
        # Mock environment variables
        def getenv_side_effect(key, default=None):
            if key == "OPENAI_API_KEY":
                return "test-key"
            elif key == "OPENAI_MODEL":
                return "gpt-3.5-turbo"
            elif key == "LLM_BASE_URL":
                return None
            return default
        
        mock_getenv.side_effect = getenv_side_effect
        
        with patch('app.llm.providers.openai.AsyncOpenAI') as mock_openai_class:
            # Mock the client and response
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "This is plain text explanation"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.total_tokens = 100
            mock_response.usage.completion_tokens = 50
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Call with plain_text=True
            messages = [{"role": "user", "content": "Explain this finding"}]
            await call_openai(messages, plain_text=True)
            
            # Verify response_format was NOT sent
            call_args = mock_client.chat.completions.create.call_args
            assert 'response_format' not in call_args.kwargs


@pytest.mark.asyncio
async def test_classification_call_uses_json():
    """Classification should still use response_format=json_object."""
    from app.llm.providers.openai import call_openai
    
    with patch('app.llm.providers.openai.os.getenv') as mock_getenv:
        # Mock environment variables
        def getenv_side_effect(key, default=None):
            if key == "OPENAI_API_KEY":
                return "test-key"
            elif key == "OPENAI_MODEL":
                return "gpt-3.5-turbo"
            elif key == "LLM_BASE_URL":
                return None
            return default
        
        mock_getenv.side_effect = getenv_side_effect
        
        with patch('app.llm.providers.openai.AsyncOpenAI') as mock_openai_class:
            # Mock the client and response
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"clauses": []}'
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.total_tokens = 100
            mock_response.usage.completion_tokens = 50
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Call with plain_text=False (default)
            messages = [{"role": "user", "content": "Classify these clauses"}]
            await call_openai(messages, plain_text=False)
            
            # Verify response_format WAS sent
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs['response_format'] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_default_is_json():
    """Default behavior (no plain_text arg) should use JSON."""
    from app.llm.providers.openai import call_openai
    
    with patch('app.llm.providers.openai.os.getenv') as mock_getenv:
        # Mock environment variables
        def getenv_side_effect(key, default=None):
            if key == "OPENAI_API_KEY":
                return "test-key"
            elif key == "OPENAI_MODEL":
                return "gpt-3.5-turbo"
            elif key == "LLM_BASE_URL":
                return None
            return default
        
        mock_getenv.side_effect = getenv_side_effect
        
        with patch('app.llm.providers.openai.AsyncOpenAI') as mock_openai_class:
            # Mock the client and response
            mock_client = AsyncMock()
            mock_openai_class.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"result": "ok"}'
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.total_tokens = 100
            mock_response.usage.completion_tokens = 50
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Call without plain_text argument
            messages = [{"role": "user", "content": "Some request"}]
            await call_openai(messages)
            
            # Verify response_format WAS sent (default)
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs['response_format'] == {"type": "json_object"}
