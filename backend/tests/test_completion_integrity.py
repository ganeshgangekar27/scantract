"""
Test completion integrity - contracts fail if any explanation is missing/invalid.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.document_processing.orchestrator import _run_explanation_stage
from app.db.models import Contract, RiskFinding
from app.db.database import get_db


# Real orchestrator tests with actual DB (scantract_test)

@pytest.mark.asyncio
async def test_all_valid_explanations_completes():
    """All findings have valid explanations -> pipeline_stage 'explanations_generated'."""
    from datetime import datetime, timezone
    async for db in get_db():
        # Create contract and findings in test DB
        contract = Contract(id=9001, pipeline_stage='risks_detected', processing_status='processing',
                           contract_type='rental', filename='test.pdf', uploaded_at=datetime.now(timezone.utc))
        db.add(contract)
        
        finding1 = RiskFinding(id='test-f1', contract_id=9001, 
                              explanation='Valid explanation with enough characters to pass validation')
        finding2 = RiskFinding(id='test-f2', contract_id=9001,
                              explanation='Another valid explanation with sufficient length for testing')
        db.add_all([finding1, finding2])
        await db.commit()
        
        # Mock generate_all_explanations to skip LLM calls
        with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = 0  # No new explanations needed (already valid)
            
            await _run_explanation_stage(contract, db)
        
        # Should complete successfully
        assert contract.pipeline_stage == 'explanations_generated'
        
        # Cleanup
        await db.delete(finding1)
        await db.delete(finding2)
        await db.delete(contract)
        await db.commit()
        break


@pytest.mark.asyncio
async def test_one_null_explanation_fails():
    """One finding with NULL explanation -> 'failed', failed_stage 'generating_explanations', message contains '1'."""
    from datetime import datetime, timezone
    async for db in get_db():
        contract = Contract(id=9002, pipeline_stage='risks_detected', processing_status='processing',
                           contract_type='rental', filename='test.pdf', uploaded_at=datetime.now(timezone.utc))
        db.add(contract)
        
        finding1 = RiskFinding(id='test-f3', contract_id=9002, explanation=None)  # NULL
        finding2 = RiskFinding(id='test-f4', contract_id=9002,
                              explanation='Valid explanation with enough characters')
        db.add_all([finding1, finding2])
        await db.commit()
        
        # Mock generate_all_explanations to not fix the NULL
        with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = 0
            
            with pytest.raises(RuntimeError, match="Explanations missing or invalid"):
                await _run_explanation_stage(contract, db)
        
        # Should be in failed state
        assert contract.pipeline_stage == 'failed'
        assert contract.failed_stage == 'generating_explanations'
        assert '1' in contract.error_message
        assert 'missing or invalid' in contract.error_message.lower()
        
        # Cleanup
        await db.delete(finding1)
        await db.delete(finding2)
        await db.delete(contract)
        await db.commit()
        break


@pytest.mark.asyncio
async def test_invalid_stored_explanation_fails():
    """One finding with stored '{"": ""}' (invalid) -> 'failed'."""
    from datetime import datetime, timezone
    async for db in get_db():
        contract = Contract(id=9003, pipeline_stage='risks_detected', processing_status='processing',
                           contract_type='rental', filename='test.pdf', uploaded_at=datetime.now(timezone.utc))
        db.add(contract)
        
        finding1 = RiskFinding(id='test-f5', contract_id=9003, explanation='{"": ""}')  # Invalid (empty)
        finding2 = RiskFinding(id='test-f6', contract_id=9003,
                              explanation='Valid explanation with enough characters')
        db.add_all([finding1, finding2])
        await db.commit()
        
        # Mock generate_all_explanations to not fix the invalid one
        with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = 0
            
            with pytest.raises(RuntimeError, match="Explanations missing or invalid"):
                await _run_explanation_stage(contract, db)
        
        # Should be in failed state
        assert contract.pipeline_stage == 'failed'
        assert contract.failed_stage == 'generating_explanations'
        assert '1' in contract.error_message
        
        # Cleanup
        await db.delete(finding1)
        await db.delete(finding2)
        await db.delete(contract)
        await db.commit()
        break


@pytest.mark.asyncio
async def test_zero_findings_completes():
    """Zero findings -> 'explanations_generated' (nothing to validate)."""
    from datetime import datetime, timezone
    async for db in get_db():
        contract = Contract(id=9004, pipeline_stage='risks_detected', processing_status='processing',
                           contract_type='rental', filename='test.pdf', uploaded_at=datetime.now(timezone.utc))
        db.add(contract)
        await db.commit()
        
        # No findings added
        
        # Mock generate_all_explanations
        with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = 0
            
            await _run_explanation_stage(contract, db)
        
        # Should complete successfully
        assert contract.pipeline_stage == 'explanations_generated'
        
        # Cleanup
        await db.delete(contract)
        await db.commit()
        break
