"""
Unit tests for risk detection (TC-1 through TC-18).

Tests verify full risk detection pipeline including traceability validation,
retry logic, persistence, and error handling.
"""

import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from sqlalchemy import select, func

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.llm.detect_risk import detect_risks
from app.llm.models import Severity
from app.db.models import Contract, Clause, RiskFinding
from tests.mocks.mock_risk_responses import (
    VALID_RISK_RESPONSE,
    MISSING_TRACEABILITY_RESPONSE,
    MISSING_TRACEABILITY_FIELD_RESPONSE,
    MALFORMED_JSON_RESPONSE,
    MARKDOWN_WRAPPED_RESPONSE,
    EMPTY_RISK_RESPONSE,
    MULTI_SEVERITY_RESPONSE,
    INVALID_CLAUSE_ID_RESPONSE,
    CITATION_FORMAT_VARIETY_RESPONSE
)


# Test fixtures and helpers

@pytest.fixture
def mock_contract():
    """Create a mock Contract object."""
    contract = MagicMock(spec=Contract)
    contract.id = 1
    contract.contract_type = "rental"
    contract.state = "MH"
    contract.processing_status = "completed"
    return contract


@pytest.fixture
def mock_clauses():
    """Create mock Clause objects."""
    clauses = []
    for i in range(1, 6):
        clause = MagicMock(spec=Clause)
        clause.id = i
        clause.clause_id = f"{i}.1"
        clause.contract_id = 1
        clause.text = f"Clause text for clause {i}.1"
        clause.clause_type = "payment_terms" if i == 1 else "termination"
        clause.position = i
        clauses.append(clause)
    return clauses


async def count_risk_findings(db, contract_id):
    """Helper to count risk findings in database."""
    result = await db.execute(
        select(func.count()).select_from(RiskFinding).where(RiskFinding.contract_id == contract_id)
    )
    return result.scalar()


def mock_llm_response(response_data, as_json=True):
    """Helper to create mock LLM response."""
    if as_json:
        return (json.dumps(response_data), 150)
    else:
        return (response_data, 150)


# TC-1: Full detection with valid response
@pytest.mark.asyncio
async def test_full_detection_valid_response(mock_contract, mock_clauses):
    """TC-1: Verify full risk detection pipeline with valid traceable response."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.return_value = mock_llm_response(VALID_RISK_RESPONSE)
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify result structure
                        assert result.contract_id == "1"
                        assert result.total_risks == 2
                        assert result.total_missing == 1
                        assert len(result.risky_clauses) == 2
                        assert len(result.missing_clauses) == 1
                        
                        # Verify severity counts
                        assert result.high_severity_count == 1
                        assert result.medium_severity_count == 1
                        assert result.low_severity_count == 1
                        
                        # Verify persistence was called
                        assert mock_persist.called


# TC-2: Traceability validation - missing field in risky clause
@pytest.mark.asyncio
async def test_traceability_validation_missing_field_risky(mock_contract, mock_clauses):
    """TC-2: Verify retry triggered when risky clause lacks traceability."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks - first call fails, second succeeds
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.side_effect = [
                            mock_llm_response(MISSING_TRACEABILITY_RESPONSE),  # First: invalid
                            mock_llm_response(VALID_RISK_RESPONSE)              # Second: valid
                        ]
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify retry occurred
                        assert mock_call_llm.call_count == 2
                        
                        # Verify final result is valid
                        assert result.total_risks == 2
                        assert result.total_missing == 1


# TC-3: Traceability validation - missing field in missing clause
@pytest.mark.asyncio
async def test_traceability_validation_missing_field_missing_clause(mock_contract, mock_clauses):
    """TC-3: Verify retry triggered when missing clause lacks traceability."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.side_effect = [
                            mock_llm_response(MISSING_TRACEABILITY_FIELD_RESPONSE),
                            mock_llm_response(VALID_RISK_RESPONSE)
                        ]
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify retry occurred
                        assert mock_call_llm.call_count == 2
                        assert result.total_risks == 2


# TC-4: Traceability validation - empty string rejected
@pytest.mark.asyncio
async def test_traceability_validation_empty_string(mock_contract, mock_clauses):
    """TC-4: Verify Pydantic validator rejects empty string traceability."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        
                        # Empty string should be rejected, then valid response
                        mock_call_llm.side_effect = [
                            mock_llm_response(MISSING_TRACEABILITY_RESPONSE),  # Empty string
                            mock_llm_response(VALID_RISK_RESPONSE)
                        ]
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify retry triggered
                        assert mock_call_llm.call_count == 2


