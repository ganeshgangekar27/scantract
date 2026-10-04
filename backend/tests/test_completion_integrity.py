"""
Test completion integrity - contracts fail if any explanation is missing/invalid.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.document_processing.orchestrator import _run_explanation_stage
from app.db.models import Contract, RiskFinding


@pytest.mark.asyncio
async def test_all_findings_get_valid_explanations_completes(monkeypatch):
    """All findings get valid explanations -> pipeline_stage 'explanations_generated'."""
    # Mock contract
    contract = Contract(id=1, pipeline_stage='risks_detected')
    
    # Mock findings without explanations
    finding1 = RiskFinding(id='f1', contract_id=1, explanation=None)
    finding2 = RiskFinding(id='f2', contract_id=1, explanation=None)
    
    # Mock DB session
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    
    # Mock generate_all_explanations to return count
    with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = 2  # 2 explanations generated
        
        await _run_explanation_stage(contract, db)
    
    # Should set stage to 'explanations_generated'
    assert contract.pipeline_stage == 'explanations_generated'
    assert db.commit.call_count >= 2  # At least start and end commit


@pytest.mark.asyncio
async def test_missing_explanations_fails_contract(monkeypatch):
    """Any finding without valid explanation -> 'failed', failed_stage 'generating_explanations'."""
    contract = Contract(id=1, pipeline_stage='risks_detected')
    
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    
    # Mock generate_all_explanations to raise error about missing explanations
    with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = RuntimeError("2 findings lack valid explanations")
        
        with pytest.raises(RuntimeError, match="2 findings lack valid explanations"):
            await _run_explanation_stage(contract, db)
    
    # Should set failed state
    assert contract.pipeline_stage == 'failed'
    assert contract.failed_stage == 'generating_explanations'
    assert "2 findings lack valid explanations" in contract.error_message


@pytest.mark.asyncio
async def test_zero_findings_completes(monkeypatch):
    """Zero findings -> 'explanations_generated' (nothing to do)."""
    contract = Contract(id=1, pipeline_stage='risks_detected')
    
    db = AsyncMock(spec=AsyncSession)
    db.commit = AsyncMock()
    
    # Mock generate_all_explanations to return 0 (no findings)
    with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = 0
        
        await _run_explanation_stage(contract, db)
    
    # Should still set stage to 'explanations_generated'
    assert contract.pipeline_stage == 'explanations_generated'


@pytest.mark.asyncio
async def test_invalid_stored_explanations_regenerated(monkeypatch):
    """Findings with STORED explanations that fail validate_explanation are regenerated."""
    from app.llm.generate_explanations import generate_all_explanations, validate_explanation
    
    # Mock findings: f1 has invalid stored explanation, f2 has valid, f3 has None
    finding1 = RiskFinding(id='f1', contract_id=1, explanation='{"": ""}')  # Invalid (empty)
    finding2 = RiskFinding(id='f2', contract_id=1, explanation='Valid explanation with enough characters to pass')
    finding3 = RiskFinding(id='f3', contract_id=1, explanation=None)
    
    # Mock DB session and query results
    db = AsyncMock(spec=AsyncSession)
    
    # First query: get ALL findings
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = [finding1, finding2, finding3]
    
    # Create an async mock for execute that returns different results per call
    call_count = 0
    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_result_all
        # Subsequent calls for other operations
        return MagicMock()
    
    db.execute = mock_execute
    db.commit = AsyncMock()
    
    # Mock generate_explanation to track which findings it's called for
    generated_for = []
    
    async def mock_generate_explanation(finding, db_session):
        generated_for.append(finding.id)
        return f"Generated explanation for {finding.id}"
    
    with patch('app.llm.generate_explanations.generate_explanation', new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = mock_generate_explanation
        
        # Run generate_all_explanations (updated version that validates stored)
        count = await generate_all_explanations(contract_id=1, db=db)
    
    # Should regenerate f1 (invalid) and f3 (None), but NOT f2 (valid)
    assert 'f1' in generated_for, "Should regenerate finding with invalid stored explanation"
    assert 'f3' in generated_for, "Should generate for finding with None"
    assert 'f2' not in generated_for, "Should NOT regenerate finding with valid stored explanation"
    assert count == 2  # 2 generated
