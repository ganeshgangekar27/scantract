#!/usr/bin/env python3
"""Verify all accepted records conform to the substring or joined content invariant."""
import json
import logging
import sys
import re
from pathlib import Path

logging.disable(logging.CRITICAL)

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.llm.generate_explanations import parse_explanation, validate_explanation

fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "real_explanations.json"

with open(fixture_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

non_conforming = 0
c4163c80_parsed = None

for item in data:
    finding_id = item['finding_id'][:8]
    stored = item['explanation']
    
    if stored is None:
        continue
    
    parsed = parse_explanation(stored)
    if not validate_explanation(parsed):
        continue
    
    # Check c4163c80
    if finding_id == 'c4163c80':
        c4163c80_parsed = parsed
    
    # Check invariant
    is_substring = parsed in stored
    is_json_joined = False
    
    if not is_substring:
        try:
            obj = json.loads(stored)
            if isinstance(obj, dict):
                content_parts = []
                for k, v in obj.items():
                    if isinstance(k, str):
                        k_stripped = re.sub(r'^["\.\s:]+', '', k).strip()
                        if len(k_stripped) >= 20:
                            content_parts.append(k_stripped)
                    if isinstance(v, str) and v.strip():
                        content_parts.append(v.strip())
                
                joined = ' '.join(content_parts)
                if parsed == joined:
                    is_json_joined = True
        except:
            pass
    
    if not (is_substring or is_json_joined):
        non_conforming += 1
        print(f"NON-CONFORMING: {finding_id}")

print(f"\nNon-conforming accepted count: {non_conforming}")
print(f"\nFirst 80 chars of c4163c80 parsed:")
print(c4163c80_parsed[:80] if c4163c80_parsed else "NOT FOUND")
