"""
Database configuration for tests.

Provides a centralized way to configure test database URL,
allowing tests to run against an isolated test database.
"""
import os


def get_test_database_url() -> str:
    """
    Get the test database URL from environment or use default.
    
    Returns:
        str: Database URL for tests, pointing to scantract_test by default
    """
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:devpass@localhost:5432/scantract_test"
    )
