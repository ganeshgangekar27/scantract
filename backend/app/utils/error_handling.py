"""
Error message handling utilities.

Provides friendly, redacted error messages for end users.
"""
import re


def friendly_error(text_or_exception) -> str:
    """
    Convert exception or error text to friendly, redacted message.
    
    Rules:
    - Rate limit errors (429, "rate limit", "free-models-per-day") → friendly daily limit message
    - Other errors: redact API keys, collapse whitespace, truncate to 300 chars
    
    Args:
        text_or_exception: Error text or Exception object
    
    Returns:
        Friendly error message suitable for end users (max 300 chars)
    
    Examples:
        >>> friendly_error("Error code: 429 - rate limit exceeded")
        "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."
        
        >>> friendly_error("Failed with key sk-or-v1-abc123def456")
        "Failed with key [redacted]"
    """
    # Convert to string
    text = str(text_or_exception)
    
    # Check for rate limit indicators (case-insensitive)
    text_lower = text.lower()
    if any(indicator in text_lower for indicator in ["429", "rate limit", "free-models-per-day"]):
        return "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."
    
    # Redact API keys
    # Pattern: sk-or-v1-{alphanum}+ or AIza{alphanum/dash/underscore}{20+}
    text = re.sub(r'sk-or-v1-[0-9a-zA-Z]+', '[redacted]', text)
    text = re.sub(r'AIza[0-9A-Za-z_-]{20,}', '[redacted]', text)
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Truncate to 300 characters
    if len(text) > 300:
        text = text[:300]
    
    return text
