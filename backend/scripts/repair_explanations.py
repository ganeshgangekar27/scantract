"""
Repair stored explanations by running parse_explanation on existing values.

Scope: contracts 3, 42, 43, 44, 45 only (never contract 1).
Actions: KEEP (parsed == stored), CLEAN (parsed != stored), NULLIFY (parse/validate fails), SKIP_NULL (already NULL).
"""
import asyncio
import argparse
import sys
import logging
from pathlib import Path

logging.disable(logging.CRITICAL)

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.db.models import Contract, RiskFinding
from app.llm.generate_explanations import parse_explanation, validate_explanation


ALLOWED_CONTRACTS = [3, 42, 43, 44, 45]


def log_and_write(msg: str, outfile=None):
    """Print message and optionally write to file."""
    print(msg)
    if outfile:
        outfile.write(msg + '\n')
        outfile.flush()


async def repair_explanations(apply: bool, out_path: str = None):
    """
    Repair explanations for allowed contracts.
    
    Args:
        apply: If True, write changes to DB. If False, dry-run only.
        out_path: Optional file path to write output.
    """
    assert 1 not in ALLOWED_CONTRACTS, "Contract 1 must never be in allow-list"
    
    outfile = None
    if out_path:
        outfile = open(out_path, 'w', encoding='utf-8')
    
    try:
        async for db in get_db():
            try:
                # Process each allowed contract
                for contract_id in ALLOWED_CONTRACTS:
                    # Get contract
                    result = await db.execute(
                        select(Contract).where(Contract.id == contract_id)
                    )
                    contract = result.scalar_one_or_none()
                    
                    if not contract:
                        log_and_write(f"Contract {contract_id}: NOT FOUND", outfile)
                        continue
                    
                    # Get findings
                    result = await db.execute(
                        select(RiskFinding).where(RiskFinding.contract_id == contract_id).order_by(RiskFinding.id)
                    )
                    findings = result.scalars().all()
                    
                    log_and_write(f"\n=== Contract {contract_id} ===", outfile)
                    
                    counts = {'KEEP': 0, 'CLEAN': 0, 'NULLIFY': 0, 'SKIP_NULL': 0}
                    null_after_repair = 0
                    
                    for finding in findings:
                        old_text = finding.explanation
                        finding_id_short = str(finding.id)[:8]
                        
                        if old_text is None:
                            action = 'SKIP_NULL'
                            new_text = None
                            null_after_repair += 1
                        else:
                            try:
                                parsed = parse_explanation(old_text)
                                
                                if parsed and validate_explanation(parsed):
                                    # Valid explanation
                                    if parsed == old_text:
                                        action = 'KEEP'
                                        new_text = old_text
                                    else:
                                        action = 'CLEAN'
                                        new_text = parsed
                                else:
                                    # Invalid
                                    action = 'NULLIFY'
                                    new_text = None
                                    null_after_repair += 1
                            except Exception:
                                action = 'NULLIFY'
                                new_text = None
                                null_after_repair += 1
                        
                        counts[action] += 1
                        
                        old_len = len(old_text) if old_text else 0
                        new_len = len(new_text) if new_text else 0
                        preview = (new_text[:40] if new_text else '') if new_text else ''
                        
                        log_and_write(
                            f"{contract_id}|{finding_id_short}|{action}|{old_len}|{new_len}|{preview}",
                            outfile
                        )
                        
                        # Apply changes if requested
                        if apply and action in ['CLEAN', 'NULLIFY']:
                            finding.explanation = new_text
                            if action == 'NULLIFY':
                                finding.explanation_generated_at = None
                    
                    # Summary for this contract
                    log_and_write(
                        f"Contract {contract_id}: {len(findings)} findings, "
                        f"KEEP={counts['KEEP']}, CLEAN={counts['CLEAN']}, "
                        f"NULLIFY={counts['NULLIFY']}, SKIP_NULL={counts['SKIP_NULL']}, "
                        f"NULL after repair: {null_after_repair}",
                        outfile
                    )
                    
                    # Update contract if needed
                    if apply:
                        if null_after_repair > 0:
                            contract.pipeline_stage = 'failed'
                            contract.failed_stage = 'generating_explanations'
                            contract.error_message = f"Explanations missing or invalid for {null_after_repair} finding(s)"
                            log_and_write(f"Contract {contract_id}: Set to FAILED", outfile)
                        else:
                            log_and_write(f"Contract {contract_id}: Stage unchanged", outfile)
                
                if apply:
                    await db.commit()
                    log_and_write("\n=== COMMITTED ===", outfile)
                else:
                    log_and_write("\n=== DRY-RUN (no changes) ===", outfile)
                
            except Exception as e:
                if apply:
                    await db.rollback()
                    log_and_write(f"\n=== ROLLED BACK: {e} ===", outfile)
                raise
            
            break  # Only process once
    
    finally:
        if outfile:
            outfile.close()


def main():
    parser = argparse.ArgumentParser(description='Repair stored explanations')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default: dry-run)')
    parser.add_argument('--out', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    asyncio.run(repair_explanations(apply=args.apply, out_path=args.out))


if __name__ == '__main__':
    main()
