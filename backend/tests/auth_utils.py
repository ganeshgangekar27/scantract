"""
Authentication utilities for tests.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.db.models import User


def create_test_db_engine():
    """Create async engine for scantract_test with NullPool."""
    return create_async_engine(
        "postgresql+asyncpg://postgres:devpass@localhost:5432/scantract_test",
        poolclass=NullPool,
        echo=False
    )


async def get_test_db() -> AsyncGenerator[AsyncSession, None]:
    """Override get_db dependency for tests."""
    engine = create_test_db_engine()
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


def create_mock_user(user_id: int = 1, email: str = "test@example.com") -> User:
    """Create a mock User instance for testing."""
    return User(
        id=user_id,
        email=email,
        password_hash="$2b$12$test",
        full_name="Test User",
        is_active=True
    )


async def mock_get_current_user() -> User:
    """Mock get_current_user dependency for tests."""
    return create_mock_user()


def mock_get_current_user_sync() -> User:
    """Mock get_current_user dependency for synchronous tests (TestClient)."""
    return create_mock_user()


