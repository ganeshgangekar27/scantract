"""
Authentication and authorization tests with real database.

Uses scantract_test database via existing conftest/db_config.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from datetime import datetime, timedelta
import hashlib

from app.main import app
from app.db.database import AsyncSessionLocal


client = TestClient(app)


@pytest.fixture
async def clean_auth_tables():
    """Clean auth tables before and after each test."""
    async with AsyncSessionLocal() as db:
        # Clean before
        await db.execute(text("DELETE FROM password_reset_tokens WHERE id >= 900000"))
        await db.execute(text("DELETE FROM contracts WHERE id >= 900000"))
        await db.execute(text("DELETE FROM users WHERE id >= 900000"))
        await db.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 900000"))
        await db.execute(text("ALTER SEQUENCE contracts_id_seq RESTART WITH 900000"))
        await db.execute(text("ALTER SEQUENCE password_reset_tokens_id_seq RESTART WITH 900000"))
        await db.commit()
    
    yield
    
    # Clean after
    async with AsyncSessionLocal() as db:
        await db.execute(text("DELETE FROM password_reset_tokens WHERE id >= 900000"))
        await db.execute(text("DELETE FROM contracts WHERE id >= 900000"))
        await db.execute(text("DELETE FROM users WHERE id >= 900000"))
        await db.commit()


def test_register_success(clean_auth_tables):
    """Register new user returns 201 with token or user info."""
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data or "user" in data
    if "access_token" in data:
        assert len(data["access_token"]) > 0


def test_register_duplicate_email(clean_auth_tables):
    """Duplicate email (case-insensitive) returns 409."""
    # Register first user
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    })
    
    # Try duplicate (same case)
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "different123",
        "full_name": "Another User"
    })
    assert response.status_code == 409
    assert "email" in response.json()["detail"].lower() or "already" in response.json()["detail"].lower()
    
    # Try duplicate (different case)
    response = client.post("/api/auth/register", json={
        "email": "TEST@EXAMPLE.COM",
        "password": "different123",
        "full_name": "Another User"
    })
    assert response.status_code == 409


def test_register_invalid_email(clean_auth_tables):
    """Invalid email format returns 422."""
    response = client.post("/api/auth/register", json={
        "email": "not-an-email",
        "password": "password123",
        "full_name": "Test User"
    })
    assert response.status_code == 422


def test_register_short_password(clean_auth_tables):
    """Password < 8 characters returns 422."""
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "short",
        "full_name": "Test User"
    })
    assert response.status_code == 422


def test_login_correct_credentials(clean_auth_tables):
    """Correct credentials return 200 with access_token."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    })
    
    # Login
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert len(data["access_token"]) > 0


