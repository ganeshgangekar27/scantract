#!/usr/bin/env python3
"""Check encoding impact on record 0e0e0cc4."""
import json
import logging
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.llm.generate_explanations import parse_explanation

fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "real_explanations.json"

# Read with platform default encoding
with open(fixture_path, 'r') as f:
    data_default = json.load(f)

# Read with explicit UTF-8
with open(fixture_path, 'r', encoding='utf-8') as f:
    data_utf8 = json.load(f)

# Find record 0e0e0cc4
target_default = None
target_utf8 = None

for item in data_default:
    if item['finding_id'].startswith('0e0e0cc4'):
        target_default = item
        break

for item in data_utf8:
    if item['finding_id'].startswith('0e0e0cc4'):
        target_utf8 = item
        break

if not target_default or not target_utf8:
    print("Record 0e0e0cc4 not found")
    sys.exit(1)

raw_default = target_default['explanation']
raw_utf8 = target_utf8['explanation']

# Count non-ASCII characters
def count_non_ascii(text):
    return sum(1 for c in text if ord(c) > 127)

print("=== WITH PLATFORM DEFAULT ENCODING ===")
print(f"len(raw): {len(raw_default)}")
print(f"non-ASCII count: {count_non_ascii(raw_default)}")
print(f"first 60: {repr(raw_default[:60])}")
print()

print("=== WITH encoding='utf-8' ===")
print(f"len(raw): {len(raw_utf8)}")
print(f"non-ASCII count: {count_non_ascii(raw_utf8)}")
print(f"first 60: {repr(raw_utf8[:60])}")
print()

if raw_default == raw_utf8:
    print("CONCLUSION: Both encodings produce identical results")
else:
    print("CONCLUSION: Encodings differ!")
    print(f"Length difference: {len(raw_utf8) - len(raw_default)}")
