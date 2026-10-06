"""
Authentication utilities for tests.
"""
from unittest.mock import MagicMock
from app.db.models import User


def create_mock_user(user_id: int = 1, email: str = "test@example.com") -> User:
    """Create a mock user for testing."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = email
    user.full_name = "Test User"
    user.is_active = True
    return user


async def mock_get_current_user() -> User:
    """Mock get_current_user dependency for tests."""
    return create_mock_user()
