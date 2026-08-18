"""
Unit tests for report assembly logic.

Tests the assemble_contract_report function with various scenarios.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from app.reports.assembler import assemble_contract_report
from app.reports.models import ContractReport
from app.db.models import Contract, Clause, RiskFinding


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_contract():
    """Mock contract with complete processing status."""
    contract = MagicMock(spec=Contract)
    contract.id = 1
    contract.filename = "lease_agreement.pdf"
    contract.upload_date = datetime(2024, 8, 15, 10, 30, 0)
    contract.processing_status = "complete"
    return contract


# ============================================================================
# TC-1: Complete Data Assembly
# ============================================================================

@pytest.mark.asyncio
async def test_complete_data_assembly(mock_db, mock_contract):
    """
    TC-1: Assemble report with complete data (10 clauses, 3 risky, 2 missing).
    
    Verifies:
    - All data assembled correctly
    - Counts match expected values
    - Clauses ordered properly
    """
    # Mock 10 clauses
    clauses = []
    for i in range(10):
        clause = MagicMock(spec=Clause)
        clause.id = i + 1
        clause.clause_id = f"{i + 1}.1"
        clause.text = f"Clause {i + 1} text"
        clause.contract_id = 1
        clauses.append(clause)
    
    # Mock 3 risky findings (high, medium, low severity)
    risky_findings = []
    severities = ["high", "medium", "low"]
    for i, severity in enumerate(severities):
        finding = MagicMock(spec=RiskFinding)
        finding.id = uuid.uuid4()
        finding.contract_id = 1
        finding.finding_type = "risky_clause"
        finding.clause_id = i + 1
        finding.severity = severity
        finding.reason = f"Risk {i + 1}"
        finding.explanation = f"Explanation for risk {i + 1}"
        finding.formatted_citation = f"[Legal] Citation {i + 1}"
        risky_findings.append(finding)
    
    # Mock 2 missing findings
    missing_findings = []
    for i in range(2):
        finding = MagicMock(spec=RiskFinding)
        finding.id = uuid.uuid4()
        finding.contract_id = 1
        finding.finding_type = "missing_clause"
        finding.clause_id = None
        finding.expected_clause_type = f"missing_type_{i + 1}"
        finding.severity = "medium"
        finding.reason = f"Missing {i + 1}"
        finding.explanation = f"Explanation for missing {i + 1}"
        finding.formatted_citation = f"[Reference] Citation {i + 3}"
        missing_findings.append(finding)
    
    all_findings = risky_findings + missing_findings
    
    # Mock database queries
    mock_result_contract = MagicMock()
    mock_result_contract.scalar_one_or_none.return_value = mock_contract
    
    mock_result_clauses = MagicMock()
    mock_result_clauses.scalars.return_value.all.return_value = clauses
    
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = all_findings
    
    mock_db.execute.side_effect = [
        mock_result_contract,  # Contract query
        mock_result_clauses,   # Clauses query
        mock_result_findings   # Findings query
    ]
    
    with patch('app.reports.assembler.generate_all_explanations') as mock_gen:
        mock_gen.return_value = 0  # All already cached
        
        report = await assemble_contract_report(1, mock_db)
        
        # Assert basic structure
        assert isinstance(report, ContractReport)
        assert report.contract_id == 1
        assert report.filename == "lease_agreement.pdf"
        
        # Assert counts
        assert len(report.all_clauses) == 10
        assert len(report.risky_clauses) == 3
        assert len(report.missing_clauses) == 2
        
        # Assert risk summary
        assert report.risk_summary.total_clauses == 10
        assert report.risk_summary.risky_clauses_count == 3
        assert report.risk_summary.missing_clauses_count == 2
        assert report.risk_summary.high_severity_count == 1
        assert report.risk_summary.medium_severity_count == 3  # 1 risky + 2 missing
        assert report.risk_summary.low_severity_count == 1
        
        # Assert risky clauses ordered by severity (high first)
        assert report.risky_clauses[0].severity == "high"
        assert report.risky_clauses[1].severity == "medium"
        assert report.risky_clauses[2].severity == "low"
        
        # Assert generate_all_explanations was called
        mock_gen.assert_called_once_with(1, mock_db)


# ============================================================================
# TC-2: Missing Explanations Handled Gracefully
# ============================================================================

@pytest.mark.asyncio
async def test_missing_explanations_handled(mock_db, mock_contract):
    """
    TC-2: Handle findings with missing explanations.
    
    Verifies:
    - generate_all_explanations is called
    - Report assembles successfully even if some explanations are None
    """
    # Mock 2 clauses
    clauses = []
    for i in range(2):
        clause = MagicMock(spec=Clause)
        clause.id = i + 1
        clause.clause_id = f"{i + 1}.1"
        clause.text = f"Clause {i + 1} text"
        clauses.append(clause)
    
    # Mock 1 finding with explanation=None
    finding = MagicMock(spec=RiskFinding)
    finding.id = uuid.uuid4()
    finding.contract_id = 1
    finding.finding_type = "risky_clause"
    finding.clause_id = 1
    finding.severity = "high"
    finding.reason = "Risk reason"
    finding.explanation = None  # Missing explanation
    finding.formatted_citation = "[Legal] Citation"
    
    # Mock database queries
    mock_result_contract = MagicMock()
    mock_result_contract.scalar_one_or_none.return_value = mock_contract
    
    mock_result_clauses = MagicMock()
    mock_result_clauses.scalars.return_value.all.return_value = clauses
    
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = [finding]
    
    mock_db.execute.side_effect = [
        mock_result_contract,
        mock_result_clauses,
        mock_result_findings
    ]
    
    with patch('app.reports.assembler.generate_all_explanations') as mock_gen:
        mock_gen.return_value = 1  # Generated 1 explanation
        
        report = await assemble_contract_report(1, mock_db)
        
        # Assert generate_all_explanations was called
        mock_gen.assert_called_once_with(1, mock_db)
        
        # Assert report assembled successfully
        assert len(report.risky_clauses) == 1
        # Should show pending message if still None after generation
        assert "Explanation pending" in report.risky_clauses[0].explanation or report.risky_clauses[0].explanation == ""


# ============================================================================
# TC-3: No Risks Found
# ============================================================================

@pytest.mark.asyncio
async def test_no_risks_found(mock_db, mock_contract):
    """
    TC-3: Contract with no risk findings.
    
    Verifies:
    - Empty risk/missing clause lists
    - Overall risk level is "none"
    - No legal references
    """
    # Mock 5 clauses
    clauses = []
    for i in range(5):
        clause = MagicMock(spec=Clause)
        clause.id = i + 1
        clause.clause_id = f"{i + 1}.1"
        clause.text = f"Clause {i + 1} text"
        clauses.append(clause)
    
    # No findings
    findings = []
    
    # Mock database queries
    mock_result_contract = MagicMock()
    mock_result_contract.scalar_one_or_none.return_value = mock_contract
    
    mock_result_clauses = MagicMock()
    mock_result_clauses.scalars.return_value.all.return_value = clauses
    
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = findings
    
    mock_db.execute.side_effect = [
        mock_result_contract,
        mock_result_clauses,
        mock_result_findings
    ]
    
    with patch('app.reports.assembler.generate_all_explanations') as mock_gen:
        mock_gen.return_value = 0
        
        report = await assemble_contract_report(1, mock_db)
        
        # Assert no risks
        assert len(report.risky_clauses) == 0
        assert len(report.missing_clauses) == 0
        assert report.risk_summary.overall_risk_level == "none"
        assert len(report.legal_references) == 0


# ============================================================================
# TC-4: Contract Not Found
# ============================================================================

@pytest.mark.asyncio
async def test_contract_not_found(mock_db):
    """
    TC-4: ValueError raised when contract not found.
    
    Verifies error handling for non-existent contract.
    """
    # Mock database returns None for contract
    mock_result_contract = MagicMock()
    mock_result_contract.scalar_one_or_none.return_value = None
    
    mock_db.execute.return_value = mock_result_contract
    
    with pytest.raises(ValueError, match="Contract not found"):
        await assemble_contract_report(999, mock_db)


# ============================================================================
# TC-5: Processing Incomplete
# ============================================================================

@pytest.mark.asyncio
async def test_processing_incomplete(mock_db):
    """
    TC-5: ValueError raised when contract processing incomplete.
    
    Verifies error handling for contracts still being processed.
    """
    # Mock contract with incomplete status
    contract = MagicMock(spec=Contract)
    contract.id = 1
    contract.processing_status = "processing"
    
    mock_result_contract = MagicMock()
    mock_result_contract.scalar_one_or_none.return_value = contract
    
    mock_db.execute.return_value = mock_result_contract
    
    with pytest.raises(ValueError, match="not complete"):
        await assemble_contract_report(1, mock_db)


# ============================================================================
# TC-6: Legal Reference Deduplication
# ============================================================================

@pytest.mark.asyncio
async def test_legal_reference_deduplication(mock_db, mock_contract):
    """
    TC-6: Legal references deduplicated with correct usage counts.
    
    Verifies:
    - Unique citations extracted
    - Usage counts correct
    - Ordered by usage_count desc, then alphabetically
    """
    # Mock 1 clause
    clause = MagicMock(spec=Clause)
    clause.id = 1
    clause.clause_id = "1.1"
    clause.text = "Clause text"
    
    # Mock 5 findings referencing 3 unique citations
    # Citation A: 2 uses, Citation B: 2 uses, Citation C: 1 use
    findings = []
    citations = [
        "[Legal] Citation A",
        "[Legal] Citation A",  # Duplicate
        "[Legal] Citation B",
        "[Legal] Citation B",  # Duplicate
        "[Reference] Citation C"
    ]
    
    for i, citation in enumerate(citations):
        finding = MagicMock(spec=RiskFinding)
        finding.id = uuid.uuid4()
        finding.contract_id = 1
        finding.finding_type = "risky_clause"
        finding.clause_id = 1
        finding.severity = "medium"
        finding.reason = f"Risk {i + 1}"
        finding.explanation = f"Explanation {i + 1}"
        finding.formatted_citation = citation
        findings.append(finding)
    
    # Mock database queries
    mock_result_contract = MagicMock()
    mock_result_contract.scalar_one_or_none.return_value = mock_contract
    
    mock_result_clauses = MagicMock()
    mock_result_clauses.scalars.return_value.all.return_value = [clause]
    
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = findings
    
    mock_db.execute.side_effect = [
        mock_result_contract,
        mock_result_clauses,
        mock_result_findings
    ]
    
    with patch('app.reports.assembler.generate_all_explanations') as mock_gen:
        mock_gen.return_value = 0
        
        report = await assemble_contract_report(1, mock_db)
        
        # Assert 3 unique citations
        assert len(report.legal_references) == 3
        
        # Extract citations and counts
        refs_dict = {ref.citation: ref.usage_count for ref in report.legal_references}
        
        # Assert usage counts
        assert refs_dict["[Legal] Citation A"] == 2
        assert refs_dict["[Legal] Citation B"] == 2
        assert refs_dict["[Reference] Citation C"] == 1
        
        # Assert ordering: by usage_count desc (2, 2, 1), then alphabetically
        # A and B both have count=2, so should be alphabetically ordered
        # C has count=1, so should be last
        assert report.legal_references[0].usage_count == 2
        assert report.legal_references[1].usage_count == 2
        assert report.legal_references[2].usage_count == 1
        assert report.legal_references[2].citation == "[Reference] Citation C"
