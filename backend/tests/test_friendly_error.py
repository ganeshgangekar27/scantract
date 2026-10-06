"""
Tests for friendly_error helper.
"""
import pytest
from app.utils.error_handling import friendly_error


def test_rate_limit_message_with_429():
    """Rate limit error with 429 code returns friendly message."""
    error = "RuntimeError: OpenAI API rate limit exceeded: Error code: 429 - {'error': {'message': 'Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day'"
    
    result = friendly_error(error)
    
    assert result == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."


def test_rate_limit_message_with_text():
    """Rate limit error with 'rate limit' text returns friendly message."""
    error = "API rate limit exceeded for free tier"
    
    result = friendly_error(error)
    
    assert result == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."


def test_rate_limit_message_with_free_models():
    """Rate limit error with 'free-models-per-day' returns friendly message."""
    error = "Rate limit exceeded: free-models-per-day. Add 10 credits"
    
    result = friendly_error(error)
    
    assert result == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."


def test_redact_openrouter_key():
    """OpenRouter key is redacted."""
    # Build key at runtime to avoid committing key-shaped literal
    key = "sk-or-v1-" + "0123456789abcdef" * 2
    error = f"Authentication failed with key {key}"
    
    result = friendly_error(error)
    
    assert "[redacted]" in result
    assert key not in result
    assert "0123456789abcdef" not in result


def test_redact_google_key():
    """Google API key is redacted."""
    # Build key at runtime
    key = "AIza" + "0123456789_abcdefABCD"
    error = f"Failed with API key {key}"
    
    result = friendly_error(error)
    
    assert "[redacted]" in result
    assert key not in result


def test_truncate_long_text():
    """Long text is truncated to 300 characters."""
    # Create 1000-character text
    error = "X" * 1000
    
    result = friendly_error(error)
    
    assert len(result) == 300
    assert result == "X" * 300


def test_ordinary_text_unchanged():
    """Ordinary error text is returned as-is."""
    error = "Classification failed: invalid response format"
    
    result = friendly_error(error)
    
    assert result == error


def test_collapse_whitespace():
    """Whitespace is collapsed."""
    error = "Error    with    lots    of     spaces\n\nand\nnewlines"
    
    result = friendly_error(error)
    
    assert "  " not in result
    assert "\n" not in result
    assert result == "Error with lots of spaces and newlines"


def test_strip_whitespace():
    """Leading/trailing whitespace is stripped."""
    error = "  \n  Error message  \n  "
    
    result = friendly_error(error)
    
    assert result == "Error message"