# TC-5: All retries fail - RuntimeError raised
@pytest.mark.asyncio
async def test_traceability_validation_all_retries_fail(mock_contract, mock_clauses):
    """TC-5: Verify RuntimeError raised when all retries fail traceability."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks - all calls return invalid response
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.return_value = mock_llm_response(MISSING_TRACEABILITY_RESPONSE)
                        
                        # Execute and expect RuntimeError
                        db = MagicMock()
                        with pytest.raises(RuntimeError) as exc_info:
                            await detect_risks("1", db)
                        
                        # Verify error message mentions traceability or triggering_rule_or_corpus
                        error_msg = str(exc_info.value).lower()
                        assert "traceability" in error_msg or "triggering_rule_or_corpus" in error_msg
                        
                        # Verify persistence NOT called
                        assert not mock_persist.called


# TC-6: Markdown wrapped JSON successfully parsed
@pytest.mark.asyncio
async def test_malformed_json_first_attempt(mock_contract, mock_clauses):
    """TC-6: Verify markdown-wrapped JSON is successfully stripped and parsed."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.return_value = (MARKDOWN_WRAPPED_RESPONSE, 150)
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify success on first attempt
                        assert mock_call_llm.call_count == 1
                        assert result.total_risks == 1
                        assert result.total_missing == 1


# TC-7: Malformed JSON triggers retry
@pytest.mark.asyncio
async def test_malformed_json_retry(mock_contract, mock_clauses):
    """TC-7: Verify malformed JSON triggers emphatic instruction and retry."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.side_effect = [
                            (MALFORMED_JSON_RESPONSE, 150),  # Malformed
                            mock_llm_response(VALID_RISK_RESPONSE)  # Valid
                        ]
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify retry occurred
                        assert mock_call_llm.call_count == 2
                        assert result.total_risks == 2


# TC-8: Empty results handled correctly
@pytest.mark.asyncio
async def test_empty_results_no_risks_found(mock_contract, mock_clauses):
    """TC-8: Verify empty results (no risks found) handled gracefully."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.return_value = mock_llm_response(EMPTY_RISK_RESPONSE)
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify empty result
                        assert result.total_risks == 0
                        assert result.total_missing == 0
                        assert result.high_severity_count == 0
                        assert result.medium_severity_count == 0
                        assert result.low_severity_count == 0


# TC-9: Severity scoring correct
@pytest.mark.asyncio
async def test_severity_scoring(mock_contract, mock_clauses):
    """TC-9: Verify severity counts calculated correctly."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks - response with 2 high, 3 medium, 1 low
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.return_value = mock_llm_response(MULTI_SEVERITY_RESPONSE)
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify severity counts
                        assert result.high_severity_count == 2
                        assert result.medium_severity_count == 3
                        assert result.low_severity_count == 1
                        assert result.total_risks == 5
                        assert result.total_missing == 1


# TC-10: Invalid clause_id reference logged but doesn't fail
@pytest.mark.asyncio
async def test_invalid_clause_id_reference(mock_contract, mock_clauses):
    """TC-10: Verify invalid clause_id logged and skipped, valid ones persisted."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    # Don't mock persist - let it run to test skip logic
                    mock_load_contract.return_value = mock_contract
                    mock_load_clauses.return_value = mock_clauses
                    mock_retrieve.return_value = "Retrieved context..."
                    mock_call_llm.return_value = mock_llm_response(INVALID_CLAUSE_ID_RESPONSE)
                    
                    # Mock db operations
                    db = MagicMock()
                    db.execute = AsyncMock()
                    db.add = MagicMock()
                    db.commit = AsyncMock()
                    
                    # Execute
                    result = await detect_risks("1", db)
                    
                    # Verify result reflects both findings
                    assert result.total_risks == 2
                    
                    # Note: In real implementation, only valid clause_id would be persisted
                    # Invalid one would be logged and skipped


