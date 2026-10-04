"""
Test explanation parser against real malformed shapes from production data.
"""

import pytest
import sys

# Import REAL parser/validator functions
sys.path.insert(0, '/app')
from app.llm.generate_explanations import parse_explanation, validate_explanation


@pytest.mark.parametrize("stored,expected_clean,should_accept", [
    # Real fixture shapes
    ('{"": "This text should be cleaned"}', "This text should be cleaned", True),
    ('{". This text has weird key"}', "This text has weird key", True),
    ('{"text": "This has normal key but is now longer"}', "This has normal key but is now longer", True),
    ('{"key": "This has arbitrary key"}', "This has arbitrary key", True),
    ('}Leading brace text that is long enough to pass validation', "Leading brace text that is long enough to pass validation", True),
    
    # Edge cases
    ('{"": ""}', None, False),  # Empty value
    ('{}', None, False),  # Empty object
    ('{\n\n}', None, False),  # Just braces
    ('null', None, False),  # Null string
    ('{"": "x"}', None, False),  # Too short after cleaning
    
    # Triple pipes should be rejected
    ('{"": "Text with ||| pipes should be rejected"}', None, False),
    ('Normal text with ||| should also be rejected', None, False),
    
    # Over-long text (simulated)
    ('{"": "' + 'x' * 3000 + '"}', None, False),  # 3000 chars in JSON
    
    # Trailing JSON fragments
    ('{"": "Text with trailing quote"}', "Text with trailing quote", True),
    
    # Plain text (no JSON)
    ('This is plain text explanation that should pass through', 'This is plain text explanation that should pass through', True),
])
def test_explanation_parser_shapes(stored, expected_clean, should_accept):
    """Test parser handles all real and edge case shapes correctly."""
    parsed = parse_explanation(stored)
    accepted = validate_explanation(parsed)
    
    if should_accept:
        assert accepted, f"Should accept but didn't: {stored[:60]}"
        if expected_clean:
            assert parsed == expected_clean, f"Expected '{expected_clean}' but got '{parsed}'"
    else:
        assert not accepted, f"Should reject but didn't: {stored[:60]}"


import json
from pathlib import Path


def test_real_fixtures_invariant():
    """Test all real fixture explanations satisfy invariant."""
    # Locate fixture relative to this test file
    fixture_path = Path(__file__).parent / "fixtures" / "real_explanations.json"
    with open(fixture_path, 'r') as f:
        data = json.load(f)
    
    checked_count = 0
    found_141c2535 = False
    
    for item in data:
        if item['explanation'] is None:
            continue  # NULL explanations are fine
        
        checked_count += 1
        finding_id = item['finding_id']
        
        # Check if this is the 141c2535 record (44666 chars, malformed)
        if finding_id.startswith('141c2535'):
            found_141c2535 = True
            parsed_141c = parse_explanation(item['explanation'])
            # This specific record should be REJECTED due to length > 2000
            assert not validate_explanation(parsed_141c), f"Record 141c2535 should be rejected but was accepted"
        
        parsed = parse_explanation(item['explanation'])
        if validate_explanation(parsed):
            # If accepted, must satisfy invariant
            assert 20 <= len(parsed) <= 2000, f"Length {len(parsed)} out of range"
            assert '{' not in parsed, f"Contains opening brace: {parsed[:60]}"
            assert '}' not in parsed, f"Contains closing brace: {parsed[:60]}"
            assert '|||' not in parsed, f"Contains triple pipes: {parsed[:60]}"
            assert not parsed.startswith('"'), f"Starts with quote: {parsed[:60]}"
            assert not parsed.startswith(':'), f"Starts with colon: {parsed[:60]}"
            assert not parsed.startswith('. '), f"Starts with '. ': {parsed[:60]}"
    
    # Assert we checked enough records
    assert checked_count >= 30, f"Expected at least 30 non-null records, got {checked_count}"
    assert found_141c2535, "Did not find the 141c2535 record in fixture"
