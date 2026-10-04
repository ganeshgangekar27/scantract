"""
OpenAI LLM provider using AsyncOpenAI SDK.
"""

import os
import asyncio
import logging
from openai import AsyncOpenAI, RateLimitError, APIError

logger = logging.getLogger(__name__)


async def call_openai(messages: list[dict[str, str]], plain_text: bool = False) -> tuple[str, int]:
    """
    Call OpenAI LLM via OpenAI API.
    
    Args:
        messages: LangChain-compatible message array with role and content
        plain_text: If True, do not enforce JSON response format (for plain-text explanations)
    
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
    
    # Read base URL from environment (for OpenRouter, etc.) or use OpenAI default
    base_url = os.getenv("LLM_BASE_URL")  # None = use OpenAI's default
    
    try:
        # Create AsyncOpenAI client with optional base_url
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url  # None uses OpenAI default, otherwise overrides
        )
        
        # Retry logic for empty/malformed responses (free models can be flaky)
        max_retries = 3
        retry_delay = 1.5  # seconds
        last_error = None
        
        for attempt in range(max_retries):
            if attempt > 0:
                logger.warning(f"Retrying API call (attempt {attempt + 1}/{max_retries}) after empty response")
                await asyncio.sleep(retry_delay)
            
            try:
                # Call API with JSON response format enforcement
                # max_tokens=8192: Significantly increased to accommodate reasoning models
                # that may generate lengthy "thinking" preambles before JSON output
                extra_body_params = {
                    "chat_template_kwargs": {
                        "enable_thinking": False
                    }
                }
                logger.info(f"Calling LLM with max_tokens=8192, plain_text={plain_text}, extra_body={extra_body_params}")
                
                # Build API call kwargs
                api_kwargs = {
                    "model": model_name,
                    "messages": messages,
                    "max_tokens": 8192,
                    "extra_body": extra_body_params
                }
                
                # Only add response_format if NOT plain_text mode
                if not plain_text:
                    api_kwargs["response_format"] = {"type": "json_object"}
                
                response = await client.chat.completions.create(**api_kwargs)
                
                # Validate response structure
                if not response:
                    last_error = "OpenRouter/OpenAI returned null response object"
                    continue  # Retry
                
                if not response.choices or len(response.choices) == 0:
                    last_error = "OpenRouter/OpenAI returned empty choices array - no response generated"
                    continue  # Retry
                
                if not response.choices[0].message:
                    last_error = "OpenRouter/OpenAI returned null message object in first choice"
                    continue  # Retry
                
                # Extract response text
                response_text = response.choices[0].message.content
                
                if not response_text:
                    last_error = "OpenRouter/OpenAI returned empty/null response content"
                    continue  # Retry
                
                # Success - get tokens and return
                tokens_used = 0
                completion_tokens = 0
                finish_reason = response.choices[0].finish_reason if response.choices else None
                
                if response.usage:
                    tokens_used = response.usage.total_tokens
                    completion_tokens = response.usage.completion_tokens
                else:
                    logger.warning("Response missing usage metadata, defaulting to 0 tokens")
                
                logger.info(
                    f"OpenAI API call successful: {tokens_used} tokens used (attempt {attempt + 1}), "
                    f"completion_tokens={completion_tokens}, finish_reason={finish_reason}"
                )
                logger.debug(f"Response content: {response_text[:200]}")
                
                return (response_text, tokens_used)
                
            except (RateLimitError, APIError):
                # Don't retry on rate limit or API errors - re-raise immediately
                raise
        
        # All retries exhausted
        raise RuntimeError(
            f"OpenRouter/OpenAI failed after {max_retries} attempts. "
            f"Last error: {last_error}"
        )
        
    except RateLimitError as e:
        logger.error(f"OpenAI rate limit exceeded: {e}")
        raise RuntimeError(f"OpenAI API rate limit exceeded: {e}") from e
        
    except APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise RuntimeError(f"OpenAI API error: {e}") from e
