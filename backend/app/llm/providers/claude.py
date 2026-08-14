"""
Claude LLM provider using Anthropic SDK.
"""

import os
import logging
from anthropic import Anthropic, RateLimitError, APIError

logger = logging.getLogger(__name__)


async def call_claude(messages: list[dict[str, str]]) -> tuple[str, int]:
    """
    Call Claude LLM via Anthropic API.
    
    Args:
        messages: LangChain-compatible message array with role and content
    
    Returns:
        Tuple of (response_text, tokens_used)
    
    Raises:
        ValueError: If CLAUDE_API_KEY not set
        RuntimeError: If API call fails
    """
    # Read API key from environment
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        raise ValueError(
            "CLAUDE_API_KEY environment variable is required but not set"
        )
    
    # Read model from environment or use default
    model_name = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")
    
    try:
        # Create Anthropic client
        client = Anthropic(api_key=api_key)
        
        # Call API
        response = client.messages.create(
            model=model_name,
            max_tokens=2048,
            messages=messages
        )
        
        # Extract response text
        response_text = response.content[0].text
        
        # Calculate total tokens
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        
        logger.info(f"Claude API call successful: {tokens_used} tokens used")
        
        return (response_text, tokens_used)
        
    except RateLimitError as e:
        logger.error(f"Claude rate limit exceeded: {e}")
        raise RuntimeError(f"Claude API rate limit exceeded: {e}") from e
        
    except APIError as e:
        logger.error(f"Claude API error: {e}")
        raise RuntimeError(f"Claude API error: {e}") from e
