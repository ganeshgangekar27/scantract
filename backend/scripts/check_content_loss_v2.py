#!/usr/bin/env python3
"""Check if accepted parsed text is substring of stored text."""
import json
import logging
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.llm.generate_explanations import parse_explanation, validate_explanation

if len(sys.argv) < 2:
    print("Usage: python check_content_loss_v2.py <output_path>")
    sys.exit(1)

output_path = Path(sys.argv[1])
fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "real_explanations.json"

with open(fixture_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

not_substring_count = 0
lines = []

for item in data:
    contract_id = item['contract_id']
    finding_id = item['finding_id'][:8]
    stored = item['explanation']
    
    if stored is None:
        continue
    
    parsed = parse_explanation(stored)
    if not validate_explanation(parsed):
        continue
    
    # Strip leading wrappers from stored for comparison
    stored_stripped = stored.lstrip('{"}.:  ')
    
    is_substring = parsed in stored
    
    line = f"{contract_id}|{finding_id}|{is_substring}|{stored_stripped[:40]}|{parsed[:40]}"
    lines.append(line)
    
    if not is_substring:
        not_substring_count += 1
    
    # Save c4163c80 full text
    if finding_id == 'c4163c80':
        lines.append("\n=== FULL STORED TEXT FOR c4163c80 ===")
        lines.append(stored)
        lines.append("\n=== FULL PARSED TEXT FOR c4163c80 ===")
        lines.append(parsed)
        lines.append("")

lines.append(f"\nAccepted records that are NOT substrings: {not_substring_count}")

# Write to file
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

# Print summary
for line in lines:
    print(line)
