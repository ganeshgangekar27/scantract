"""
Pytest configuration and fixtures for ScanTract backend tests.

This module:
1. Sets DATABASE_URL env var to test database before any imports
2. Guards against running tests on production database
3. Provides shared fixtures
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Import test DB config
from tests.db_config import get_test_database_url

# Set DATABASE_URL to test database BEFORE any app imports
os.environ["DATABASE_URL"] = get_test_database_url()


def pytest_sessionstart(session):
    """
    Hook called after Session object creation, before running tests.
    
    Verifies tests are NOT running against production database.
    """
    import pytest
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    
    test_db_url = get_test_database_url()
    
    async def check_database():
        engine = create_async_engine(test_db_url, echo=False)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                
                # ABORT if database is exactly 'scantract' or doesn't end with 'test' or 'scratch'
                if db_name == 'scantract' or not (db_name.endswith('test') or db_name.endswith('scratch')):
                    pytest.exit(
                        f"SAFETY ABORT: Tests attempted to run against database '{db_name}'. "
                        f"Tests must use a database ending in 'test' or 'scratch', not production DB. "
                        f"Set TEST_DATABASE_URL environment variable to a test database.",
                        returncode=2
                    )
        finally:
            await engine.dispose()
    
    # Run the check
    asyncio.run(check_database())

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.database import get_db
from tests.db_config import get_test_database_url


@pytest.fixture
async def db_session():
    """Provide a clean database session for tests."""
    test_db_url = get_test_database_url()
    engine = create_async_engine(test_db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    """Provide an async HTTP client with database override."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
