"""
Database URL utilities for converting between async and sync connection strings.

Handles URL schemes and query parameters for managed Postgres providers (e.g., Neon)
that may provide URLs with varying formats and SSL requirements.
"""

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def is_pooler_url(url: str) -> bool:
    """
    Check if a database URL points to a connection pooler (e.g., pgbouncer).
    
    Detects pooler URLs by checking if the hostname contains "-pooler".
    This is a common naming pattern for managed Postgres providers like Neon.
    
    Args:
        url: Database connection URL
        
    Returns:
        True if hostname exists and contains "-pooler", False otherwise
        
    Examples:
        >>> is_pooler_url("postgresql://user:pass@db-pooler.neon.tech/dbname")
        True
        
        >>> is_pooler_url("postgresql://user:pass@db.neon.tech/dbname")
        False
        
        >>> is_pooler_url("postgresql+asyncpg://postgres:devpass@db:5432/scantract")
        False
        
        >>> is_pooler_url("")
        False
    """
    if not url:
        return False
    
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    if not hostname:
        return False
    
    return "-pooler" in hostname


def to_async_url(url: str) -> str:
    """
    Convert a database URL to asyncpg-compatible format.
    
    Transformations:
    - Scheme: postgres:// or postgresql:// -> postgresql+asyncpg://
    - Query params: sslmode=X -> ssl=X
    - Removes: channel_binding parameter
    - Preserves: all other query parameters
    - Unchanged: URLs without query params (e.g., local development URLs)
    
    Args:
        url: Database connection URL in any supported format
        
    Returns:
        URL with postgresql+asyncpg:// scheme and asyncpg-compatible params
        
    Examples:
        >>> to_async_url("postgres://user:pass@host/db?sslmode=require")
        'postgresql+asyncpg://user:pass@host/db?ssl=require'
        
        >>> to_async_url("postgresql+asyncpg://postgres:devpass@db:5432/scantract")
        'postgresql+asyncpg://postgres:devpass@db:5432/scantract'
    """
    parsed = urlparse(url)
    
    # Normalize scheme to postgresql+asyncpg
    if parsed.scheme in ("postgres", "postgresql", "postgresql+asyncpg"):
        scheme = "postgresql+asyncpg"
    else:
        # Unknown scheme, leave as-is
        scheme = parsed.scheme
    
    # Parse query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Convert sslmode to ssl for asyncpg
    if "sslmode" in query_params:
        ssl_value = query_params.pop("sslmode")
        query_params["ssl"] = ssl_value
    
    # Remove channel_binding (not supported by asyncpg)
    query_params.pop("channel_binding", None)
    
    # Rebuild query string (flatten list values from parse_qs)
    new_query = urlencode({k: v[0] if isinstance(v, list) else v for k, v in query_params.items()})
    
    # Reconstruct URL
    return urlunparse((
        scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


def to_sync_url(url: str) -> str:
    """
    Convert a database URL to psycopg2-compatible format (for Alembic).
    
    Transformations:
    - Scheme: postgres://, postgresql://, or postgresql+asyncpg:// -> postgresql://
    - Query params: ssl=X -> sslmode=X
    - Removes: channel_binding parameter
    - Preserves: all other query parameters
    - Unchanged: URLs without query params (e.g., local development URLs)
    
    Args:
        url: Database connection URL in any supported format
        
    Returns:
        URL with postgresql:// scheme and psycopg2-compatible params
        
    Examples:
        >>> to_sync_url("postgresql+asyncpg://user:pass@host/db?ssl=require")
        'postgresql://user:pass@host/db?sslmode=require'
        
        >>> to_sync_url("postgresql+asyncpg://postgres:devpass@db:5432/scantract")
        'postgresql://postgres:devpass@db:5432/scantract'
    """
    parsed = urlparse(url)
    
    # Normalize scheme to postgresql (sync)
    if parsed.scheme in ("postgres", "postgresql", "postgresql+asyncpg"):
        scheme = "postgresql"
    else:
        # Unknown scheme, leave as-is
        scheme = parsed.scheme
    
    # Parse query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    
    # Convert ssl to sslmode for psycopg2
    if "ssl" in query_params:
        ssl_value = query_params.pop("ssl")
        query_params["sslmode"] = ssl_value
    
    # Remove channel_binding (may not be supported)
    query_params.pop("channel_binding", None)
    
    # Rebuild query string (flatten list values from parse_qs)
    new_query = urlencode({k: v[0] if isinstance(v, list) else v for k, v in query_params.items()})
    
    # Reconstruct URL
    return urlunparse((
        scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))
