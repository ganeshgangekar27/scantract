#!/usr/bin/env python3
"""Test JSON unwrapping parser against malformed LLM response."""
import json

# Exact malformed response captured earlier (double brace, no key)
test_input = """{ 
{
"This clause differs from standard practice because it lets the landlord change the lease terms on their own, without asking the tenant or giving notice."""

print("=" * 80)
print("TESTING MALFORMED JSON PARSER")
print("=" * 80)
print(f"\nInput ({len(test_input)} chars):")
print(repr(test_input))
print()

# Current parsing logic from generate_explanations.py (FIXED)
explanation = test_input.strip()

# Try to parse as JSON first
if explanation.startswith('{'):
    try:
        parsed = json.loads(explanation)
        if isinstance(parsed, dict) and 'explanation' in parsed:
            explanation = parsed['explanation']
        print("✓ SUCCESS: Extracted from JSON wrapper")
    except json.JSONDecodeError as e:
        print(f"✗ JSON PARSE FAILED: {e}")
        print("  Stripping malformed JSON artifacts...")
        # Strip leading braces and quotes that aren't part of prose
        import re
        explanation = re.sub(r'^[\{\s"]+', '', explanation)
        explanation = explanation.strip()

print(f"\n{'=' * 80}")
print(f"FINAL OUTPUT ({len(explanation)} chars):")
print(f"{'=' * 80}")
print(explanation)
print()

# Check if output is clean prose
if explanation.startswith('{'):
    print("⚠️  WARNING: Output still contains JSON artifacts!")
else:
    print("✓ Output is clean prose (no JSON artifacts)")
