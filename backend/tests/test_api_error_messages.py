"""
Tests for API error messages in list and 409 responses.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.api.routes.contracts import list_contracts
from app.api.routes.reports import get_contract_report
from app.db.models import Contract
from fastapi import HTTPException
from tests.auth_utils import create_mock_user


@pytest.mark.asyncio
async def test_list_contracts_includes_error_message():
    """Contracts list includes error_message field."""
    db = AsyncMock()
    current_user = create_mock_user()
    
    # Mock contracts with and without errors
    contract1 = MagicMock(spec=Contract)
    contract1.id = 1
    contract1.filename = "test1.pdf"
    contract1.uploaded_at = datetime(2024, 1, 1)
    contract1.processing_status = "completed"
    contract1.pipeline_stage = "completed"
    contract1.failed_stage = None
    contract1.error_message = None
    contract1.user_id = current_user.id
    
    contract2 = MagicMock(spec=Contract)
    contract2.id = 2
    contract2.filename = "test2.pdf"
    contract2.uploaded_at = datetime(2024, 1, 2)
    contract2.processing_status = "failed"
    contract2.pipeline_stage = "failed"
    contract2.failed_stage = "classifying"
    contract2.error_message = "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."
    contract2.user_id = current_user.id
    
    # Mock DB response
    result = MagicMock()
    result.scalars.return_value.all.return_value = [contract1, contract2]
    db.execute.return_value = result
    
    # Call endpoint
    response = await list_contracts(db, current_user)
    
    # Verify response includes error_message
    assert len(response) == 2
    assert response[0].contract_id == 1
    assert response[0].error_message is None
    assert response[1].contract_id == 2
    assert response[1].error_message == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."


@pytest.mark.asyncio
async def test_report_409_includes_error_details():
    """Report 409 response includes failed_stage and error_message."""
    db = AsyncMock()
    current_user = create_mock_user()
    
    # Mock contract that's not completed
    contract = MagicMock(spec=Contract)
    contract.id = 3
    contract.pipeline_stage = "failed"
    contract.failed_stage = "detecting_risks"
    contract.error_message = "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."
    contract.user_id = current_user.id
    
    contract_result = MagicMock()
    contract_result.scalar_one_or_none.return_value = contract
    
    db.execute.return_value = contract_result
    
    # Call endpoint and expect 409
    with pytest.raises(HTTPException) as exc_info:
        await get_contract_report(3, db, current_user)
    
    # Verify 409 status
    assert exc_info.value.status_code == 409
    
    # Verify detail includes error info
    detail = exc_info.value.detail
    assert isinstance(detail, dict)
    assert "message" in detail
    assert detail["failed_stage"] == "detecting_risks"
    assert detail["error_message"] == "Daily AI request limit reached. Try again after the quota resets (about 5:30 AM IST)."