def test_login_unknown_email(clean_auth_tables):
    """Unknown email returns 401 with specific message."""
    response = client.post("/api/auth/login", json={
        "email": "unknown@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 401
    detail = response.json()["detail"].lower()
    assert "no account" in detail or "not found" in detail or "email" in detail


def test_login_wrong_password(clean_auth_tables):
    """Wrong password returns 401 with specific message."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    })
    
    # Login with wrong password
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    detail = response.json()["detail"].lower()
    assert "incorrect" in detail or "password" in detail or "wrong" in detail


def test_get_me_with_token(clean_auth_tables):
    """GET /api/auth/me with valid token returns user info."""
    # Register
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    })
    token = response.json()["access_token"]
    
    # Get me
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


def test_get_me_without_token(clean_auth_tables):
    """GET /api/auth/me without token returns 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401 or response.status_code == 403


@pytest.mark.asyncio
async def test_isolation_user_a_sees_only_own_contracts(clean_auth_tables):
    """User A sees only their own contracts in list."""
    # Register users
    response_a = client.post("/api/auth/register", json={
        "email": "usera@example.com",
        "password": "password123",
        "full_name": "User A"
    })
    token_a = response_a.json()["access_token"]
    
    response_b = client.post("/api/auth/register", json={
        "email": "userb@example.com",
        "password": "password123",
        "full_name": "User B"
    })
    token_b = response_b.json()["access_token"]
    
    # Get user IDs from /api/auth/me
    me_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    me_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()
    user_a_id = me_a["id"]
    user_b_id = me_b["id"]
    
    # Insert contracts directly
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, user_id)
            VALUES (900001, 'rental', 'a1.pdf', :now, 'completed', :user_a),
                   (900002, 'rental', 'a2.pdf', :now, 'completed', :user_a),
                   (900003, 'rental', 'b1.pdf', :now, 'completed', :user_b)
        """), {"now": datetime.utcnow(), "user_a": user_a_id, "user_b": user_b_id})
        await db.commit()
    
    # User A lists contracts
    response = client.get("/api/contracts/list", headers={"Authorization": f"Bearer {token_a}"})
    assert response.status_code == 200
    contracts = response.json()
    contract_ids = [c["contract_id"] for c in contracts]
    
    assert 900001 in contract_ids
    assert 900002 in contract_ids
    assert 900003 not in contract_ids


@pytest.mark.asyncio
async def test_isolation_cannot_access_other_user_contract(clean_auth_tables):
    """User A cannot access User B's contract (404, not 403)."""
    # Register users
    response_a = client.post("/api/auth/register", json={
        "email": "usera@example.com",
        "password": "password123",
        "full_name": "User A"
    })
    token_a = response_a.json()["access_token"]
    
    response_b = client.post("/api/auth/register", json={
        "email": "userb@example.com",
        "password": "password123",
        "full_name": "User B"
    })
    
    me_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {response_b.json()['access_token']}"}).json()
    user_b_id = me_b["id"]
    
    # Insert contract for User B
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, pipeline_stage, user_id)
            VALUES (900010, 'rental', 'b.pdf', :now, 'completed', 'completed', :user_b)
        """), {"now": datetime.utcnow(), "user_b": user_b_id})
        await db.commit()
    
    # User A tries to access User B's contract
    response = client.get("/api/contracts/900010/report", headers={"Authorization": f"Bearer {token_a}"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_isolation_no_token_returns_401(clean_auth_tables):
    """No token returns 401 on protected routes."""
    # Insert contract
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, user_id)
            VALUES (900020, 'rental', 'test.pdf', :now, 'completed', 900000)
        """), {"now": datetime.utcnow()})
        await db.commit()
    
    # Try without token
    response = client.get("/api/contracts/list")
    assert response.status_code == 401 or response.status_code == 403
    
    response = client.get("/api/contracts/900020/report")
    assert response.status_code == 401 or response.status_code == 403


@pytest.mark.asyncio
async def test_isolation_legacy_contracts_not_visible(clean_auth_tables):
    """Legacy contracts (user_id NULL) are not visible to any user."""
    # Register user
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    })
    token = response.json()["access_token"]
    
    # Insert legacy contract (user_id NULL)
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, user_id)
            VALUES (900030, 'rental', 'legacy.pdf', :now, 'completed', NULL)
        """), {"now": datetime.utcnow()})
        await db.commit()
    
    # List contracts
    response = client.get("/api/contracts/list", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    contract_ids = [c["contract_id"] for c in response.json()]
    assert 900030 not in contract_ids


def test_forgot_password_known_email(clean_auth_tables):
    """Forgot password with known email returns 200 and creates token."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    })
    
    # Forgot password
    response = client.post("/api/auth/forgot-password", json={
        "email": "test@example.com"
    })
    
    assert response.status_code == 200
    data = response.json()
    # In demo mode, should include demo_reset_link
    if "demo_reset_link" in data:
        assert "token=" in data["demo_reset_link"]


