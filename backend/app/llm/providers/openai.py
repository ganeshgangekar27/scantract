"""
OpenAI LLM provider using AsyncOpenAI SDK.
"""

import os
import logging
from openai import AsyncOpenAI, RateLimitError, APIError

logger = logging.getLogger(__name__)


async def call_openai(messages: list[dict[str, str]]) -> tuple[str, int]:
    """
    Call OpenAI LLM via OpenAI API.
    
    Args:
        messages: LangChain-compatible message array with role and content
    
    Returns:
        Tuple of (response_text, tokens_used)
    
    Raises:
        ValueError: If OPENAI_API_KEY not set
        RuntimeError: If API call fails
    """
    # Read API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required but not set"
        )
    
    # Read model from environment or use default
    model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    try:
        # Create AsyncOpenAI client
        client = AsyncOpenAI(api_key=api_key)
        
        # Call API with JSON response format enforcement
        response = await client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=2048
        )
        
        # Extract response text
        response_text = response.choices[0].message.content
        
        # Get total tokens
        tokens_used = response.usage.total_tokens
        
        logger.info(f"OpenAI API call successful: {tokens_used} tokens used")
        
        return (response_text, tokens_used)
        
    except RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {e}")
        raise RuntimeError(f"OpenAI API rate limit exceeded: {e}") from e
        
    except APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise RuntimeError(f"OpenAI API error: {e}") from e
