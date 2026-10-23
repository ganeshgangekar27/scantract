"""
Tests for database URL conversion utilities.
"""

import pytest
from db_url_utils import to_async_url, to_sync_url, is_pooler_url


class TestIsPoolerUrl:
    """Tests for is_pooler_url function."""
    
    def test_pooler_host_detected(self):
        """URL with -pooler in hostname is detected as pooler."""
        url = "postgresql://user:pass@db-pooler.neon.tech/dbname"
        assert is_pooler_url(url) is True
    
    def test_direct_host_not_pooler(self):
        """URL without -pooler is not detected as pooler."""
        url = "postgresql://user:pass@db.neon.tech/dbname"
        assert is_pooler_url(url) is False
    
    def test_local_compose_url_not_pooler(self):
        """Local docker-compose URL is not a pooler."""
        url = "postgresql+asyncpg://postgres:devpass@db:5432/scantract"
        assert is_pooler_url(url) is False
    
    def test_url_with_no_host(self):
        """URL with no host (path-only) returns False."""
        url = "postgresql+asyncpg:///scantract"
        assert is_pooler_url(url) is False
    
    def test_empty_string(self):
        """Empty string returns False."""
        assert is_pooler_url("") is False
    
    def test_pooler_in_path_not_hostname(self):
        """'-pooler' in path but not hostname is not detected."""
        url = "postgresql://user:pass@db.neon.tech/my-pooler-db"
        assert is_pooler_url(url) is False
    
    def test_pooler_with_port(self):
        """Pooler URL with explicit port is detected."""
        url = "postgresql://user:pass@db-pooler.neon.tech:5432/dbname"
        assert is_pooler_url(url) is True


class TestToAsyncUrl:
    """Tests for to_async_url function."""
    
    def test_local_url_unchanged(self):
        """Local URL without query params remains functionally equivalent."""
        url = "postgresql+asyncpg://postgres:devpass@db:5432/scantract"
        result = to_async_url(url)
        assert result == "postgresql+asyncpg://postgres:devpass@db:5432/scantract"
    
    def test_postgres_scheme_normalized(self):
        """postgres:// scheme is converted to postgresql+asyncpg://."""
        url = "postgres://user:pass@example.neon.tech/dbname"
        result = to_async_url(url)
        assert result.startswith("postgresql+asyncpg://")
        assert "user:pass@example.neon.tech/dbname" in result
    
    def test_sslmode_to_ssl(self):
        """sslmode=require is converted to ssl=require."""
        url = "postgres://user:pass@example.neon.tech/dbname?sslmode=require"
        result = to_async_url(url)
        assert "ssl=require" in result
        assert "sslmode" not in result
    
    def test_channel_binding_dropped(self):
        """channel_binding parameter is removed."""
        url = "postgres://user:pass@example.neon.tech/dbname?sslmode=require&channel_binding=require"
        result = to_async_url(url)
        assert "channel_binding" not in result
        assert "ssl=require" in result
    
    def test_extra_params_kept(self):
        """Other query parameters are preserved."""
        url = "postgres://user:pass@example.neon.tech/dbname?sslmode=require&connect_timeout=10&application_name=scantract"
        result = to_async_url(url)
        assert "ssl=require" in result
        assert "connect_timeout=10" in result
        assert "application_name=scantract" in result
    
    def test_password_with_special_chars(self):
        """URL-encoded passwords are not corrupted."""
        # Password is "p@ss" encoded as "p%40ss"
        url = "postgres://user:p%40ss@example.neon.tech/dbname?sslmode=require"
        result = to_async_url(url)
        assert "user:p%40ss@example.neon.tech" in result
        assert "ssl=require" in result
    
    def test_postgresql_asyncpg_preserved(self):
        """postgresql+asyncpg:// scheme is preserved."""
        url = "postgresql+asyncpg://user:pass@example.neon.tech/dbname?ssl=require"
        result = to_async_url(url)
        assert result.startswith("postgresql+asyncpg://")
        assert "ssl=require" in result
    
    def test_plain_postgresql_scheme(self):
        """postgresql:// scheme is converted to postgresql+asyncpg://."""
        url = "postgresql://user:pass@example.neon.tech/dbname?sslmode=require"
        result = to_async_url(url)
        assert result.startswith("postgresql+asyncpg://")
        assert "ssl=require" in result


class TestToSyncUrl:
    """Tests for to_sync_url function."""
    
    def test_local_url_converted_to_sync(self):
        """Local asyncpg URL is converted to postgresql://."""
        url = "postgresql+asyncpg://postgres:devpass@db:5432/scantract"
        result = to_sync_url(url)
        assert result == "postgresql://postgres:devpass@db:5432/scantract"
    
    def test_asyncpg_scheme_normalized(self):
        """postgresql+asyncpg:// scheme is converted to postgresql://."""
        url = "postgresql+asyncpg://user:pass@example.neon.tech/dbname"
        result = to_sync_url(url)
        assert result.startswith("postgresql://")
        assert "user:pass@example.neon.tech/dbname" in result
    
    def test_ssl_to_sslmode(self):
        """ssl=require is converted to sslmode=require."""
        url = "postgresql+asyncpg://user:pass@example.neon.tech/dbname?ssl=require"
        result = to_sync_url(url)
        assert "sslmode=require" in result
        assert "ssl=" not in result or "sslmode" in result  # ssl should be converted
    
    def test_channel_binding_dropped(self):
        """channel_binding parameter is removed."""
        url = "postgresql+asyncpg://user:pass@example.neon.tech/dbname?ssl=require&channel_binding=require"
        result = to_sync_url(url)
        assert "channel_binding" not in result
        assert "sslmode=require" in result
    
    def test_extra_params_kept(self):
        """Other query parameters are preserved."""
        url = "postgresql+asyncpg://user:pass@example.neon.tech/dbname?ssl=require&connect_timeout=10&application_name=scantract"
        result = to_sync_url(url)
        assert "sslmode=require" in result
        assert "connect_timeout=10" in result
        assert "application_name=scantract" in result
    
    def test_password_with_special_chars(self):
        """URL-encoded passwords are not corrupted."""
        # Password is "p@ss" encoded as "p%40ss"
        url = "postgresql+asyncpg://user:p%40ss@example.neon.tech/dbname?ssl=require"
        result = to_sync_url(url)
        assert "user:p%40ss@example.neon.tech" in result
        assert "sslmode=require" in result
    
    def test_postgres_scheme_handled(self):
        """postgres:// scheme is converted to postgresql://."""
        url = "postgres://user:pass@example.neon.tech/dbname?sslmode=require"
        result = to_sync_url(url)
        assert result.startswith("postgresql://")
        assert "sslmode=require" in result
    
    def test_plain_postgresql_preserved(self):
        """postgresql:// scheme remains postgresql://."""
        url = "postgresql://user:pass@example.neon.tech/dbname?sslmode=require"
        result = to_sync_url(url)
        assert result.startswith("postgresql://")
        assert "sslmode=require" in result


class TestRoundTrip:
    """Test conversion round-trips."""
    
    def test_neon_url_roundtrip(self):
        """URL can be converted to async and back to sync."""
        original = "postgres://user:pass@example.neon.tech/dbname?sslmode=require"
        async_url = to_async_url(original)
        sync_url = to_sync_url(async_url)
        
        # Both should have the core connection info
        assert "user:pass@example.neon.tech/dbname" in async_url
        assert "user:pass@example.neon.tech/dbname" in sync_url
        
        # Async should have ssl param
        assert "ssl=require" in async_url
        
        # Sync should have sslmode param
        assert "sslmode=require" in sync_url
