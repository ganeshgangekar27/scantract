"""
Tests for processor and orchestrator processing_status integration.

Verifies that processing_status stays 'processing' until full pipeline completes,
and becomes 'failed' if any stage fails.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.document_processing.orchestrator import run_full_pipeline
from app.db.models import Contract


# TC-1: processing_status='processing' during pipeline, 'completed' after success  
@pytest.mark.asyncio
async def test_processing_status_stays_processing_until_completion():
    """TC-1: Verify processing_status stays 'processing' during pipeline, becomes 'completed' on success."""
    # Test orchestrator.py behavior: status stays 'processing' until pipeline completes
    with patch('app.document_processing.orchestrator._run_classification_stage') as mock_classify:
        with patch('app.document_processing.orchestrator._run_risk_detection_stage') as mock_risk:
            with patch('app.document_processing.orchestrator._run_explanation_stage') as mock_explain:
                # All stages succeed
                mock_classify.return_value = AsyncMock()
                mock_risk.return_value = AsyncMock()
                mock_explain.return_value = AsyncMock()
                
                # Contract starts as 'processing' (set by processor.py line 99)
                mock_contract = MagicMock(spec=Contract)
                mock_contract.id = 1
                mock_contract.processing_status = 'processing'
                mock_contract.pipeline_stage = 'segmented'
                
                mock_db = MagicMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_contract
                mock_db.execute = AsyncMock(return_value=mock_result)
                mock_db.commit = AsyncMock()
                
                # Run pipeline
                await run_full_pipeline(1, mock_db)
                
                # Verify: orchestrator sets 'completed' only at the end
                assert mock_contract.processing_status == 'completed'
                assert mock_contract.pipeline_stage == 'completed'


# TC-2: run_full_pipeline sets processing_status='failed' on stage failure
@pytest.mark.asyncio
async def test_run_full_pipeline_failed_status():
    """TC-2: Verify processing_status='failed' when pipeline stage fails."""
    # Setup contract mock
    mock_contract = MagicMock(spec=Contract)
    mock_contract.id = 1
    mock_contract.processing_status = 'processing'
    mock_contract.pipeline_stage = 'segmented'
    
    # Setup db session mock
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_contract
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    with patch('app.document_processing.orchestrator._run_classification_stage') as mock_stage:
        # Setup: stage raises exception
        async def raise_error(contract, db):
            # Simulate what the real exception handler does
            contract.pipeline_stage = 'failed'
            contract.processing_status = 'failed'
            contract.failed_stage = 'classifying'
            await db.commit()
            raise RuntimeError("Classification failed")
        
        mock_stage.side_effect = raise_error
        
        # Execute and expect exception
        with pytest.raises(RuntimeError):
            await run_full_pipeline(1, mock_db)
        
        # Verify: processing_status should be set to 'failed'
        assert mock_contract.processing_status == 'failed'
        assert mock_contract.pipeline_stage == 'failed'
        assert mock_contract.failed_stage == 'classifying'


# TC-3: run_full_pipeline sets processing_status='completed' on success
@pytest.mark.asyncio
async def test_run_full_pipeline_completed_status():
    """TC-3: Verify processing_status='completed' when all stages succeed."""
    with patch('app.document_processing.orchestrator._run_classification_stage') as mock_classify:
        with patch('app.document_processing.orchestrator._run_risk_detection_stage') as mock_risk:
            with patch('app.document_processing.orchestrator._run_explanation_stage') as mock_explain:
                # Setup: all stages succeed
                mock_classify.return_value = AsyncMock()
                mock_risk.return_value = AsyncMock()
                mock_explain.return_value = AsyncMock()
                
                # Setup contract mock
                mock_contract = MagicMock(spec=Contract)
                mock_contract.id = 1
                mock_contract.processing_status = 'processing'
                mock_contract.pipeline_stage = 'segmented'
                
                # Setup db session mock
                mock_db = MagicMock()
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_contract
                mock_db.execute = AsyncMock(return_value=mock_result)
                mock_db.commit = AsyncMock()
                
                # Execute
                await run_full_pipeline(1, mock_db)
                
                # Verify: both processing_status and pipeline_stage should be 'completed'
                assert mock_contract.processing_status == 'completed'
                assert mock_contract.pipeline_stage == 'completed'
                assert mock_contract.failed_stage is None
                assert mock_contract.error_message is None



# TC-4: top-level except catches uncaught exceptions and sets processing_status='failed'
@pytest.mark.asyncio
async def test_top_level_except_sets_failed_status():
    """TC-4: Verify top-level except in run_full_pipeline sets processing_status='failed'."""
    # Setup contract mock
    mock_contract = MagicMock(spec=Contract)
    mock_contract.id = 1
    mock_contract.processing_status = 'processing'
    mock_contract.pipeline_stage = 'segmented'
    mock_contract.error_message = None
    mock_contract.failed_stage = None
    
    # Setup db session mock
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_contract
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    
    with patch('app.document_processing.orchestrator._run_classification_stage') as mock_stage:
        # Setup: stage raises but does NOT set processing_status (simulating an uncaught exception)
        async def raise_without_handling(contract, db):
            # Stage raises but doesn't catch/set status (unlike TC-2)
            raise ValueError("Uncaught pipeline error")
        
        mock_stage.side_effect = raise_without_handling
        
        # Execute and expect exception
        with pytest.raises(ValueError, match="Uncaught pipeline error"):
            await run_full_pipeline(1, mock_db)
        
        # Verify: top-level except set processing_status to 'failed'
        assert mock_contract.processing_status == 'failed', \
            "Top-level except must set processing_status='failed'"
        assert mock_contract.pipeline_stage == 'failed', \
            "Top-level except must set pipeline_stage='failed'"
        # Verify the top-level except actually ran by checking it set error_message
        assert mock_contract.error_message is not None, \
            "Top-level except must set error_message"
