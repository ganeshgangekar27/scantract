"""
Tests for display_citation helper.
"""
import pytest
from app.llm.generate_explanations import display_citation


def test_returns_stored_value_when_non_empty():
    """If stored_formatted is non-empty, return it unchanged."""
    stored = "[Legal] Model Tenancy Act §7(1)"
    trigger = "Model Tenancy Act Section 7(1): Full long explanation text here"
    
    result = display_citation(stored, trigger)
    
    assert result == stored


def test_formats_short_legal_reference():
    """Short legal reference without colon."""
    stored = ""
    trigger = "Model Tenancy Act Section 7(1)"
    
    result = display_citation(stored, trigger)
    
    assert result == "[Legal] Model Tenancy Act §7(1)"


def test_extracts_label_before_colon_short():
    """Extract label before ': ' if ≤120 chars."""
    stored = ""
    trigger = "Model Tenancy Act Section 7(1): The security deposit shall not exceed an amount equivalent to two months' rent"
    
    result = display_citation(stored, trigger)
    
    assert result == "[Legal] Model Tenancy Act §7(1)"
    assert len(result) <= 120


def test_extracts_label_multiple_sections():
    """Multiple sections separated by semicolons."""
    stored = ""
    trigger = "Model Tenancy Act Section 13(1); Model Tenancy Act Section 15(2)"
    
    result = display_citation(stored, trigger)
    
    assert result == "[Legal] Model Tenancy Act §13(1); Model Tenancy Act §15(2)"


def test_extracts_label_before_colon_single_section():
    """Single section with explanation."""
    stored = ""
    trigger = "Model Tenancy Act Section 9(1)"
    
    result = display_citation(stored, trigger)
    
    assert result == "[Legal] Model Tenancy Act §9(1)"


def test_reference_example_with_bracket():
    """Reference corpus with bracket notation extracts template name."""
    stored = ""
    trigger = "[Reference Example: Tamil Nadu lease agreement template] Either party may terminate this agreement by giving 60 days' written notice to the other party."
    
    result = display_citation(stored, trigger)
    
    # Should extract the template name from inside the brackets
    assert result == "[Reference] Tamil Nadu lease agreement template"


def test_reference_example_without_bracket():
    """Reference corpus without bracket notation extracts template name."""
    stored = ""
    trigger = "Reference Example: Maharashtra standard lease (market rate): The monthly rent is INR 25,000, payable by the 5th of each month"
    
    result = display_citation(stored, trigger)
    
    # Should extract the label before the second ': '
    assert result == "[Reference] Maharashtra standard lease (market rate)"


def test_mixed_legal_and_reference():
    """Mixed legal and reference corpus citation."""
    stored = ""
    trigger = "Model Tenancy Act Section 13(1); Reference Example: Chennai house lease format"
    
    result = display_citation(stored, trigger)
    
    # Should format both parts properly
    assert result == "[Legal] Model Tenancy Act §13(1); [Reference] Chennai house lease format"


def test_bare_sentence_truncation():
    """Bare 300-character sentence with no colon."""
    stored = ""
    # Create a 300-char sentence
    trigger = "This is a very long reference sentence that does not contain any colon character and should be truncated to exactly one hundred and twenty characters followed by three dots to indicate that there is more content available but it exceeds the display limit for this particular use case" + "X" * 50
    
    result = display_citation(stored, trigger)
    
    assert result.endswith('...')
    assert len(result) == 123  # 120 + '...'


def test_empty_trigger():
    """Empty trigger returns empty string."""
    stored = ""
    trigger = ""
    
    result = display_citation(stored, trigger)
    
    assert result == ""


def test_stored_value_takes_precedence():
    """Stored non-empty value is returned unchanged regardless of trigger."""
    stored = "Custom Citation"
    trigger = "Model Tenancy Act Section 99(99): Some text"
    
    result = display_citation(stored, trigger)
    
    assert result == "Custom Citation"



