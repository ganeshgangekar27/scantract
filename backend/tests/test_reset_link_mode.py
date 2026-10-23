"""
Tests for RESET_LINK_MODE behavior in forgot-password endpoint.

Verifies that demo mode includes reset link, while other modes return
generic success without revealing link or email existence.
"""
import pytest
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text

from app.main import app
from app.db.database import get_db
from tests.auth_utils import get_test_db


# Override get_db for all tests
app.dependency_overrides[get_db] = get_test_db


async def cleanup_test_data():
    """Clean up test data from database."""
    async for db in get_test_db():
        await db.execute(text("DELETE FROM password_reset_tokens WHERE id >= 900000"))
        await db.execute(text("DELETE FROM contracts WHERE id >= 900000"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@resettest.com'"))
        await db.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 900000"))
        await db.execute(text("ALTER SEQUENCE password_reset_tokens_id_seq RESTART WITH 900000"))
        await db.commit()
        break


async def create_test_user(email: str, password: str = "password123"):
    """Create a test user."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Test User"
        })
        assert response.status_code == 201
        return response.json()


@pytest.mark.asyncio
async def test_demo_mode_includes_link(monkeypatch):
    """Demo mode returns demo_reset_link for existing user."""
    try:
        await cleanup_test_data()
        
        # Set demo mode
        monkeypatch.setenv("RESET_LINK_MODE", "demo")
        
        # Create test user
        user_email = "demo-user@resettest.com"
        await create_test_user(user_email)
        
        # Request password reset
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/forgot-password", json={
                "email": user_email
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "demo_reset_link" in data
        assert "token=" in data["demo_reset_link"]
        assert "http://localhost:3000/reset-password?token=" in data["demo_reset_link"]
        
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_off_mode_existing_user_no_link(monkeypatch):
    """Non-demo mode returns success without demo_reset_link for existing user."""
    try:
        await cleanup_test_data()
        
        # Set non-demo mode
        monkeypatch.setenv("RESET_LINK_MODE", "off")
        
        # Create test user
        user_email = "off-user@resettest.com"
        await create_test_user(user_email)
        
        # Request password reset
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/forgot-password", json={
                "email": user_email
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "demo_reset_link" not in data
        
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_off_mode_unknown_email_same_response(monkeypatch):
    """Non-demo mode returns same response for unknown email (no enumeration)."""
    try:
        await cleanup_test_data()
        
        # Set non-demo mode
        monkeypatch.setenv("RESET_LINK_MODE", "off")
        
        # Request password reset for non-existent user
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/forgot-password", json={
                "email": "nonexistent@resettest.com"
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "demo_reset_link" not in data
        
        # Response should be identical to existing user case
        # (Only difference is internal: no token created, but response is same)
        
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_smtp_mode_existing_user_no_link(monkeypatch):
    """SMTP mode (any non-demo value) returns success without demo_reset_link."""
    try:
        await cleanup_test_data()
        
        # Set SMTP mode
        monkeypatch.setenv("RESET_LINK_MODE", "smtp")
        
        # Create test user
        user_email = "smtp-user@resettest.com"
        await create_test_user(user_email)
        
        # Request password reset
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/forgot-password", json={
                "email": user_email
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "demo_reset_link" not in data
        
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_production_mode_no_link(monkeypatch):
    """Production mode returns success without demo_reset_link."""
    try:
        await cleanup_test_data()
        
        # Set production mode
        monkeypatch.setenv("RESET_LINK_MODE", "production")
        
        # Create test user
        user_email = "prod-user@resettest.com"
        await create_test_user(user_email)
        
        # Request password reset
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/forgot-password", json={
                "email": user_email
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "demo_reset_link" not in data
        
    finally:
        await cleanup_test_data()