def test_forgot_password_unknown_email(clean_auth_tables):
    """Forgot password with unknown email returns same 200 response."""
    response = client.post("/api/auth/forgot-password", json={
        "email": "unknown@example.com"
    })
    
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_forgot_password_token_not_stored_plaintext(clean_auth_tables):
    """Token in database is hashed, not plaintext."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User"
    })
    
    # Forgot password
    response = client.post("/api/auth/forgot-password", json={
        "email": "test@example.com"
    })
    
    # Extract token from demo_reset_link if present
    if "demo_reset_link" in response.json():
        link = response.json()["demo_reset_link"]
        raw_token = link.split("token=")[1]
        
        # Check database
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT token_hash FROM password_reset_tokens WHERE id >= 900000"))
            token_hash = result.scalar_one()
            
            # Hash should be 64 chars (SHA-256 hex)
            assert len(token_hash) == 64
            assert token_hash != raw_token


def test_reset_password_valid_token(clean_auth_tables):
    """Valid token + new password returns 200, login works with new password."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "oldpassword",
        "full_name": "Test User"
    })
    
    # Forgot password
    forgot_response = client.post("/api/auth/forgot-password", json={
        "email": "test@example.com"
    })
    
    # Extract token
    link = forgot_response.json()["demo_reset_link"]
    token = link.split("token=")[1]
    
    # Reset password
    response = client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "newpassword"
    })
    
    assert response.status_code == 200
    
    # Login with new password
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "newpassword"
    })
    assert response.status_code == 200
    
    # Login with old password fails
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "oldpassword"
    })
    assert response.status_code == 401


def test_reset_password_token_used_twice(clean_auth_tables):
    """Using same token twice returns 400."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "oldpassword",
        "full_name": "Test User"
    })
    
    # Forgot password
    forgot_response = client.post("/api/auth/forgot-password", json={
        "email": "test@example.com"
    })
    token = forgot_response.json()["demo_reset_link"].split("token=")[1]
    
    # Reset password first time
    client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "newpassword"
    })
    
    # Try again
    response = client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "anotherpassword"
    })
    
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "used" in detail or "already" in detail


@pytest.mark.asyncio
async def test_reset_password_expired_token(clean_auth_tables):
    """Expired token returns 400."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "oldpassword",
        "full_name": "Test User"
    })
    
    # Forgot password
    forgot_response = client.post("/api/auth/forgot-password", json={
        "email": "test@example.com"
    })
    token = forgot_response.json()["demo_reset_link"].split("token=")[1]
    
    # Expire the token
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            UPDATE password_reset_tokens 
            SET expires_at = :past 
            WHERE id >= 900000
        """), {"past": datetime.utcnow() - timedelta(hours=1)})
        await db.commit()
    
    # Try to reset
    response = client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "newpassword"
    })
    
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "expired" in detail or "invalid" in detail


def test_reset_password_garbage_token(clean_auth_tables):
    """Garbage token returns 400."""
    response = client.post("/api/auth/reset-password", json={
        "token": "garbage-token-12345",
        "new_password": "newpassword"
    })
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_password_hashing_not_plaintext(clean_auth_tables):
    """Stored password is not plaintext."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "mypassword",
        "full_name": "Test User"
    })
    
    # Check database
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT password_hash FROM users WHERE id >= 900000"))
        password_hash = result.scalar_one()
        
        assert password_hash != "mypassword"
        assert len(password_hash) > 20  # Should be a hash


@pytest.mark.asyncio
async def test_password_hashing_different_salts(clean_auth_tables):
    """Two users with same password get different hashes."""
    # Register user 1
    client.post("/api/auth/register", json={
        "email": "user1@example.com",
        "password": "samepassword",
        "full_name": "User 1"
    })
    
    # Register user 2
    client.post("/api/auth/register", json={
        "email": "user2@example.com",
        "password": "samepassword",
        "full_name": "User 2"
    })
    
    # Check database
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("SELECT password_hash FROM users WHERE id >= 900000 ORDER BY id"))
        hashes = result.scalars().all()
        
        assert len(hashes) == 2
        assert hashes[0] != hashes[1]
