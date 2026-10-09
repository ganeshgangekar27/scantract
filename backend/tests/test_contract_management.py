"""
Tests for contract management endpoints: delete, retry, delete-my-data, upload cap, stats.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile

from app.main import app
from app.db.database import get_db
from tests.auth_utils import get_test_db

# Override get_db for all tests
app.dependency_overrides[get_db] = get_test_db


def get_token_for_user(email: str, user_id: int) -> str:
    """Generate JWT token for a test user."""
    from app.auth.jwt import create_access_token
    return create_access_token(user_id=user_id, email=email)


async def setup_users_and_contracts():
    """Create test users and contracts for testing."""
    async for db in get_test_db():
        # Clean up
        await db.execute(text("DELETE FROM risk_findings WHERE contract_id >= 910000"))
        await db.execute(text("DELETE FROM clauses WHERE contract_id >= 910000"))
        await db.execute(text("DELETE FROM contracts WHERE id >= 910000"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@contractmgmt.test'"))
        await db.commit()
        
        # Create users
        await db.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, created_at, is_active)
            VALUES 
                (910001, 'owner@contractmgmt.test', '$2b$12$test', 'Owner User', :now, true),
                (910002, 'other@contractmgmt.test', '$2b$12$test', 'Other User', :now, true)
        """), {"now": datetime.now()})
        
        # Create contracts with different states
        # Completed contract for owner
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, file_path, uploaded_at, processing_status, user_id, is_sample)
            VALUES (910010, 'rental', 'completed.pdf', '/tmp/completed.pdf', :now, 'completed', 910001, false)
        """), {"now": datetime.now()})
        
        # Processing contract for owner
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, file_path, uploaded_at, processing_status, pipeline_stage, user_id, is_sample)
            VALUES (910011, 'rental', 'processing.pdf', '/tmp/processing.pdf', :now, 'processing', 'classification', 910001, false)
        """), {"now": datetime.now()})
        
        # Failed contract for owner
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, file_path, uploaded_at, processing_status, failed_stage, error_message, user_id, is_sample)
            VALUES (910012, 'rental', 'failed.pdf', '/tmp/failed.pdf', :now, 'failed', 'extraction', 'Test error', 910001, false)
        """), {"now": datetime.now()})
        
        # Sample contract
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, file_path, uploaded_at, processing_status, user_id, is_sample)
            VALUES (910013, 'rental', 'sample.pdf', '/tmp/sample.pdf', :now, 'completed', NULL, true)
        """), {"now": datetime.now()})
        
        # Contract for other user
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, file_path, uploaded_at, processing_status, user_id, is_sample)
            VALUES (910014, 'rental', 'other_user.pdf', '/tmp/other.pdf', :now, 'completed', 910002, false)
        """), {"now": datetime.now()})
        
        # Add some clauses and findings to completed contract for cascade testing
        await db.execute(text("""
            INSERT INTO clauses (id, contract_id, clause_id, position, text)
            VALUES (910100, 910010, 1, 0, 'Test clause 1')
        """))
        
        await db.execute(text("""
            INSERT INTO risk_findings (id, contract_id, finding_type, clause_id, severity, reason, explanation, formatted_citation, triggering_rule_or_corpus)
            VALUES ('910100aa-0000-0000-0000-000000000001', 910010, 'risky_clause', 1, 'high', 'Test risk', 'Test explanation', 'Test citation', 'legal_rule')
        """))
        
        await db.commit()
        break
    
    return 910001, 910002


async def cleanup_test_data():
    """Clean up test data."""
    async for db in get_test_db():
        await db.execute(text("DELETE FROM risk_findings WHERE contract_id >= 910000"))
        await db.execute(text("DELETE FROM clauses WHERE contract_id >= 910000"))
        await db.execute(text("DELETE FROM contracts WHERE id >= 910000"))
        await db.execute(text("DELETE FROM users WHERE email LIKE '%@contractmgmt.test'"))
        await db.commit()
        break


# DELETE CONTRACT TESTS

@pytest.mark.asyncio
async def test_delete_contract_owner_success():
    """Owner can delete their own completed contract."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = get_token_for_user("owner@contractmgmt.test", owner_id)
            
            response = await client.delete(
                "/api/contracts/910010",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True
            
            # Verify contract no longer exists
            async for db in get_test_db():
                result = await db.execute(text("SELECT COUNT(*) FROM contracts WHERE id = 910010"))
                count = result.scalar()
                assert count == 0
                
                # Verify clauses and findings were cascade deleted
                result = await db.execute(text("SELECT COUNT(*) FROM clauses WHERE contract_id = 910010"))
                assert result.scalar() == 0
                result = await db.execute(text("SELECT COUNT(*) FROM risk_findings WHERE contract_id = 910010"))
                assert result.scalar() == 0
                break
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_delete_contract_other_user_returns_404():
    """Other user gets 404 when trying to delete someone else's contract."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = get_token_for_user("other@contractmgmt.test", other_id)
            
            response = await client.delete(
                "/api/contracts/910010",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 404
            
            # Verify contract still exists
            async for db in get_test_db():
                result = await db.execute(text("SELECT COUNT(*) FROM contracts WHERE id = 910010"))
                count = result.scalar()
                assert count == 1
                break
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_delete_sample_contract_returns_404():
    """Sample contracts cannot be deleted."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = get_token_for_user("owner@contractmgmt.test", owner_id)
            
            response = await client.delete(
                "/api/contracts/910013",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 404
            
            # Verify sample still exists
            async for db in get_test_db():
                result = await db.execute(text("SELECT COUNT(*) FROM contracts WHERE id = 910013"))
                count = result.scalar()
                assert count == 1
                break
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_delete_processing_contract_returns_409():
    """Cannot delete a contract that is currently processing."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = get_token_for_user("owner@contractmgmt.test", owner_id)
            
            response = await client.delete(
                "/api/contracts/910011",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 409
            assert "processing" in response.json()["detail"].lower()
    finally:
        await cleanup_test_data()


# RETRY CONTRACT TESTS

@pytest.mark.asyncio
async def test_retry_failed_contract_success():
    """Owner can retry a failed contract."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        # Mock the background processing
        with patch("app.api.routes.contracts.process_contract", new_callable=AsyncMock) as mock_process:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                token = get_token_for_user("owner@contractmgmt.test", owner_id)
                
                response = await client.post(
                    "/api/contracts/910012/retry",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                assert response.status_code == 202
                data = response.json()
                assert data["success"] is True
                assert data["data"]["contract_id"] == 910012
                
                # Verify processing was queued
                mock_process.assert_called_once()
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_retry_non_failed_contract_returns_409():
    """Cannot retry a contract that hasn't failed."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = get_token_for_user("owner@contractmgmt.test", owner_id)
            
            response = await client.post(
                "/api/contracts/910010/retry",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 409
            assert "failed" in response.json()["detail"].lower()
    finally:
        await cleanup_test_data()


# DELETE MY DATA TESTS

@pytest.mark.asyncio
async def test_delete_my_data_removes_all_contracts():
    """Delete my data removes all user's contracts and the user."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = get_token_for_user("owner@contractmgmt.test", owner_id)
            
            response = await client.delete(
                "/api/auth/me/data",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["deleted_contracts"] == 3  # completed, processing, failed
            
            # Verify user and contracts are deleted
            async for db in get_test_db():
                result = await db.execute(text("SELECT COUNT(*) FROM users WHERE id = 910001"))
                assert result.scalar() == 0
                
                result = await db.execute(text("SELECT COUNT(*) FROM contracts WHERE user_id = 910001"))
                assert result.scalar() == 0
                
                # Verify other user's contract still exists
                result = await db.execute(text("SELECT COUNT(*) FROM contracts WHERE user_id = 910002"))
                assert result.scalar() == 1
                break
            
            # Verify token is now invalid
            response2 = await client.get(
                "/api/contracts/list",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response2.status_code == 401
    finally:
        await cleanup_test_data()


# UPLOAD CAP TESTS

@pytest.mark.asyncio
async def test_upload_cap_allows_up_to_limit():
    """Can upload up to MAX_UPLOADS_PER_DAY contracts."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        # Clear the user's existing contracts so we start fresh
        async for db in get_test_db():
            await db.execute(text("DELETE FROM risk_findings WHERE contract_id >= 910000"))
            await db.execute(text("DELETE FROM clauses WHERE contract_id >= 910000"))
            await db.execute(text("DELETE FROM contracts WHERE user_id = 910001 AND id >= 910000"))
            await db.commit()
            break
        
        # Mock the process_contract to avoid actual processing
        with patch("app.api.routes.contracts.process_contract", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                token = get_token_for_user("owner@contractmgmt.test", owner_id)
                
                # Create a test PDF file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
                    f.write("Test PDF content")
                    temp_path = f.name
                
                try:
                    # Upload 3 files (should succeed, assuming MAX_UPLOADS_PER_DAY=3)
                    for i in range(3):
                        with open(temp_path, 'rb') as f:
                            response = await client.post(
                                "/api/contracts/upload",
                                headers={"Authorization": f"Bearer {token}"},
                                files={"file": (f"test{i}.pdf", f, "application/pdf")}
                            )
                        assert response.status_code == 200, f"Upload {i+1} failed"
                finally:
                    Path(temp_path).unlink(missing_ok=True)
    finally:
        await cleanup_test_data()


@pytest.mark.asyncio
async def test_upload_cap_returns_429_on_excess():
    """Returns 429 when exceeding MAX_UPLOADS_PER_DAY."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        # The user already has 3 contracts uploaded today in setup
        # Try to upload a 4th
        with patch("app.api.routes.contracts.process_contract", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                token = get_token_for_user("owner@contractmgmt.test", owner_id)
                
                with tempfile.NamedTemporaryFile(mode='w', suffix='.pdf', delete=False) as f:
                    f.write("Test PDF content")
                    temp_path = f.name
                
                try:
                    with open(temp_path, 'rb') as f:
                        response = await client.post(
                            "/api/contracts/upload",
                            headers={"Authorization": f"Bearer {token}"},
                            files={"file": ("test.pdf", f, "application/pdf")}
                        )
                    
                    assert response.status_code == 429
                    detail = response.json()["detail"]
                    assert "daily upload limit" in detail.lower()
                    assert "sample" in detail.lower()
                finally:
                    Path(temp_path).unlink(missing_ok=True)
    finally:
        await cleanup_test_data()


# STATS TESTS

@pytest.mark.asyncio
async def test_stats_excludes_samples():
    """Stats endpoint returns counts excluding samples."""
    try:
        owner_id, other_id = await setup_users_and_contracts()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = get_token_for_user("owner@contractmgmt.test", owner_id)
            
            response = await client.get(
                "/api/contracts/stats",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            stats = data["data"]
            
            # Owner has: 1 completed, 1 processing, 1 failed (sample not counted)
            assert stats["total"] == 3
            assert stats["completed"] == 1
            assert stats["processing"] == 1
            assert stats["failed"] == 1
    finally:
        await cleanup_test_data()
