#!/usr/bin/env python3
"""
Prove the invariant test is not vacuous by comparing identity vs real parser.
"""
import json
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.llm.generate_explanations import parse_explanation, validate_explanation

fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "real_explanations.json"

with open(fixture_path, 'r') as f:
    data = json.load(f)

def check_invariant(text):
    """Check if text violates invariant."""
    if text is None:
        return None
    if len(text) < 20 or len(text) > 2000:
        return "length"
    if '{' in text or '}' in text:
        return "braces"
    if '|||' in text:
        return "pipes"
    if text.startswith('"') or text.startswith(':') or text.startswith('. '):
        return "bad_start"
    return None  # No violation

# Test with identity parser
print("=== IDENTITY PARSER (lambda s: s) ===")
identity_checked = 0
identity_violations = 0

for item in data:
    if item['explanation'] is None:
        continue
    identity_checked += 1
    # Identity: no parsing, validate raw stored text
    violation = check_invariant(item['explanation'])
    if violation:
        identity_violations += 1

print(f"Records checked: {identity_checked}")
print(f"Violations: {identity_violations}")

# Test with real parser
print("\n=== REAL PARSER (parse_explanation + validate_explanation) ===")
real_checked = 0
real_violations = 0

for item in data:
    if item['explanation'] is None:
        continue
    real_checked += 1
    parsed = parse_explanation(item['explanation'])
    if validate_explanation(parsed):
        # Only check invariant on ACCEPTED results
        violation = check_invariant(parsed)
        if violation:
            real_violations += 1

print(f"Records checked: {real_checked}")
print(f"Violations: {real_violations}")
