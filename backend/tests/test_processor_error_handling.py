"""
Tests for processor error handling with friendly_error.
"""
import pytest
from sqlalchemy import text
from datetime import datetime

from app.document_processing.processor import process_contract
from tests.auth_utils import get_test_db


async def setup_test_contract_with_missing_file():
    """Create a test contract whose file_path does not exist."""
    async for db in get_test_db():
        # Clean up
        await db.execute(text("DELETE FROM contracts WHERE id >= 920000"))
        await db.execute(text("DELETE FROM users WHERE email = 'processor@test.local'"))
        await db.commit()
        
        # Create user
        await db.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, created_at, is_active)
            VALUES (920001, 'processor@test.local', '$2b$12$test', 'Processor Test User', :now, true)
        """), {"now": datetime.now()})
        
        # Create contract with nonexistent file path
        await db.execute(text("""
            INSERT INTO contracts (id, contract_type, filename, file_path, uploaded_at, processing_status, user_id, is_sample)
            VALUES (920010, 'rental', 'missing.pdf', '/nonexistent/path/missing.pdf', :now, 'uploaded', 920001, false)
        """), {"now": datetime.now()})
        
        await db.commit()
        break
    
    return 920010


async def cleanup_test_data():
    """Clean up test data."""
    async for db in get_test_db():
        await db.execute(text("DELETE FROM contracts WHERE id >= 920000"))
        await db.execute(text("DELETE FROM users WHERE email = 'processor@test.local'"))
        await db.commit()
        break


@pytest.mark.asyncio
async def test_process_contract_missing_file_friendly_error():
    """process_contract with missing file stores friendly error without server paths."""
    try:
        contract_id = await setup_test_contract_with_missing_file()
        
        # Call process_contract with the nonexistent file path
        await process_contract(contract_id, '/nonexistent/path/missing.pdf', None)
        
        # Check the stored error message
        async for db in get_test_db():
            result = await db.execute(text("SELECT processing_status, error_message FROM contracts WHERE id = :id"), {"id": contract_id})
            row = result.fetchone()
            
            assert row is not None
            status, error_msg = row
            
            # Must be failed
            assert status == 'failed'
            
            # Must have non-empty error message
            assert error_msg is not None
            assert len(error_msg) > 0
            
            # Must NOT contain server paths
            assert '/app/' not in error_msg
            assert '/nonexistent/path/missing.pdf' not in error_msg
            
            break
    finally:
        await cleanup_test_data()