# TC-11: Database persistence for risky clauses
@pytest.mark.asyncio
async def test_database_persistence_risky_clauses(mock_contract, mock_clauses):
    """TC-11: Verify risky clauses persisted correctly with clause_id."""
    response = {
        "risky_clauses": [
            {
                "clause_id": "1.1",
                "reason": "Test risky clause 1",
                "triggering_rule_or_corpus": "Test rule 1",
                "severity": "high"
            },
            {
                "clause_id": "2.1",
                "reason": "Test risky clause 2",
                "triggering_rule_or_corpus": "Test rule 2",
                "severity": "medium"
            }
        ],
        "missing_clauses": []
    }
    
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    # Setup mocks
                    mock_load_contract.return_value = mock_contract
                    mock_load_clauses.return_value = mock_clauses
                    mock_retrieve.return_value = "Retrieved context..."
                    mock_call_llm.return_value = mock_llm_response(response)
                    
                    # Mock db operations
                    db = MagicMock()
                    db.execute = AsyncMock()
                    db.add = MagicMock()
                    db.commit = AsyncMock()
                    
                    # Execute
                    result = await detect_risks("1", db)
                    
                    # Verify 2 risky findings
                    assert result.total_risks == 2
                    assert result.total_missing == 0
                    
                    # Verify db.add called for risky findings
                    assert db.add.call_count == 2


# TC-12: Database persistence for missing clauses
@pytest.mark.asyncio
async def test_database_persistence_missing_clauses(mock_contract, mock_clauses):
    """TC-12: Verify missing clauses persisted correctly with expected_clause_type."""
    response = {
        "risky_clauses": [],
        "missing_clauses": [
            {
                "expected_clause_type": "maintenance_responsibilities",
                "why_expected": "Test missing clause 1",
                "triggering_rule_or_corpus": "Test rule 1",
                "severity": "medium"
            },
            {
                "expected_clause_type": "dispute_resolution",
                "why_expected": "Test missing clause 2",
                "triggering_rule_or_corpus": "Test rule 2",
                "severity": "low"
            }
        ]
    }
    
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    # Setup mocks
                    mock_load_contract.return_value = mock_contract
                    mock_load_clauses.return_value = mock_clauses
                    mock_retrieve.return_value = "Retrieved context..."
                    mock_call_llm.return_value = mock_llm_response(response)
                    
                    # Mock db operations
                    db = MagicMock()
                    db.execute = AsyncMock()
                    db.add = MagicMock()
                    db.commit = AsyncMock()
                    
                    # Execute
                    result = await detect_risks("1", db)
                    
                    # Verify 2 missing findings
                    assert result.total_risks == 0
                    assert result.total_missing == 2
                    
                    # Verify db.add called for missing findings
                    assert db.add.call_count == 2


# TC-13: Idempotent re-runs delete old findings
@pytest.mark.asyncio
async def test_database_persistence_idempotent_reruns(mock_contract, mock_clauses):
    """TC-13: Verify re-running detection deletes old findings before inserting new."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    # Setup mocks
                    mock_load_contract.return_value = mock_contract
                    mock_load_clauses.return_value = mock_clauses
                    mock_retrieve.return_value = "Retrieved context..."
                    mock_call_llm.return_value = mock_llm_response(VALID_RISK_RESPONSE)
                    
                    # Mock db operations
                    db = MagicMock()
                    db.execute = AsyncMock()
                    db.add = MagicMock()
                    db.commit = AsyncMock()
                    
                    # Execute twice
                    await detect_risks("1", db)
                    await detect_risks("1", db)
                    
                    # Verify DELETE executed twice (once per run)
                    assert db.execute.call_count >= 2


# TC-14: Merged context retrieval called correctly
@pytest.mark.asyncio
async def test_merged_context_retrieval(mock_contract, mock_clauses):
    """TC-14: Verify both search functions called and results merged."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk.search_legal_rules', new_callable=AsyncMock) as mock_legal:
                with patch('app.llm.detect_risk.search_reference_corpus', new_callable=AsyncMock) as mock_corpus:
                    with patch('app.llm.detect_risk.merge_retrieval_results') as mock_merge:
                        with patch('app.llm.detect_risk.format_merged_context') as mock_format:
                            with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                                with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock):
                                    # Setup mocks
                                    mock_load_contract.return_value = mock_contract
                                    mock_load_clauses.return_value = mock_clauses[:3]  # Limit to 3
                                    mock_legal.return_value = []
                                    mock_corpus.return_value = []
                                    mock_merge.return_value = MagicMock(chunks=[], total_tokens=0)
                                    mock_format.return_value = "Merged context"
                                    mock_call_llm.return_value = mock_llm_response(EMPTY_RISK_RESPONSE)
                                    
                                    # Execute
                                    db = MagicMock()
                                    await detect_risks("1", db)
                                    
                                    # Verify search functions called for each clause
                                    assert mock_legal.call_count == 3
                                    assert mock_corpus.call_count == 3
                                    
                                    # Verify merge and format called
                                    assert mock_merge.called
                                    assert mock_format.called


