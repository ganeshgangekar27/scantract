"""
Route isolation tests: ownership checks, 401 on missing auth, LLM not called on auth failures.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.main import app
from app.db.database import get_db
from tests.auth_utils import get_test_db


# Override get_db for all tests
app.dependency_overrides[get_db] = get_test_db


async def setup_test_users_and_contract():
    """Create two users and one contract owned by user A."""
    async for db in get_test_db():
        # Clean up
        await db.execute(text("DELETE FROM contracts WHERE id >= 900000"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        await db.commit()
        
        # Create users
        await db.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, created_at, is_active)
            VALUES 
                (900001, 'usera@example.com', '$2b$12$test', 'User A', :now, true),
                (900002, 'userb@example.com', '$2b$12$test', 'User B', :now, true)
        """), {"now": datetime.now()})
        
        # Create contract owned by user A
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, uploaded_at, processing_status, user_id)
            VALUES (900010, 'rental', 'test.pdf', :now, 'completed', 900001)
        """), {"now": datetime.now()})
        
        await db.commit()
        break
    
    return 900001, 900002, 900010


async def cleanup_test_data():
    """Clean up test data."""
    async for db in get_test_db():
        await db.execute(text("DELETE FROM contracts WHERE id >= 900000"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@example.com'"))
        await db.commit()
        break


def get_token_for_user(email: str, user_id: int) -> str:
    """Generate JWT token for a test user."""
    from app.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, email=email)


@pytest.mark.parametrize("route_template,method", [
    ("/api/contracts/{id}/report", "GET"),
    ("/api/contracts/{id}/report/pdf", "GET"),
    ("/api/contracts/{id}/explanations", "GET"),
    ("/api/contracts/{id}/explanations/regenerate", "POST"),
    ("/api/contracts/{id}/classify", "POST"),
    ("/api/contracts/{id}/detect-risks", "POST"),
    ("/api/contracts/{id}/generate-explanations", "POST"),
])
@pytest.mark.asyncio
async def test_isolation_wrong_user_returns_404(route_template, method):
    """User B's token on User A's contract returns exactly 404."""
    try:
        user_a_id, user_b_id, contract_id = await setup_test_users_and_contract()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_b = get_token_for_user("userb@example.com", user_b_id)
            
            route = route_template.replace("{id}", str(contract_id))
            headers = {"Authorization": f"Bearer {token_b}"}
            
            if method == "GET":
                response = await client.get(route, headers=headers)
            else:
                response = await client.post(route, headers=headers)
            
            assert response.status_code == 404, f"{route} returned {response.status_code}, expected 404"
    finally:
        await cleanup_test_data()


@pytest.mark.parametrize("route_template,method", [
    ("/api/contracts/{id}/report", "GET"),
    ("/api/contracts/{id}/report/pdf", "GET"),
    ("/api/contracts/{id}/explanations", "GET"),
    ("/api/contracts/{id}/explanations/regenerate", "POST"),
    ("/api/contracts/{id}/classify", "POST"),
    ("/api/contracts/{id}/detect-risks", "POST"),
    ("/api/contracts/{id}/generate-explanations", "POST"),
])
@pytest.mark.asyncio
async def test_isolation_no_token_returns_401(route_template, method):
    """No token returns exactly 401."""
    try:
        user_a_id, user_b_id, contract_id = await setup_test_users_and_contract()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            route = route_template.replace("{id}", str(contract_id))
            
            if method == "GET":
                response = await client.get(route)
            else:
                response = await client.post(route)
            
            assert response.status_code == 401, f"{route} returned {response.status_code}, expected 401"
    finally:
        await cleanup_test_data()


@pytest.mark.parametrize("route_template,method", [
    ("/api/contracts/{id}/report", "GET"),
    ("/api/contracts/{id}/report/pdf", "GET"),
    ("/api/contracts/{id}/explanations", "GET"),
    ("/api/contracts/{id}/explanations/regenerate", "POST"),
    ("/api/contracts/{id}/classify", "POST"),
    ("/api/contracts/{id}/detect-risks", "POST"),
    ("/api/contracts/{id}/generate-explanations", "POST"),
])
@pytest.mark.asyncio
async def test_isolation_nonexistent_contract_returns_404(route_template, method):
    """Valid token on non-existent contract returns exactly 404."""
    try:
        user_a_id, user_b_id, contract_id = await setup_test_users_and_contract()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a = get_token_for_user("usera@example.com", user_a_id)
            
            route = route_template.replace("{id}", "999999999")
            headers = {"Authorization": f"Bearer {token_a}"}
            
            if method == "GET":
                response = await client.get(route, headers=headers)
            else:
                response = await client.post(route, headers=headers)
            
            assert response.status_code == 404, f"{route} returned {response.status_code}, expected 404"
    finally:
        await cleanup_test_data()


@pytest.mark.parametrize("route_template,method,patch_target", [
    ("/api/contracts/{id}/explanations/regenerate", "POST", "app.api.routes.explanations.generate_all_explanations"),
    ("/api/contracts/{id}/classify", "POST", "app.api.routes.pipeline.classify_all_clauses"),
    ("/api/contracts/{id}/detect-risks", "POST", "app.api.routes.pipeline.detect_risks"),
    ("/api/contracts/{id}/generate-explanations", "POST", "app.api.routes.pipeline.generate_all_explanations"),
])
@pytest.mark.asyncio
async def test_llm_routes_not_called_on_auth_failure(route_template, method, patch_target):
    """LLM functions not called when auth fails (user B accessing user A's contract)."""
    try:
        user_a_id, user_b_id, contract_id = await setup_test_users_and_contract()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_b = get_token_for_user("userb@example.com", user_b_id)
            
            route = route_template.replace("{id}", str(contract_id))
            headers = {"Authorization": f"Bearer {token_b}"}
            
            # Mock the LLM function to fail the test if called
            mock_fn = MagicMock(side_effect=Exception("LLM function should not be called on auth failure"))
            
            with patch(patch_target, mock_fn):
                response = await client.post(route, headers=headers)
                
                # Should return 404 without calling the LLM function
                assert response.status_code == 404
                mock_fn.assert_not_called()
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_happy_path_own_contract_not_blocked():
    """User A with valid token on own contract returns 200 or 409, not 401/404."""
    try:
        user_a_id, user_b_id, contract_id = await setup_test_users_and_contract()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token_a = get_token_for_user("usera@example.com", user_a_id)
            
            response = await client.get(
                f"/api/contracts/{contract_id}/report",
                headers={"Authorization": f"Bearer {token_a}"}
            )
            
            # Should not be auth errors
            assert response.status_code not in [401, 403, 404], \
                f"Got {response.status_code}, expected 200 or 409 (processing incomplete)"
            assert response.status_code in [200, 409], \
                f"Got {response.status_code}, expected 200 or 409"
    finally:
        await cleanup_test_data()
