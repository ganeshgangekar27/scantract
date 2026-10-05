#!/usr/bin/env python3
"""Show content loss for specific records."""
import json
import logging
import sys
from pathlib import Path

logging.disable(logging.CRITICAL)

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.llm.generate_explanations import parse_explanation

if len(sys.argv) < 2:
    print("Usage: python show_content_loss_v2.py <output_path>")
    sys.exit(1)

output_path = Path(sys.argv[1])
fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "real_explanations.json"

with open(fixture_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

target_ids = ['c4163c80', '9b3e0e73', '2ee57af6', 'a0a79187', 'afcae3b1']

lines = []

for target_id in target_ids:
    for item in data:
        if item['finding_id'].startswith(target_id):
            stored = item['explanation']
            parsed = parse_explanation(stored)
            
            lines.append(f"\n{'=' * 60}")
            lines.append(f"RECORD: {target_id}")
            lines.append(f"{'=' * 60}")
            lines.append(f"\nFULL STORED TEXT:")
            lines.append(stored)
            lines.append(f"\nFULL PARSED TEXT:")
            lines.append(parsed if parsed else "None")
            
            # Try parsing as JSON
            try:
                obj = json.loads(stored)
                lines.append(f"\njson.loads(stored) = {repr(obj)}")
            except Exception as e:
                lines.append(f"\njson.loads(stored) = INVALID JSON ({e})")
            
            # Analyze what was dropped
            lines.append(f"\nANALYSIS:")
            if parsed in stored:
                lines.append("  Parsed is substring of stored")
            else:
                lines.append("  Parsed is NOT substring of stored")
                
                # Check what was lost
                if stored.startswith('{'):
                    try:
                        obj = json.loads(stored)
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if isinstance(v, str) and parsed == v:
                                    lines.append(f"  Parser extracted VALUE, dropped KEY: {repr(k[:80])}")
                                    break
                                import re
                                k_stripped = re.sub(r'^["\.\s:]+', '', k).strip()
                                if parsed == k_stripped:
                                    lines.append(f"  Parser extracted KEY (stripped), dropped VALUE: {repr(v[:80])}")
                                    break
                    except:
                        pass
            
            break

# Write to file
with open(output_path, 'w', encoding='utf-8', newline='') as f:
    f.write('\n'.join(lines))

print(f"Written to {output_path}")
