"""
Standalone script to test pipeline orchestrator.

Tests the full pipeline without HTTP/TestClient complications.
Hard timeout of 240 seconds to detect hangs.

Usage:
  python test_orchestrator_standalone.py [CONTRACT_ID] [--mock]
  
Arguments:
  CONTRACT_ID: Contract ID to process (default: 3)
  --mock: Use mock LLM responses instead of real API calls
"""
import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.db.database import AsyncSessionLocal
from app.db.models import Contract, Clause, RiskFinding
from app.document_processing.orchestrator import run_full_pipeline


def log_with_timestamp(message: str):
    """Print message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}", flush=True)


def create_mock_llm_response(clause_text: str) -> str:
    """Create a mock JSON response for clause classification."""
    # Mock classification based on keywords - use VALID clause_type values
    if "rent" in clause_text.lower() or "payment" in clause_text.lower():
        clause_type = "payment_terms"
    elif "terminate" in clause_text.lower() or "notice" in clause_text.lower():
        clause_type = "termination"
    elif "repair" in clause_text.lower() or "maintain" in clause_text.lower():
        clause_type = "liability"
    else:
        # Default to 'other' which is a valid literal value
        clause_type = "other"
    
    return json.dumps({
        "clause_type": clause_type,
        "key_entities": ["tenant", "landlord"],
        "confidence": 0.85
    })


def create_mock_risk_response(clause_count: int = 4) -> str:
    """Create a mock JSON response for risk detection.
    
    Args:
        clause_count: Number of clauses in contract (for generating valid clause_ids)
    """
    # Create risky clauses for first 3 clauses if they exist
    # CRITICAL: clause_id format must match DB format (e.g., "1.", "2.", "3." with trailing period)
    risky_clauses = []
    for i in range(min(3, clause_count)):
        risky_clauses.append({
            "clause_id": f"{i+1}.",  # Match DB format: "1.", "2.", "3."
            "reason": f"Mock risky clause {i+1} detected for testing purposes",
            "triggering_rule_or_corpus": f"Mock Legal Rule: Test Citation (Section 5.{i+1}.2)",
            "severity": "medium" if i == 0 else "low"
        })
    
    return json.dumps({
        "risky_clauses": risky_clauses,
        "missing_clauses": [
            {
                "expected_clause_type": "dispute_resolution",
                "why_expected": "Mock: Standard contracts typically include dispute resolution mechanisms",
                "triggering_rule_or_corpus": "Mock Reference Corpus: Common Practice Clause Database",
                "severity": "low"
            }
        ]
    })


def create_mock_explanation_response() -> str:
    """Create a mock explanation."""
    return "This is a mock explanation for testing purposes."


async def test_orchestrator_on_contract(contract_id: int, use_mock: bool = False):
    """Run full pipeline on a contract with detailed logging."""
    
    log_with_timestamp("="*70)
    log_with_timestamp(f"STANDALONE ORCHESTRATOR TEST - CONTRACT {contract_id}")
    if use_mock:
        log_with_timestamp("MODE: MOCK (fake LLM responses)")
    else:
        log_with_timestamp("MODE: REAL (actual Gemini API calls)")
    log_with_timestamp("="*70)
    
    start_time = datetime.now()
    
    async with AsyncSessionLocal() as db:
        # Step 1: Check initial state
        log_with_timestamp(f"Step 1: Querying initial state of contract {contract_id}...")
        
        result = await db.execute(select(Contract).where(Contract.id == contract_id))
        contract = result.scalar_one_or_none()
        
        if not contract:
            log_with_timestamp(f"ERROR: Contract {contract_id} not found!")
            return False
        
        clause_result = await db.execute(select(Clause).where(Clause.contract_id == contract_id))
        clauses = clause_result.scalars().all()
        
        log_with_timestamp(f"  Contract ID: {contract.id}")
        log_with_timestamp(f"  Type: {contract.contract_type}")
        log_with_timestamp(f"  Pipeline Stage: {contract.pipeline_stage}")
        log_with_timestamp(f"  Processing Status: {contract.processing_status}")
        log_with_timestamp(f"  Clause Count: {len(clauses)}")
        log_with_timestamp(f"  Classified Clauses: {sum(1 for c in clauses if c.clause_type is not None)}")
        
        # Step 2: Run pipeline with timeout
        log_with_timestamp(f"\nStep 2: Running full pipeline orchestrator...")
        log_with_timestamp(f"  Timeout: 240 seconds")
        log_with_timestamp(f"  Starting at: {start_time}")
        
        clause_count = len(clauses)  # For mock response generation
        
        try:
            if use_mock:
                log_with_timestamp("  Setting up mocks...")
                
                # Mock the LLM calls at the point where they're imported
                # classify_clauses.py imports: from app.llm.llm_client import call_llm
                # detect_risk.py imports: from .llm_client import call_llm
                # generate_explanations.py imports: from .llm_client import call_llm
                
                with patch('app.llm.classify_clauses.call_llm') as mock_classify_llm:
                    with patch('app.llm.detect_risk.call_llm') as mock_risk_llm:
                        with patch('app.llm.generate_explanations.call_llm') as mock_explain_llm:
                            
                            # Set up mock for classification
                            async def mock_classify_call(*args, **kwargs):
                                log_with_timestamp("    [MOCK] Classification LLM call intercepted")
                                return (create_mock_llm_response("test clause"), 100)
                            mock_classify_llm.side_effect = mock_classify_call
                            
                            # Set up mock for risk detection
                            async def mock_risk_call(*args, **kwargs):
                                log_with_timestamp("    [MOCK] Risk detection LLM call intercepted")
                                return (create_mock_risk_response(clause_count), 200)
                            mock_risk_llm.side_effect = mock_risk_call
                            
                            # Set up mock for explanation generation
                            async def mock_explain_call(*args, **kwargs):
                                log_with_timestamp("    [MOCK] Explanation LLM call intercepted")
                                return (create_mock_explanation_response(), 150)
                            mock_explain_llm.side_effect = mock_explain_call
                            
                            log_with_timestamp("  Mocks configured, starting pipeline...")
                            
                            # Wrap in timeout
                            await asyncio.wait_for(
                                run_full_pipeline(contract_id, db),
                                timeout=240.0
                            )
            else:
                # Real API calls
                await asyncio.wait_for(
                    run_full_pipeline(contract_id, db),
                    timeout=240.0
                )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            log_with_timestamp(f"  Completed at: {end_time}")
            log_with_timestamp(f"  TOTAL DURATION: {duration:.3f} seconds")
            log_with_timestamp(f"\nStep 3: Pipeline completed successfully!")
            
        except asyncio.TimeoutError:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            log_with_timestamp(f"\nERROR: Pipeline timed out after {duration:.3f} seconds!")
            log_with_timestamp(f"  Check which stage it was stuck on...")
            
            # Query current state
            result = await db.execute(select(Contract).where(Contract.id == contract_id))
            contract = result.scalar_one()
            log_with_timestamp(f"  Last pipeline_stage: {contract.pipeline_stage}")
            log_with_timestamp(f"  Failed stage: {contract.failed_stage}")
            log_with_timestamp(f"  Error message: {contract.error_message}")
            return False
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            log_with_timestamp(f"\nERROR: Pipeline failed with exception after {duration:.3f} seconds!")
            log_with_timestamp(f"  Exception type: {type(e).__name__}")
            log_with_timestamp(f"  Exception message: {str(e)}")
            
            # Query current state
            result = await db.execute(select(Contract).where(Contract.id == contract_id))
            contract = result.scalar_one()
            log_with_timestamp(f"  Pipeline stage: {contract.pipeline_stage}")
            log_with_timestamp(f"  Failed stage: {contract.failed_stage}")
            log_with_timestamp(f"  DB error message: {contract.error_message}")
            return False
        
        # Step 4: Query final state
        log_with_timestamp(f"\nStep 4: Querying final state...")
        
        result = await db.execute(select(Contract).where(Contract.id == contract_id))
        contract = result.scalar_one()
        
        clause_result = await db.execute(select(Clause).where(Clause.contract_id == contract_id))
        clauses = clause_result.scalars().all()
        classified_clauses = [c for c in clauses if c.clause_type is not None]
        
        risk_result = await db.execute(select(RiskFinding).where(RiskFinding.contract_id == contract_id))
        findings = risk_result.scalars().all()
        
        log_with_timestamp(f"\n{'='*70}")
        log_with_timestamp(f"FINAL STATE:")
        log_with_timestamp(f"{'='*70}")
        log_with_timestamp(f"  Contract ID: {contract.id}")
        log_with_timestamp(f"  Pipeline Stage: {contract.pipeline_stage}")
        log_with_timestamp(f"  Processing Status: {contract.processing_status}")
        log_with_timestamp(f"  Failed Stage: {contract.failed_stage}")
        log_with_timestamp(f"  Error Message: {contract.error_message}")
        log_with_timestamp(f"")
        log_with_timestamp(f"  Total Clauses: {len(clauses)}")
        log_with_timestamp(f"  Classified Clauses: {len(classified_clauses)}")
        log_with_timestamp(f"  Risk Findings: {len(findings)}")
        
        if findings:
            risky = sum(1 for f in findings if f.finding_type == 'risky_clause')
            missing = sum(1 for f in findings if f.finding_type == 'missing_clause')
            with_explanations = sum(1 for f in findings if f.explanation is not None)
            
            log_with_timestamp(f"    - Risky: {risky}")
            log_with_timestamp(f"    - Missing: {missing}")
            log_with_timestamp(f"    - With Explanations: {with_explanations}/{len(findings)}")
        
        log_with_timestamp(f"{'='*70}")
        
        # Verify success
        success = (
            contract.pipeline_stage == 'completed' and
            len(classified_clauses) == len(clauses) and
            len(findings) >= 0
        )
        
        if success:
            log_with_timestamp(f"\n[SUCCESS] Orchestrator test PASSED")
        else:
            log_with_timestamp(f"\n[FAILED] Orchestrator test FAILED")
            log_with_timestamp(f"  Expected: pipeline_stage='completed', all clauses classified")
            log_with_timestamp(f"  Got: pipeline_stage='{contract.pipeline_stage}', {len(classified_clauses)}/{len(clauses)} classified")
        
        return success


async def main():
    """Main entry point."""
    # Parse arguments
    contract_id = 3
    use_mock = False
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--mock':
            use_mock = True
        elif sys.argv[1].isdigit():
            contract_id = int(sys.argv[1])
            if len(sys.argv) > 2 and sys.argv[2] == '--mock':
                use_mock = True
        elif sys.argv[1] == '-h' or sys.argv[1] == '--help':
            print(__doc__)
            sys.exit(0)
    
    try:
        success = await test_orchestrator_on_contract(contract_id, use_mock)
        sys.exit(0 if success else 1)
    except Exception as e:
        log_with_timestamp(f"\nFATAL ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