def test_assemble_report_uses_display_citation():
    """Assemble_contract_report returns computed citation when stored is None."""
    from unittest.mock import AsyncMock, MagicMock
    from datetime import datetime
    import uuid
    from app.reports.assembler import assemble_contract_report
    from app.db.models import Contract, Clause, RiskFinding
    
    # Setup
    db = AsyncMock()
    
    contract = MagicMock(spec=Contract)
    contract.id = 1
    contract.filename = "test.pdf"
    contract.uploaded_at = datetime(2024, 1, 1)
    contract.pipeline_stage = "completed"
    
    # One clause
    clause = MagicMock(spec=Clause)
    clause.id = 1
    clause.clause_id = "1.1"
    clause.text = "Test clause text"
    clause.contract_id = 1
    
    # Two findings: one risky with stored citation, one missing without
    risky_finding = MagicMock(spec=RiskFinding)
    risky_finding.id = uuid.uuid4()
    risky_finding.contract_id = 1
    risky_finding.clause_id = 1
    risky_finding.finding_type = "risky_clause"
    risky_finding.severity = "high"
    risky_finding.reason = "Test reason"
    risky_finding.explanation = "Test explanation"
    risky_finding.formatted_citation = "Stored Citation"  # Has stored value
    risky_finding.triggering_rule_or_corpus = "Model Tenancy Act Section 7(1)"
    
    missing_finding = MagicMock(spec=RiskFinding)
    missing_finding.id = uuid.uuid4()
    missing_finding.contract_id = 1
    missing_finding.clause_id = None
    missing_finding.finding_type = "missing_clause"
    missing_finding.expected_clause_type = "Termination Notice"
    missing_finding.severity = "medium"
    missing_finding.reason = "Missing reason"
    missing_finding.explanation = "Missing explanation"
    missing_finding.formatted_citation = None  # No stored value
    missing_finding.triggering_rule_or_corpus = "Model Tenancy Act Section 9(1): The rent increase cannot exceed 8 percent annually"
    
    # Mock DB responses
    contract_result = MagicMock()
    contract_result.scalar_one_or_none.return_value = contract
    
    clause_result = MagicMock()
    clause_result.scalars.return_value.all.return_value = [clause]
    
    findings_result = MagicMock()
    findings_result.scalars.return_value.all.return_value = [risky_finding, missing_finding]
    
    db.execute.side_effect = [contract_result, clause_result, findings_result]
    
    # Execute
    import asyncio
    report = asyncio.run(assemble_contract_report(1, db))
    
    # Verify risky clause uses stored citation
    assert len(report.risky_clauses) == 1
    assert report.risky_clauses[0].formatted_citation == "Stored Citation"
    
    # Verify missing clause uses computed label (before ':')
    assert len(report.missing_clauses) == 1
    assert report.missing_clauses[0].formatted_citation == "[Legal] Model Tenancy Act §9(1)"
    assert ": " not in report.missing_clauses[0].formatted_citation
    assert len(report.missing_clauses[0].formatted_citation) <= 120



def test_invariant_no_unbalanced_brackets():
    """No result should have unbalanced brackets."""
    # Test with all real trigger prefixes from contracts 1 and 44
    triggers = [
        "Model Tenancy Act Section 7(1): The security deposit shall not exceed...",
        "Model Tenancy Act Section 13(1); Model Tenancy Act Section 15(2)",
        "Reference Example: Maharashtra standard lease (market rate): The monthly rent...",
        "[Reference Example: Tamil Nadu lease agreement template] Either party may terminate...",
        "Model Tenancy Act Section 13(1); Reference Example: Chennai house lease format",
        "This is a very long bare sentence with no colon that exceeds one hundred and twenty characters and should be truncated with three dots at the end to indicate more content" + "X" * 100,
        ""
    ]
    
    for trigger in triggers:
        result = display_citation("", trigger)
        open_count = result.count('[')
        close_count = result.count(']')
        assert open_count == close_count, f"Unbalanced brackets in result for trigger: {trigger[:60]}"
        
        if result:  # Non-empty results
            assert len(result) <= 123, f"Result too long ({len(result)} chars) for trigger: {trigger[:60]}"
