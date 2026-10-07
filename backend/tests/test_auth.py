"""
Authentication and authorization tests with real database.

Uses scantract_test database via httpx.AsyncClient.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from datetime import datetime, timedelta

from app.main import app
from app.db.database import get_db
from tests.auth_utils import get_test_db


# Override get_db for all auth tests
app.dependency_overrides[get_db] = get_test_db


async def cleanup_test_data():
    """Clean up test data from database."""
    async for db in get_test_db():
        await db.execute(text("DELETE FROM password_reset_tokens WHERE id >= 900000"))
        await db.execute(text("DELETE FROM contracts WHERE id >= 900000"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        await db.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 900000"))
        await db.execute(text("ALTER SEQUENCE contracts_id_seq RESTART WITH 900000"))
        await db.execute(text("ALTER SEQUENCE password_reset_tokens_id_seq RESTART WITH 900000"))
        await db.commit()
        break


@pytest.mark.asyncio
async def test_register_success():
    """Register new user returns 201 with token."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/register", json={
                "email": "test1@example.com",
                "password": "password123",
                "full_name": "Test User"
            })
        
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.json()}"
        data = response.json()
        assert "access_token" in data
        assert len(data["access_token"]) > 0
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_register_duplicate_email():
    """Duplicate email (case-insensitive) returns 409."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register first user
            await client.post("/api/auth/register", json={
                "email": "test2@example.com",
                "password": "password123",
                "full_name": "Test User"
            })
            
            # Try duplicate (same case)
            response = await client.post("/api/auth/register", json={
                "email": "test2@example.com",
                "password": "different123",
                "full_name": "Another User"
            })
            assert response.status_code == 409
            
            # Try duplicate (different case)
            response = await client.post("/api/auth/register", json={
                "email": "TEST2@example.com",
                "password": "different123",
                "full_name": "Another User"
            })
            assert response.status_code == 409
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_register_invalid_email():
    """Invalid email format returns 422."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/register", json={
                "email": "not-an-email",
                "password": "password123",
                "full_name": "Test User"
            })
        
        assert response.status_code == 422
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_register_short_password():
    """Password < 8 characters returns 422."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/register", json={
                "email": "test3@example.com",
                "password": "short",
                "full_name": "Test User"
            })
        
        assert response.status_code == 422
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_login_correct_credentials():
    """Correct credentials return 200 with access_token."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            await client.post("/api/auth/register", json={
                "email": "test4@example.com",
                "password": "password123",
                "full_name": "Test User"
            })
            
            # Login
            response = await client.post("/api/auth/login", json={
                "email": "test4@example.com",
                "password": "password123"
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_login_unknown_email():
    """Unknown email returns 401 with specific message."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/login", json={
                "email": "unknown@example.com",
                "password": "password123"
            })
        
        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert "no account" in detail or "not found" in detail
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_login_wrong_password():
    """Wrong password returns 401 with specific message."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            await client.post("/api/auth/register", json={
                "email": "test5@example.com",
                "password": "password123",
                "full_name": "Test User"
            })
            
            # Login with wrong password
            response = await client.post("/api/auth/login", json={
                "email": "test5@example.com",
                "password": "wrongpassword"
            })
        
        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert "incorrect" in detail or "password" in detail
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_get_me_with_token():
    """GET /api/auth/me with valid token returns user info."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            response = await client.post("/api/auth/register", json={
                "email": "test6@example.com",
                "password": "password123",
                "full_name": "Test User"
            })
            token = response.json()["access_token"]
            
            # Get me
            response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test6@example.com"
        assert data["full_name"] == "Test User"
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_get_me_without_token():
    """GET /api/auth/me without token returns 401."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/auth/me")
        
        assert response.status_code == 401 or response.status_code == 403
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_isolation_user_a_sees_only_own_contracts():
    """User A sees only their own contracts in list."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register users
            response_a = await client.post("/api/auth/register", json={
                "email": "usera@example.com",
                "password": "password123",
                "full_name": "User A"
            })
            token_a = response_a.json()["access_token"]
            
            response_b = await client.post("/api/auth/register", json={
                "email": "userb@example.com",
                "password": "password123",
                "full_name": "User B"
            })
            token_b = response_b.json()["access_token"]
            
            # Get user IDs
            me_a = (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"})).json()
            me_b = (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"})).json()
            user_a_id = me_a["id"]
            user_b_id = me_b["id"]
        
        # Insert contracts directly
        async for db in get_test_db():
            await db.execute(text("""
                INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, user_id)
                VALUES (900001, 'rental', 'a1.pdf', :now, 'completed', :user_a),
                       (900002, 'rental', 'a2.pdf', :now, 'completed', :user_a),
                       (900003, 'rental', 'b1.pdf', :now, 'completed', :user_b)
            """), {"now": datetime.utcnow(), "user_a": user_a_id, "user_b": user_b_id})
            await db.commit()
            break
        
        # User A lists contracts
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/contracts/list", headers={"Authorization": f"Bearer {token_a}"})
        
        assert response.status_code == 200
        contracts = response.json()
        contract_ids = [c["contract_id"] for c in contracts]
        
        assert 900001 in contract_ids
        assert 900002 in contract_ids
        assert 900003 not in contract_ids
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_isolation_cannot_access_other_user_contract():
    """User A cannot access User B's contract (404)."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register users
            response_a = await client.post("/api/auth/register", json={
                "email": "usera2@example.com",
                "password": "password123",
                "full_name": "User A"
            })
            token_a = response_a.json()["access_token"]
            
            response_b = await client.post("/api/auth/register", json={
                "email": "userb2@example.com",
                "password": "password123",
                "full_name": "User B"
            })
            token_b = response_b.json()["access_token"]
            
            me_b = (await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"})).json()
            user_b_id = me_b["id"]
        
        # Insert contract for User B
        async for db in get_test_db():
            await db.execute(text("""
                INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, pipeline_stage, user_id)
                VALUES (900010, 'rental', 'b.pdf', :now, 'completed', 'completed', :user_b)
            """), {"now": datetime.utcnow(), "user_b": user_b_id})
            await db.commit()
            break
        
        # User A tries to access User B's contract
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/contracts/900010/report", headers={"Authorization": f"Bearer {token_a}"})
        
        assert response.status_code == 404
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_isolation_no_token_returns_401():
    """No token returns 401 on protected routes."""
    try:
        await cleanup_test_data()
        
        async for db in get_test_db():
            # Create user first
            await db.execute(text("""
                INSERT INTO users (id, email, password_hash, full_name, created_at, is_active)
                VALUES (900000, 'dummy@example.com', 'hash', 'Dummy', :now, true)
            """), {"now": datetime.utcnow()})
            await db.execute(text("""
                INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, user_id)
                VALUES (900020, 'rental', 'test.pdf', :now, 'completed', 900000)
            """), {"now": datetime.utcnow()})
            await db.commit()
            break
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/contracts/list")
            assert response.status_code == 401 or response.status_code == 403
            
            response = await client.get("/api/contracts/900020/report")
            assert response.status_code == 401 or response.status_code == 403
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_isolation_legacy_contracts_not_visible():
    """Legacy contracts (user_id NULL) are not visible to any user."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register user
            response = await client.post("/api/auth/register", json={
                "email": "test7@example.com",
                "password": "password123",
                "full_name": "Test User"
            })
            token = response.json()["access_token"]
        
        # Insert legacy contract (user_id NULL)
        async for db in get_test_db():
            await db.execute(text("""
                INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, user_id)
                VALUES (900030, 'rental', 'legacy.pdf', :now, 'completed', NULL)
            """), {"now": datetime.utcnow()})
            await db.commit()
            break
        
        # List contracts
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/contracts/list", headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 200
        contract_ids = [c["contract_id"] for c in response.json()]
        assert 900030 not in contract_ids
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_forgot_password_known_email():
    """Forgot password with known email returns 200 and creates token."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            await client.post("/api/auth/register", json={
                "email": "test8@example.com",
                "password": "password123",
                "full_name": "Test User"
            })
            
            # Forgot password
            response = await client.post("/api/auth/forgot-password", json={
                "email": "test8@example.com"
            })
        
        assert response.status_code == 200
        data = response.json()
        if "demo_reset_link" in data:
            assert "token=" in data["demo_reset_link"]
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_forgot_password_unknown_email():
    """Forgot password with unknown email returns same 200 response."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/forgot-password", json={
                "email": "unknown2@example.com"
            })
        
        assert response.status_code == 200
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_forgot_password_token_not_stored_plaintext():
    """Token in database is hashed, not plaintext."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            await client.post("/api/auth/register", json={
                "email": "test9@example.com",
                "password": "password123",
                "full_name": "Test User"
            })
            
            # Forgot password
            response = await client.post("/api/auth/forgot-password", json={
                "email": "test9@example.com"
            })
        
        if "demo_reset_link" in response.json():
            link = response.json()["demo_reset_link"]
            raw_token = link.split("token=")[1]
            
            # Check database
            async for db in get_test_db():
                result = await db.execute(text("SELECT token_hash FROM password_reset_tokens WHERE id >= 900000"))
                token_hash = result.scalar_one()
                
                assert len(token_hash) == 64
                assert token_hash != raw_token
                break
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_reset_password_valid_token():
    """Valid token + new password returns 200, login works with new password."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            await client.post("/api/auth/register", json={
                "email": "test10@example.com",
                "password": "oldpassword",
                "full_name": "Test User"
            })
            
            # Forgot password
            forgot_response = await client.post("/api/auth/forgot-password", json={
                "email": "test10@example.com"
            })
            
            link = forgot_response.json()["demo_reset_link"]
            token = link.split("token=")[1]
            
            # Reset password
            response = await client.post("/api/auth/reset-password", json={
                "token": token,
                "new_password": "newpassword"
            })
            assert response.status_code == 200
            
            # Login with new password
            response = await client.post("/api/auth/login", json={
                "email": "test10@example.com",
                "password": "newpassword"
            })
            assert response.status_code == 200
            
            # Login with old password fails
            response = await client.post("/api/auth/login", json={
                "email": "test10@example.com",
                "password": "oldpassword"
            })
            assert response.status_code == 401
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_reset_password_token_used_twice():
    """Using same token twice returns 400."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            await client.post("/api/auth/register", json={
                "email": "test11@example.com",
                "password": "oldpassword",
                "full_name": "Test User"
            })
            
            # Forgot password
            forgot_response = await client.post("/api/auth/forgot-password", json={
                "email": "test11@example.com"
            })
            token = forgot_response.json()["demo_reset_link"].split("token=")[1]
            
            # Reset password first time
            await client.post("/api/auth/reset-password", json={
                "token": token,
                "new_password": "newpassword"
            })
            
            # Try again
            response = await client.post("/api/auth/reset-password", json={
                "token": token,
                "new_password": "anotherpassword"
            })
        
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "used" in detail or "already" in detail
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_reset_password_expired_token():
    """Expired token returns 400."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            await client.post("/api/auth/register", json={
                "email": "test12@example.com",
                "password": "oldpassword",
                "full_name": "Test User"
            })
            
            # Forgot password
            forgot_response = await client.post("/api/auth/forgot-password", json={
                "email": "test12@example.com"
            })
            token = forgot_response.json()["demo_reset_link"].split("token=")[1]
        
        # Expire the token
        async for db in get_test_db():
            await db.execute(text("""
                UPDATE password_reset_tokens 
                SET expires_at = :past 
                WHERE id >= 900000
            """), {"past": datetime.utcnow() - timedelta(hours=1)})
            await db.commit()
            break
        
        # Try to reset
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/reset-password", json={
                "token": token,
                "new_password": "newpassword"
            })
        
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "expired" in detail or "invalid" in detail
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_reset_password_garbage_token():
    """Garbage token returns 400."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/auth/reset-password", json={
                "token": "garbage-token-12345",
                "new_password": "newpassword"
            })
        
        assert response.status_code == 400
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_password_hashing_not_plaintext():
    """Stored password is not plaintext."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            await client.post("/api/auth/register", json={
                "email": "test13@example.com",
                "password": "mypassword",
                "full_name": "Test User"
            })
        
        # Check database
        async for db in get_test_db():
            result = await db.execute(text("SELECT password_hash FROM users WHERE email LIKE '%@example.com' LIMIT 1"))
            password_hash = result.scalar_one()
            
            assert password_hash != "mypassword"
            assert len(password_hash) > 20
            break
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_password_hashing_different_salts():
    """Two users with same password get different hashes."""
    try:
        await cleanup_test_data()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register user 1
            await client.post("/api/auth/register", json={
                "email": "user1@example.com",
                "password": "samepassword",
                "full_name": "User 1"
            })
            
            # Register user 2
            await client.post("/api/auth/register", json={
                "email": "user2@example.com",
                "password": "samepassword",
                "full_name": "User 2"
            })
        
        # Check database
        async for db in get_test_db():
            result = await db.execute(text("SELECT password_hash FROM users WHERE email LIKE '%@example.com' ORDER BY id"))
            hashes = result.scalars().all()
            
            assert len(hashes) == 2
            assert hashes[0] != hashes[1]
            break
    finally:
        await cleanup_test_data()

