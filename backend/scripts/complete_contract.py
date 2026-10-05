"""
Complete the explanation stage for contract 44.

Calls the real _run_explanation_stage from orchestrator.
"""
import asyncio
import argparse
import sys
import logging
from pathlib import Path

# Custom formatter to truncate log messages
class TruncatingFormatter(logging.Formatter):
    def format(self, record):
        msg = super().format(record)
        if len(msg) > 200:
            return msg[:197] + '...'
        return msg

# Set up logging
handler = logging.StreamHandler()
handler.setFormatter(TruncatingFormatter('%(levelname)s - %(name)s - %(message)s'))

logging.root.setLevel(logging.INFO)
logging.root.addHandler(handler)

# Only log app.llm and app.document_processing
for logger_name in ['app.llm', 'app.document_processing']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Contract
from app.document_processing.orchestrator import _run_explanation_stage


ALLOWED_CONTRACT = 44


def log_and_write(msg: str, outfile=None):
    """Print message and optionally write to file."""
    print(msg)
    if outfile:
        outfile.write(msg + '\n')
        outfile.flush()


async def complete_contract(out_path: str = None):
    """
    Complete explanation stage for contract 44.
    
    Args:
        out_path: Optional file path to write output.
    """
    assert ALLOWED_CONTRACT == 44, "Only contract 44 is allowed"
    
    outfile = None
    if out_path:
        outfile = open(out_path, 'w', encoding='utf-8')
    
    try:
        async for db in get_db():
            try:
                # Load contract
                result = await db.execute(
                    select(Contract).where(Contract.id == ALLOWED_CONTRACT)
                )
                contract = result.scalar_one_or_none()
                
                if not contract:
                    log_and_write(f"Contract {ALLOWED_CONTRACT}: NOT FOUND", outfile)
                    break
                
                # Assert it's in failed state
                assert contract.pipeline_stage == 'failed', f"Expected failed, got {contract.pipeline_stage}"
                assert contract.failed_stage == 'generating_explanations', f"Expected generating_explanations, got {contract.failed_stage}"
                
                log_and_write(f"Contract {ALLOWED_CONTRACT}: State verified (failed at generating_explanations)", outfile)
                
                # Call the real _run_explanation_stage
                try:
                    await _run_explanation_stage(contract, db)
                    
                    # If we get here without raising, set to completed
                    contract.pipeline_stage = 'completed'
                    contract.processing_status = 'completed'
                    contract.failed_stage = None
                    contract.error_message = None
                    await db.commit()
                    
                    log_and_write(f"Contract {ALLOWED_CONTRACT}: Successfully completed", outfile)
                    
                except Exception as e:
                    # Stage raised, leave it failed
                    error_msg = str(e)
                    if len(error_msg) > 300:
                        error_msg = error_msg[:297] + '...'
                    log_and_write(f"Contract {ALLOWED_CONTRACT}: Exception raised: {error_msg}", outfile)
                    # Don't re-raise, just report
            
            except Exception as e:
                error_msg = str(e)
                if len(error_msg) > 300:
                    error_msg = error_msg[:297] + '...'
                log_and_write(f"Error: {error_msg}", outfile)
                raise
            
            break  # Only process once
    
    finally:
        if outfile:
            outfile.close()


def main():
    parser = argparse.ArgumentParser(description='Complete explanation stage for contract 44')
    parser.add_argument('--out', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    asyncio.run(complete_contract(out_path=args.out))


if __name__ == '__main__':
    main()
