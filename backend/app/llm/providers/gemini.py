"""
Google Gemini LLM provider using google-generativeai SDK.
"""

import os
import logging
import json
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)


async def call_gemini(messages: list[dict[str, str]]) -> tuple[str, int]:
    """
    Call Google Gemini LLM via Google Generative AI API.
    
    Args:
        messages: LangChain-compatible message array with role and content
    
    Returns:
        Tuple of (response_text, tokens_used)
    
    Raises:
        ValueError: If GEMINI_API_KEY not set
        RuntimeError: If API call fails
    """
    # Read API key from environment
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is required but not set"
        )
    
    # Read model from environment or use default
    model_name = os.getenv("GEMINI_MODEL", "models/gemini-3.7-flash")
    
    try:
        # Configure Gemini API
        genai.configure(api_key=api_key)
        
        # Create model with JSON response format enforcement
        generation_config = {
            "temperature": 0.7,
            "max_output_tokens": 2048,
            "response_mime_type": "application/json"
        }
        
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config
        )
        
        # Convert messages to Gemini format
        # Gemini uses 'user' and 'model' roles instead of 'user' and 'assistant'
        gemini_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "assistant":
                role = "model"  # Gemini uses 'model' instead of 'assistant'
            gemini_messages.append({
                "role": role,
                "parts": [msg["content"]]
            })
        
        # Start chat session
        chat = model.start_chat(history=gemini_messages[:-1] if len(gemini_messages) > 1 else [])
        
        # Send last message and get response
        last_message = gemini_messages[-1]["parts"][0] if gemini_messages else ""
        response = chat.send_message(last_message)
        
        # Extract response text
        response_text = response.text
        
        # Calculate token usage
        # Gemini provides token counts in usage metadata
        tokens_used = 0
        if hasattr(response, 'usage_metadata'):
            tokens_used = (
                response.usage_metadata.prompt_token_count +
                response.usage_metadata.candidates_token_count
            )
        
        logger.info(f"Gemini API call successful: {tokens_used} tokens used")
        
        return (response_text, tokens_used)
        
    except google_exceptions.ResourceExhausted as e:
        logger.error(f"Gemini rate limit exceeded: {e}")
        raise RuntimeError(f"Gemini API rate limit exceeded: {e}") from e
        
    except google_exceptions.GoogleAPIError as e:
        logger.error(f"Gemini API error: {e}")
        raise RuntimeError(f"Gemini API error: {e}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error calling Gemini: {e}")
        raise RuntimeError(f"Gemini API unexpected error: {e}") from e
