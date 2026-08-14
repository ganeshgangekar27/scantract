"""
LLM client dispatcher - routes to appropriate provider based on env var.
"""

import os
from enum import Enum
from app.llm.providers.claude import call_claude
from app.llm.providers.openai import call_openai
from app.llm.providers.gemini import call_gemini


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"


async def call_llm(messages: list[dict[str, str]]) -> tuple[str, int]:
    """
    Call LLM using provider specified in LLM_PROVIDER env var.
    
    Args:
        messages: LangChain-compatible message array
    
    Returns:
        Tuple of (response_text, tokens_used)
    
    Raises:
        ValueError: If LLM_PROVIDER not set or unsupported
    """
    provider = os.getenv("LLM_PROVIDER", "").lower()
    
    if not provider:
        raise ValueError(
            "LLM_PROVIDER environment variable is required but not set. "
            "Supported values: claude, openai, gemini"
        )
    
    if provider == LLMProvider.CLAUDE:
        return await call_claude(messages)
    elif provider == LLMProvider.OPENAI:
        return await call_openai(messages)
    elif provider == LLMProvider.GEMINI:
        return await call_gemini(messages)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: {', '.join([p.value for p in LLMProvider])}"
        )
