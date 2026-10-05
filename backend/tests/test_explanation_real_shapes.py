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
    
    # Text-in-the-KEY shapes (from 1a561bc0, 2a712cfb, 6646bd1c)
    ('{". This clause differs from standard practice because": []}', "This clause differs from standard practice because", True),
    ('{": This text is in the key with colon prefix"}', "This text is in the key with colon prefix", True),
    ('{". Another text in key here": ""}', "Another text in key here", True),
    
    # Real c4163c80: key and value both content (20+ chars), should be joined
    ('{"This clause differs from standard practice because it ties the lease term.": "Indian rental law typically requires a defined lease duration."}', 
     "This clause differs from standard practice because it ties the lease term. Indian rental law typically requires a defined lease duration.", True),
    
    # Label key (short): only value extracted
    ('{"text": "This is the actual content we want"}', "This is the actual content we want", True),
    
    # Both key and value 20+ chars: joined with space
    ('{"First content part over twenty characters": "Second content part over twenty characters"}', 
     "First content part over twenty characters Second content part over twenty characters", True),
    
    # Key with leading punctuation, empty value list: key only
    ('{". Text in key that is long enough": []}', "Text in key that is long enough", True),
    
    # Newline inside wrapper
    ('{"First sentence.\\nSecond sentence of at least twenty characters."}', "First sentence.\\nSecond sentence of at least twenty characters.", True),
    
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
    with open(fixture_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    checked_count = 0
    found_141c2535 = False
    
    for item in data:
        if item['explanation'] is None:
            continue  # NULL explanations are fine
        
        checked_count += 1
        finding_id = item['finding_id']
        stored = item['explanation']
        
        # Check if this is the 141c2535 record (44666 chars, malformed)
        if finding_id.startswith('141c2535'):
            found_141c2535 = True
            parsed_141c = parse_explanation(stored)
            # This specific record should be REJECTED due to length > 2000
            assert not validate_explanation(parsed_141c), f"Record 141c2535 should be rejected but was accepted"
        
        parsed = parse_explanation(stored)
        if validate_explanation(parsed):
            # If accepted, must satisfy invariant
            assert 20 <= len(parsed) <= 2000, f"Length {len(parsed)} out of range"
            assert '{' not in parsed, f"Contains opening brace: {parsed[:60]}"
            assert '}' not in parsed, f"Contains closing brace: {parsed[:60]}"
            assert '|||' not in parsed, f"Contains triple pipes: {parsed[:60]}"
            assert not parsed.startswith('"'), f"Starts with quote: {parsed[:60]}"
            assert not parsed.startswith(':'), f"Starts with colon: {parsed[:60]}"
            assert not parsed.startswith('. '), f"Starts with '. ': {parsed[:60]}"
            
            # Substring invariant: parsed must be a contiguous substring of stored,
            # OR when stored is valid JSON, equal the single-space-joined content strings
            # (keys 20+ chars + all non-empty string values, order preserved, wrappers stripped, JSON escapes decoded)
            is_substring = parsed in stored
            
            # Try parsing as JSON to check joined content
            is_json_joined = False
            if not is_substring:
                try:
                    obj = json.loads(stored)
                    if isinstance(obj, dict):
                        # Collect content strings: keys >= 20 chars (after stripping) and all non-empty values
                        content_parts = []
                        for k, v in obj.items():
                            if isinstance(k, str):
                                import re
                                k_stripped = re.sub(r'^["\.\s:]+', '', k).strip()
                                if len(k_stripped) >= 20:
                                    content_parts.append(k_stripped)
                            if isinstance(v, str) and v.strip():
                                content_parts.append(v.strip())
                        
                        # Join with single space
                        joined = ' '.join(content_parts)
                        if parsed == joined:
                            is_json_joined = True
                except:
                    pass  # Not valid JSON, that's ok
            
            assert is_substring or is_json_joined, f"Parsed not substring or joined content for {finding_id}: stored={stored[:60]}, parsed={parsed[:60]}"
    
    # Assert we checked enough records
    assert checked_count >= 30, f"Expected at least 30 non-null records, got {checked_count}"
    assert found_141c2535, "Did not find the 141c2535 record in fixture"
