"""
Tests for CORS origins configuration from environment variable.
"""

import pytest
import os


def test_unset_returns_default(monkeypatch):
    """When CORS_ORIGINS is unset, get_allowed_origins returns default localhost list."""
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    
    from app.main import get_allowed_origins
    
    result = get_allowed_origins()
    assert result == ["http://localhost:5173", "http://localhost:3000"]


def test_two_origins_with_spaces(monkeypatch):
    """Comma-separated origins with whitespace are parsed correctly."""
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com , https://www.example.com")
    
    from app.main import get_allowed_origins
    
    result = get_allowed_origins()
    assert result == ["https://app.example.com", "https://www.example.com"]


def test_empty_string_returns_default(monkeypatch):
    """Empty CORS_ORIGINS string returns default list."""
    monkeypatch.setenv("CORS_ORIGINS", "")
    
    from app.main import get_allowed_origins
    
    result = get_allowed_origins()
    assert result == ["http://localhost:5173", "http://localhost:3000"]


def test_wildcard_alone_returns_default(monkeypatch):
    """Wildcard '*' alone is filtered out and returns default list."""
    monkeypatch.setenv("CORS_ORIGINS", "*")
    
    from app.main import get_allowed_origins
    
    result = get_allowed_origins()
    assert result == ["http://localhost:5173", "http://localhost:3000"]


def test_wildcard_with_origin_filters_wildcard(monkeypatch):
    """Wildcard mixed with valid origin returns only the valid origin."""
    monkeypatch.setenv("CORS_ORIGINS", "*,https://a.com")
    
    from app.main import get_allowed_origins
    
    result = get_allowed_origins()
    assert result == ["https://a.com"]


def test_single_origin(monkeypatch):
    """Single origin without commas works correctly."""
    monkeypatch.setenv("CORS_ORIGINS", "https://production.example.com")
    
    from app.main import get_allowed_origins
    
    result = get_allowed_origins()
    assert result == ["https://production.example.com"]


def test_multiple_origins_no_spaces(monkeypatch):
    """Multiple comma-separated origins without spaces work correctly."""
    monkeypatch.setenv("CORS_ORIGINS", "https://a.com,https://b.com,https://c.com")
    
    from app.main import get_allowed_origins
    
    result = get_allowed_origins()
    assert result == ["https://a.com", "https://b.com", "https://c.com"]


def test_empty_items_filtered(monkeypatch):
    """Empty items from multiple commas are filtered out."""
    monkeypatch.setenv("CORS_ORIGINS", "https://a.com,,https://b.com,  ,https://c.com")
    
    from app.main import get_allowed_origins
    
    result = get_allowed_origins()
    assert result == ["https://a.com", "https://b.com", "https://c.com"]
