"""
Google Gemini LLM provider using google-genai SDK (new).
"""

import os
import logging
import json
from google import genai

logger = logging.getLogger(__name__)

# Lazy singleton for Gemini client
_gemini_client: genai.Client | None = None


def get_gemini_client() -> genai.Client:
    """Get or create Gemini API client singleton."""
    global _gemini_client
    
    if _gemini_client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required but not set"
            )
        _gemini_client = genai.Client(api_key=api_key)
        logger.info("Gemini API client created successfully")
    
    return _gemini_client


async def call_gemini(messages: list[dict[str, str]]) -> tuple[str, int]:
    """
    Call Google Gemini LLM via Google Generative AI API (new SDK).
    
    Args:
        messages: LangChain-compatible message array with role and content
    
    Returns:
        Tuple of (response_text, tokens_used)
    
    Raises:
        ValueError: If GEMINI_API_KEY not set
        RuntimeError: If API call fails
    """
    # Get client (raises ValueError if key not set)
    client = get_gemini_client()
    
    # Read model from environment or use default
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
    # Remove 'models/' prefix if present (new SDK doesn't require it)
    if model_name.startswith("models/"):
        model_name = model_name[7:]
    
    try:
        # Convert messages to Gemini format
        # New SDK uses Content objects with role='user' or role='model'
        from google.genai import types
        
        gemini_contents = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"  # Gemini uses 'model' instead of 'assistant'
            
            gemini_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part(text=msg["content"])]
                )
            )
        
        # Generate content using new SDK
        response = client.models.generate_content(
            model=model_name,
            contents=gemini_contents,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )
        
        # Extract response text
        response_text = response.text
        
        # Calculate token usage from usage_metadata
        tokens_used = 0
        if response.usage_metadata:
            tokens_used = (
                response.usage_metadata.prompt_token_count +
                response.usage_metadata.candidates_token_count
            )
        
        logger.info(f"Gemini API call successful: {tokens_used} tokens used")
        
        return (response_text, tokens_used)
        
    except Exception as e:
        # Handle rate limits and API errors generically
        error_msg = str(e)
        
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            logger.error(f"Gemini rate limit exceeded: {e}")
            raise RuntimeError(f"Gemini API rate limit exceeded: {e}") from e
        elif "API" in error_msg or "genai" in error_msg:
            logger.error(f"Gemini API error: {e}")
            raise RuntimeError(f"Gemini API error: {e}") from e
        else:
            logger.error(f"Unexpected error calling Gemini: {e}")
            raise RuntimeError(f"Gemini API unexpected error: {e}") from e
