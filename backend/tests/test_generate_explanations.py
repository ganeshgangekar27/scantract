"""
Test suite for Stage 8 explanation generation and citation formatting.

Tests explanation generation, citation formatting (deterministic, no LLM),
forbidden language detection, batch operations, and API endpoints.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import uuid

from app.llm.generate_explanations import (
    generate_explanation,
    format_citation,
    generate_all_explanations,
    get_contract_explanations,
    _contains_forbidden_language,
    _is_legal_rule,
    _format_legal_citation,
    _format_corpus_citation,
)
from app.llm.models import ContractExplanationsResponse
from app.db.models import RiskFinding, Clause
from tests.mocks.mock_explanation_responses import (
    VALID_EXPLANATION_PLAIN_LANGUAGE,
    FORBIDDEN_LANGUAGE_EXPLANATION,
    VALID_EXPLANATION_AFTER_RETRY,
    LEGAL_RULE_CITATION_RAW,
    LEGAL_RULE_CITATION_FORMATTED,
    LEGAL_RULE_STATE_CITATION_RAW,
    LEGAL_RULE_STATE_CITATION_FORMATTED,
    CORPUS_CITATION_RAW,
    CORPUS_CITATION_FORMATTED,
    CITATION_TEST_CASES,
)


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
def mock_risky_finding():
    """Mock risky clause finding with INTEGER clause_id."""
    finding = MagicMock(spec=RiskFinding)
    finding.id = uuid.uuid4()
    finding.contract_id = 1  # INTEGER
    finding.finding_type = "risky_clause"
    finding.clause_id = 1  # INTEGER
    finding.reason = "Exceeds legal limit for security deposits"
    finding.severity = "high"
    finding.triggering_rule_or_corpus = LEGAL_RULE_CITATION_RAW
    finding.explanation = None
    finding.formatted_citation = None
    finding.created_at = datetime.utcnow()
    return finding


@pytest.fixture
def mock_missing_finding():
    """Mock missing clause finding."""
    finding = MagicMock(spec=RiskFinding)
    finding.id = uuid.uuid4()
    finding.contract_id = 1  # INTEGER
    finding.finding_type = "missing_clause"
    finding.clause_id = None
    finding.expected_clause_type = "maintenance_and_repairs"
    finding.reason = "Standard clause missing from agreement"
    finding.severity = "medium"
    finding.triggering_rule_or_corpus = CORPUS_CITATION_RAW
    finding.explanation = None
    finding.formatted_citation = None
    finding.created_at = datetime.utcnow()
    return finding


@pytest.fixture
def mock_clause():
    """Mock clause with INTEGER id."""
    clause = MagicMock(spec=Clause)
    clause.id = 1  # INTEGER
    clause.clause_id = "1.1"
    clause.text = "Security deposit shall be 4 months' rent."
    clause.contract_id = 1  # INTEGER
    return clause


# ============================================================================
# TC-1: Single Explanation Generation
# ============================================================================

@pytest.mark.asyncio
async def test_generate_single_explanation(mock_db, mock_risky_finding):
    """
    TC-1: Generate explanation for a single finding.
    
    Verifies:
    - Explanation is 2-4 sentences
    - No forbidden language
    - Cached in database
    """
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        # Mock LLM returns valid plain-language explanation
        mock_llm.return_value = (VALID_EXPLANATION_PLAIN_LANGUAGE, 150)
        
        explanation = await generate_explanation(mock_risky_finding, mock_db)
        
        # Assert explanation returned
        assert explanation == VALID_EXPLANATION_PLAIN_LANGUAGE
        
        # Assert LLM called once (no retry)
        assert mock_llm.call_count == 1
        
        # Assert no forbidden language
        assert not _contains_forbidden_language(explanation)
        
        # Assert cached in database
        mock_db.execute.assert_called()
        mock_db.commit.assert_called()
        
        # Validate explanation length (2-4 sentences)
        sentence_count = explanation.count('.') + explanation.count('!') + explanation.count('?')
        assert 2 <= sentence_count <= 4, f"Expected 2-4 sentences, got {sentence_count}"


# ============================================================================
# TC-2: Citation Formatting - Legal Rule
# ============================================================================

def test_format_citation_legal_rule():
    """
    TC-2: Format legal rule citation deterministically.
    
    Verifies:
    - "Section" replaced with "§"
    - "[Legal]" prefix added
    - NO LLM call made
    """
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        result = format_citation(LEGAL_RULE_CITATION_RAW)
        
        assert result == LEGAL_RULE_CITATION_FORMATTED
        
        # CRITICAL: No LLM call for citation formatting
        mock_llm.assert_not_called()


# ============================================================================
# TC-3: Citation Formatting - Legal Rule with State
# ============================================================================

def test_format_citation_legal_rule_with_state():
    """
    TC-3: Format legal rule citation with state qualifier.
    
    Verifies state-specific legal rules formatted correctly.
    """
    result = format_citation(LEGAL_RULE_STATE_CITATION_RAW)
    assert result == LEGAL_RULE_STATE_CITATION_FORMATTED


# ============================================================================
# TC-4: Citation Formatting - Reference Corpus
# ============================================================================

def test_format_citation_reference_corpus():
    """
    TC-4: Format reference corpus citation.
    
    Verifies:
    - "[Reference]" prefix added
    - Original text preserved
    """
    result = format_citation(CORPUS_CITATION_RAW)
    assert result == CORPUS_CITATION_FORMATTED


# ============================================================================
# TC-5: Citation Formatting - Multiple Formats
# ============================================================================

def test_format_citation_multiple_formats():
    """
    TC-5: Test various citation formats.
    
    Verifies all citation formats work without errors and no LLM calls.
    """
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        for raw, expected in CITATION_TEST_CASES:
            result = format_citation(raw)
            assert result == expected, f"Failed for: {raw}"
        
        # CRITICAL: No LLM calls for any citation
        mock_llm.assert_not_called()


# ============================================================================
# TC-6: Forbidden Language Detection - Present
# ============================================================================

@pytest.mark.asyncio
async def test_forbidden_language_detection_present(mock_db, mock_risky_finding):
    """
    TC-6: Detect forbidden language and trigger retry.
    
    Verifies:
    - Forbidden language detected
    - Retry triggered with emphasis
    - LLM called twice
    """
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        # First call returns forbidden language, second returns valid
        mock_llm.side_effect = [
            (FORBIDDEN_LANGUAGE_EXPLANATION, 100),
            (VALID_EXPLANATION_AFTER_RETRY, 120)
        ]
        
        explanation = await generate_explanation(mock_risky_finding, mock_db)
        
        # Assert retry occurred (LLM called twice)
        assert mock_llm.call_count == 2
        
        # Assert final explanation has no forbidden language
        assert not _contains_forbidden_language(explanation)
        assert explanation == VALID_EXPLANATION_AFTER_RETRY


# ============================================================================
# TC-7: Forbidden Language Detection - Absent
# ============================================================================

@pytest.mark.asyncio
async def test_forbidden_language_detection_absent(mock_db, mock_risky_finding):
    """
    TC-7: No retry when forbidden language absent.
    
    Verifies:
    - No forbidden language detected
    - LLM called once (no retry)
    """
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        mock_llm.return_value = (VALID_EXPLANATION_PLAIN_LANGUAGE, 150)
        
        explanation = await generate_explanation(mock_risky_finding, mock_db)
        
        # Assert no retry (LLM called once)
        assert mock_llm.call_count == 1
        
        # Assert no forbidden language
        assert not _contains_forbidden_language(explanation)


# ============================================================================
# TC-8: Batch Generation - All New
# ============================================================================

@pytest.mark.asyncio
async def test_batch_generation_all_new(mock_db):
    """
    TC-8: Generate explanations for all findings (none cached).
    
    Verifies:
    - 5 explanations generated
    - All cached in database
    """
    # Create 5 findings without explanations
    findings = []
    for i in range(5):
        finding = MagicMock(spec=RiskFinding)
        finding.id = uuid.uuid4()
        finding.contract_id = 1
        finding.finding_type = "risky_clause"
        finding.clause_id = i + 1
        finding.reason = f"Risk {i+1}"
        finding.severity = "medium"
        finding.triggering_rule_or_corpus = LEGAL_RULE_CITATION_RAW
        finding.explanation = None
        findings.append(finding)
    
    # Mock database query - CORRECT PATTERN
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = findings
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        mock_llm.return_value = (VALID_EXPLANATION_PLAIN_LANGUAGE, 150)
        
        count = await generate_all_explanations(1, mock_db)
        
        # Assert 5 explanations generated
        assert count == 5
        
        # Assert LLM called 5 times
        assert mock_llm.call_count == 5


# ============================================================================
# TC-9: Batch Generation - Partial Cached
# ============================================================================

@pytest.mark.asyncio
async def test_batch_generation_partial_cached(mock_db):
    """
    TC-9: Generate only missing explanations (3 cached, 2 new).
    
    Verifies:
    - Only 2 new explanations generated
    - Existing 3 unchanged
    """
    # Create 2 findings without explanations
    findings = []
    for i in range(2):
        finding = MagicMock(spec=RiskFinding)
        finding.id = uuid.uuid4()
        finding.contract_id = 1
        finding.finding_type = "risky_clause"
        finding.clause_id = i + 4  # IDs 4, 5
        finding.reason = f"Risk {i+4}"
        finding.severity = "medium"
        finding.triggering_rule_or_corpus = LEGAL_RULE_CITATION_RAW
        finding.explanation = None
        findings.append(finding)
    
    # Mock database query (only returns findings without explanations) - CORRECT PATTERN
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = findings
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        mock_llm.return_value = (VALID_EXPLANATION_PLAIN_LANGUAGE, 150)
        
        count = await generate_all_explanations(1, mock_db)
        
        # Assert only 2 new explanations generated
        assert count == 2
        
        # Assert LLM called only 2 times
        assert mock_llm.call_count == 2


# ============================================================================
# TC-10: Batch Generation - All Cached
# ============================================================================

@pytest.mark.asyncio
async def test_batch_generation_all_cached(mock_db):
    """
    TC-10: No generation when all explanations cached.
    
    Verifies:
    - Returns 0
    - No LLM calls made
    """
    # Mock database query returns empty (all have explanations) - CORRECT PATTERN
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        count = await generate_all_explanations(1, mock_db)
        
        # Assert no new generations
        assert count == 0
        
        # Assert no LLM calls
        mock_llm.assert_not_called()


# ============================================================================
# TC-11: API Endpoint - First Request
# ============================================================================

@pytest.mark.asyncio
async def test_api_endpoint_first_request(mock_db, mock_risky_finding, mock_clause):
    """
    TC-11: First request generates explanations on-the-fly.
    
    Verifies:
    - Explanations generated
    - Response includes all findings
    - Summary counts correct
    """
    # Finding without explanation
    mock_risky_finding.explanation = None
    
    # Mock database queries - CORRECT PATTERN
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = []
    
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = [mock_risky_finding]
    
    mock_result_update = MagicMock()  # For UPDATE citation
    
    mock_result_clause = MagicMock()
    mock_result_clause.scalar_one_or_none.return_value = mock_clause
    
    mock_db.execute.side_effect = [
        mock_result_findings,  # For generate_all_explanations
        mock_result_all,  # For get_contract_explanations SELECT
        mock_result_update,  # For UPDATE formatted_citation
        mock_result_clause  # For _fetch_clause
    ]
    
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        mock_llm.return_value = (VALID_EXPLANATION_PLAIN_LANGUAGE, 150)
        
        # Update finding to have explanation after generation
        mock_risky_finding.explanation = VALID_EXPLANATION_PLAIN_LANGUAGE
        
        response = await get_contract_explanations(1, mock_db, auto_generate=True)
        
        # Assert response structure
        assert isinstance(response, ContractExplanationsResponse)
        assert response.contract_id == 1
        assert len(response.risky_clauses) == 1
        assert response.summary["total_risks"] == 1


# ============================================================================
# TC-12: API Endpoint - Cached Request
# ============================================================================

@pytest.mark.asyncio
async def test_api_endpoint_cached_request(mock_db, mock_risky_finding, mock_clause):
    """
    TC-12: Cached request returns without LLM calls.
    
    Verifies:
    - No LLM calls
    - Response includes cached explanations
    """
    # Finding with cached explanation
    mock_risky_finding.explanation = VALID_EXPLANATION_PLAIN_LANGUAGE
    mock_risky_finding.formatted_citation = LEGAL_RULE_CITATION_FORMATTED
    
    # Mock database queries - CORRECT PATTERN
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = []
    
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = [mock_risky_finding]
    
    mock_result_clause = MagicMock()
    mock_result_clause.scalar_one_or_none.return_value = mock_clause
    
    mock_db.execute.side_effect = [
        mock_result_findings,
        mock_result_all,
        mock_result_clause
    ]
    
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        response = await get_contract_explanations(1, mock_db, auto_generate=True)
        
        # Assert no LLM calls (all cached)
        mock_llm.assert_not_called()
        
        # Assert response contains cached data
        assert response.risky_clauses[0].explanation == VALID_EXPLANATION_PLAIN_LANGUAGE


# ============================================================================
# TC-13: API Endpoint - No Auto-Generate
# ============================================================================

@pytest.mark.asyncio
async def test_api_endpoint_no_auto_generate(mock_db, mock_risky_finding, mock_clause):
    """
    TC-13: No generation when auto_generate=False.
    
    Verifies:
    - Returns "Explanation pending..." for missing
    - No LLM calls
    """
    # Finding without explanation
    mock_risky_finding.explanation = None
    
    # Mock database queries - CORRECT PATTERN
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = [mock_risky_finding]
    
    mock_result_update = MagicMock()  # For UPDATE citation
    
    mock_result_clause = MagicMock()
    mock_result_clause.scalar_one_or_none.return_value = mock_clause
    
    mock_db.execute.side_effect = [
        mock_result_all,  # For get_contract_explanations SELECT
        mock_result_update,  # For UPDATE formatted_citation
        mock_result_clause  # For _fetch_clause
    ]
    
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        response = await get_contract_explanations(1, mock_db, auto_generate=False)
        
        # Assert no LLM calls
        mock_llm.assert_not_called()
        
        # Assert pending message
        assert response.risky_clauses[0].explanation == "Explanation pending..."


# ============================================================================
# TC-14: Citation Traceability
# ============================================================================

@pytest.mark.asyncio
async def test_citation_traceability(mock_db, mock_risky_finding, mock_clause):
    """
    TC-14: Every citation traces to triggering_rule_or_corpus.
    
    Verifies:
    - formatted_citation based on triggering_rule_or_corpus
    - No orphan citations
    """
    mock_risky_finding.explanation = VALID_EXPLANATION_PLAIN_LANGUAGE
    
    # Mock database queries - CORRECT PATTERN
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = []
    
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = [mock_risky_finding]
    
    mock_result_update = MagicMock()  # For UPDATE citation
    
    mock_result_clause = MagicMock()
    mock_result_clause.scalar_one_or_none.return_value = mock_clause
    
    mock_db.execute.side_effect = [
        mock_result_findings,
        mock_result_all,
        mock_result_update,  # For UPDATE formatted_citation
        mock_result_clause
    ]
    
    response = await get_contract_explanations(1, mock_db, auto_generate=True)
    
    # Assert citation traces to source
    finding = response.risky_clauses[0]
    assert finding.formatted_citation == format_citation(mock_risky_finding.triggering_rule_or_corpus)


# ============================================================================
# TC-15: Regenerate Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_regenerate_endpoint(mock_db):
    """
    TC-15: Regenerate clears cache and generates new.
    
    Verifies:
    - Cached explanations cleared
    - New explanations generated
    - Count returned correctly
    """
    from app.api.routes.explanations import regenerate_explanations
    
    # Mock findings without explanations after clearing
    findings = [MagicMock(spec=RiskFinding) for _ in range(3)]
    for i, finding in enumerate(findings):
        finding.id = uuid.uuid4()
        finding.contract_id = 1
        finding.finding_type = "risky_clause"
        finding.clause_id = i + 1
        finding.reason = f"Risk {i+1}"
        finding.severity = "medium"
        finding.triggering_rule_or_corpus = LEGAL_RULE_CITATION_RAW
        finding.explanation = None
    
    # CORRECT PATTERN
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = findings
    mock_db.execute = AsyncMock(return_value=mock_result)
    
    with patch('app.llm.generate_explanations.call_llm') as mock_llm:
        mock_llm.return_value = (VALID_EXPLANATION_PLAIN_LANGUAGE, 150)
        
        result = await regenerate_explanations(1, mock_db)
        
        # Assert success response
        assert result["success"] is True
        assert result["data"]["regenerated_count"] == 3


# ============================================================================
# TC-16: Risky Clause with Clause Details
# ============================================================================

@pytest.mark.asyncio
async def test_risky_clause_with_clause_details(mock_db, mock_risky_finding, mock_clause):
    """
    TC-16: Risky clause response includes clause details.
    
    Verifies:
    - clause_text included
    - clause_number included
    - Clause fetched from database (clause_id is INTEGER)
    """
    mock_risky_finding.explanation = VALID_EXPLANATION_PLAIN_LANGUAGE
    
    # Mock database queries - CORRECT PATTERN
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = []
    
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = [mock_risky_finding]
    
    mock_result_update = MagicMock()  # For UPDATE citation
    
    mock_result_clause = MagicMock()
    mock_result_clause.scalar_one_or_none.return_value = mock_clause
    
    mock_db.execute.side_effect = [
        mock_result_findings,
        mock_result_all,
        mock_result_update,  # For UPDATE formatted_citation
        mock_result_clause
    ]
    
    response = await get_contract_explanations(1, mock_db, auto_generate=True)
    
    # Assert clause details included
    risky = response.risky_clauses[0]
    assert risky.clause_id == 1  # INTEGER
    assert risky.clause_text == mock_clause.text
    assert risky.clause_number == mock_clause.clause_id


# ============================================================================
# TC-17: Missing Clause Details
# ============================================================================

@pytest.mark.asyncio
async def test_missing_clause_details(mock_db, mock_missing_finding):
    """
    TC-17: Missing clause response includes expected_clause_type.
    
    Verifies:
    - expected_clause_type included
    - clause_id is None
    """
    mock_missing_finding.explanation = "Missing clause explanation"
    
    # Mock database queries - CORRECT PATTERN
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = []
    
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = [mock_missing_finding]
    
    mock_result_update = MagicMock()  # For UPDATE citation
    
    mock_db.execute.side_effect = [
        mock_result_findings,
        mock_result_all,
        mock_result_update  # For UPDATE formatted_citation
    ]
    
    response = await get_contract_explanations(1, mock_db, auto_generate=True)
    
    # Assert missing clause details
    missing = response.missing_clauses[0]
    assert missing.expected_clause_type == "maintenance_and_repairs"
    assert missing.clause_id is None


# ============================================================================
# TC-18: Severity Ordering
# ============================================================================

@pytest.mark.asyncio
async def test_severity_ordering(mock_db, mock_clause):
    """
    TC-18: Findings ordered by severity (high first).
    
    Verifies:
    - Response ordered by severity
    - Summary counts correct
    """
    # Create findings with mixed severity
    findings = []
    severities = ["low", "high", "medium", "high", "low"]
    for i, sev in enumerate(severities):
        finding = MagicMock(spec=RiskFinding)
        finding.id = uuid.uuid4()
        finding.contract_id = 1
        finding.finding_type = "risky_clause"
        finding.clause_id = i + 1
        finding.reason = f"Risk {i+1}"
        finding.severity = sev
        finding.triggering_rule_or_corpus = LEGAL_RULE_CITATION_RAW
        finding.explanation = VALID_EXPLANATION_PLAIN_LANGUAGE
        finding.created_at = datetime.utcnow()
        finding.formatted_citation = None
        findings.append(finding)
    
    # Mock database queries - CORRECT PATTERN
    mock_result_findings = MagicMock()
    mock_result_findings.scalars.return_value.all.return_value = []
    
    # Findings already sorted by severity in query (ORDER BY severity DESC)
    sorted_findings = sorted(findings, key=lambda f: {"high": 3, "medium": 2, "low": 1}[f.severity], reverse=True)
    
    mock_result_all = MagicMock()
    mock_result_all.scalars.return_value.all.return_value = sorted_findings
    
    # Mock UPDATE and clause fetches - need 5 UPDATEs + 5 clause fetches
    mock_result_update = MagicMock()
    mock_result_clause = MagicMock()
    mock_result_clause.scalar_one_or_none.return_value = mock_clause
    
    # Build side_effect list: generate_all_explanations, get all findings, then 5x (UPDATE + fetch clause)
    execute_returns = [mock_result_findings, mock_result_all]
    for _ in range(5):
        execute_returns.append(mock_result_update)  # UPDATE citation
        execute_returns.append(mock_result_clause)   # fetch clause
    
    mock_db.execute.side_effect = execute_returns
    
    response = await get_contract_explanations(1, mock_db, auto_generate=True)
    
    # Assert severity counts
    assert response.summary["high_severity"] == 2
    assert response.summary["medium_severity"] == 1
    assert response.summary["low_severity"] == 2
    
    # Assert ordering (first should be high severity)
    assert response.risky_clauses[0].severity == "high"
