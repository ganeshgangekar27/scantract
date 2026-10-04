#!/usr/bin/env python3
"""
Run parser on real fixture data - compact one-line-per-record output.
Takes an output path argument to save results.
"""
import json
import sys
from pathlib import Path

# Determine if running in container or host
if Path('/app').exists():
    # Running in container
    sys.path.insert(0, '/app')
    fixture_default = '/tmp/real_explanations.json'
else:
    # Running on host
    sys.path.insert(0, str(Path(__file__).parent.parent))
    fixture_default = str(Path(__file__).parent.parent / "tests" / "fixtures" / "real_explanations.json")

from app.llm.generate_explanations import parse_explanation, validate_explanation

if len(sys.argv) < 2:
    print("Usage: python run_parser_on_real.py <output_path> [fixture_path]")
    sys.exit(1)

output_path = Path(sys.argv[1])
fixture_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path(fixture_default)

with open(fixture_path, 'r') as f:
    data = json.load(f)

accepted = 0
rejected = 0
bad_chars_in_accepted = 0
lines = []

for item in data:
    contract_id = item['contract_id']
    finding_id = item['finding_id'][:8]
    stored = item['explanation']
    
    if stored is None:
        stored_len = "NULL"
        status = "REJECT"
        parsed_preview = "NULL"
        full_parsed = None
    else:
        stored_len = len(stored)
        parsed = parse_explanation(stored)
        if validate_explanation(parsed):
            status = "ACCEPT"
            accepted += 1
            parsed_preview = parsed[:50] if len(parsed) >= 50 else parsed
            full_parsed = parsed
            # Check for bad chars in FULL parsed text
            if '{' in parsed or '}' in parsed or '|||' in parsed:
                bad_chars_in_accepted += 1
        else:
            status = "REJECT"
            rejected += 1
            parsed_preview = parsed[:50] if parsed and len(parsed) >= 50 else (parsed if parsed else "")
            full_parsed = parsed
    
    line = f"{contract_id}|{finding_id}|{stored_len}|{status}|{parsed_preview}"
    lines.append(line)
    print(line)

# Write to output file
with open(output_path, 'w') as f:
    f.write('\n'.join(lines))
    f.write('\n')

print(f"accepted {accepted}, rejected {rejected}, bad chars in accepted: {bad_chars_in_accepted}")