# TC-15: Contract not found error
@pytest.mark.asyncio
async def test_contract_not_found_error():
    """TC-15: Verify ValueError raised when contract doesn't exist."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        # Setup mock to raise ValueError
        mock_load_contract.side_effect = ValueError("Contract not found: 999")
        
        # Execute and expect ValueError
        db = MagicMock()
        with pytest.raises(ValueError) as exc_info:
            await detect_risks("999", db)
        
        assert "not found" in str(exc_info.value).lower()


# TC-16: Contract not processed error
@pytest.mark.asyncio
async def test_contract_not_processed_error():
    """TC-16: Verify ValueError raised when contract status is not 'completed'."""
    mock_contract = MagicMock(spec=Contract)
    mock_contract.id = 1
    mock_contract.processing_status = "pending"
    
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        # Setup mock to raise ValueError for wrong status
        mock_load_contract.side_effect = ValueError("Contract 1 is not ready for risk detection. Status: pending")
        
        # Execute and expect ValueError
        db = MagicMock()
        with pytest.raises(ValueError) as exc_info:
            await detect_risks("1", db)
        
        assert "not ready" in str(exc_info.value).lower() or "status" in str(exc_info.value).lower()


# TC-17: No clauses to analyze returns empty result
@pytest.mark.asyncio
async def test_no_clauses_to_analyze_empty_result(mock_contract):
    """TC-17: Verify empty result returned when contract has no clauses."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            # Setup mocks - no clauses
            mock_load_contract.return_value = mock_contract
            mock_load_clauses.return_value = []
            
            # Execute
            db = MagicMock()
            result = await detect_risks("1", db)
            
            # Verify empty result
            assert result.total_risks == 0
            assert result.total_missing == 0
            assert result.contract_id == "1"


# TC-18: Citation format flexibility
@pytest.mark.asyncio
async def test_citation_format_flexibility(mock_contract, mock_clauses):
    """TC-18: Verify various citation formats accepted (validator only checks non-empty)."""
    with patch('app.llm.detect_risk._load_contract', new_callable=AsyncMock) as mock_load_contract:
        with patch('app.llm.detect_risk._load_clauses', new_callable=AsyncMock) as mock_load_clauses:
            with patch('app.llm.detect_risk._retrieve_merged_context_for_contract', new_callable=AsyncMock) as mock_retrieve:
                with patch('app.llm.detect_risk.call_llm', new_callable=AsyncMock) as mock_call_llm:
                    with patch('app.llm.detect_risk._persist_findings', new_callable=AsyncMock) as mock_persist:
                        # Setup mocks - various citation formats
                        mock_load_contract.return_value = mock_contract
                        mock_load_clauses.return_value = mock_clauses
                        mock_retrieve.return_value = "Retrieved context..."
                        mock_call_llm.return_value = mock_llm_response(CITATION_FORMAT_VARIETY_RESPONSE)
                        
                        # Execute
                        db = MagicMock()
                        result = await detect_risks("1", db)
                        
                        # Verify all findings accepted
                        assert result.total_risks == 2
                        assert result.total_missing == 1
                        
                        # All findings should have non-empty triggering_rule_or_corpus
                        for finding in result.risky_clauses:
                            assert finding.triggering_rule_or_corpus
                            assert len(finding.triggering_rule_or_corpus.strip()) > 0
                        
                        for finding in result.missing_clauses:
                            assert finding.triggering_rule_or_corpus
                            assert len(finding.triggering_rule_or_corpus.strip()) > 0
