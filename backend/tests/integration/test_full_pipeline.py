"""
Integration test for full pipeline orchestration (Stage 10).

Tests end-to-end contract processing from upload through explanation generation.
"""
import asyncio
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import AsyncSessionLocal
from app.db.models import Contract, Clause, RiskFinding


def test_full_pipeline_integration():
    """
    INTEGRATION TEST: Upload contract and verify full pipeline execution.
    
    This test:
    1. Uploads a real PDF contract through POST /api/contracts/upload
    2. Polls until pipeline completes or times out
    3. Queries DB directly to verify all stages completed
    4. Asserts: clause_count > 0, classified_count == clause_count, risk_finding_count >= 0
    
    Note: Uses REAL Gemini API calls (not mocked). This test will consume API quota.
    """
    # Get test file (resolve from backend/tests/integration/ up to project root)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent  # integration -> tests -> backend -> project root
    test_file_path = project_root / "backend/uploads/temp/20260825_132559_65b67fa7_test_contract.pdf"
    
    if not test_file_path.exists():
        pytest.skip(f"Test file not found: {test_file_path}")
    
    print(f"\n{'='*70}")
    print(f"FULL PIPELINE INTEGRATION TEST")
    print(f"{'='*70}")
    print(f"Test file: {test_file_path.name}")
    
    client = TestClient(app)
    
    # Step 1: Upload contract
    print(f"\n[Step 1] Uploading contract...")
    
    with open(test_file_path, "rb") as f:
        files = {"file": (test_file_path.name, f, "application/pdf")}
        response = client.post("/api/contracts/upload", files=files)
    
    assert response.status_code == 200, f"Upload failed: {response.text}"
    
    upload_data = response.json()
    contract_id = upload_data["contract_id"]
    
    print(f"[SUCCESS] Contract uploaded: ID={contract_id}")
    print(f"   Status: {upload_data['status']}")
    
    # Step 2: Poll for completion (using synchronous sleep and async DB queries)
    print(f"\n[Step 2] Polling for pipeline completion...")
    
    max_wait_seconds = 180  # 3 minutes timeout
    poll_interval = 3
    start_time = time.time()
    
    pipeline_completed = False
    last_stage = None
    
    async def check_pipeline_status():
        nonlocal pipeline_completed, last_stage
        
        async with AsyncSessionLocal() as db:
            while time.time() - start_time < max_wait_seconds:
                # Query contract status
                result = await db.execute(
                    select(Contract).where(Contract.id == contract_id)
                )
                contract = result.scalar_one()
                
                current_stage = contract.pipeline_stage
                
                # Print stage updates
                if current_stage != last_stage:
                    print(f"   Pipeline stage: {current_stage}")
                    last_stage = current_stage
                
                # Check for completion
                if current_stage == 'completed':
                    pipeline_completed = True
                    print(f"[SUCCESS] Pipeline completed in {time.time() - start_time:.1f}s")
                    break
                
                # Check for failure
                if current_stage == 'failed':
                    print(f"\n[FAILED] Pipeline failed at stage: {contract.failed_stage}")
                    print(f"   Error: {contract.error_message}")
                    pytest.fail(
                        f"Pipeline failed at {contract.failed_stage}: {contract.error_message}"
                    )
                
                await asyncio.sleep(poll_interval)
            
            if not pipeline_completed:
                print(f"\n[TIMEOUT] Pipeline timeout after {max_wait_seconds}s")
                print(f"   Last stage: {last_stage}")
                pytest.fail(
                    f"Pipeline did not complete within {max_wait_seconds}s. "
                    f"Last stage: {last_stage}"
                )
    
    # Run async check
    asyncio.run(check_pipeline_status())
    
    # Step 3: Verify database state
    async def verify_database_state():
        print(f"\n[Step 3] Verifying database state...")
        
        async with AsyncSessionLocal() as db:
            # Query clause counts
            clause_result = await db.execute(
                select(Clause).where(Clause.contract_id == contract_id)
            )
            clauses = clause_result.scalars().all()
            
            classified_clauses = [c for c in clauses if c.clause_type is not None]
            
            # Query risk findings
            risk_result = await db.execute(
                select(RiskFinding).where(RiskFinding.contract_id == contract_id)
            )
            risk_findings = risk_result.scalars().all()
            
            # Get contract
            contract_result = await db.execute(
                select(Contract).where(Contract.id == contract_id)
            )
            contract = contract_result.scalar_one()
            
            # Print results
            print(f"\n[RESULTS]")
            print(f"{'='*70}")
            print(f"Contract ID: {contract_id}")
            print(f"Pipeline Stage: {contract.pipeline_stage}")
            print(f"Processing Status: {contract.processing_status}")
            print(f"")
            print(f"Clauses: {len(clauses)}")
            print(f"Classified: {len(classified_clauses)}")
            print(f"Risk Findings: {len(risk_findings)}")
            
            if risk_findings:
                risky = sum(1 for f in risk_findings if f.finding_type == 'risky_clause')
                missing = sum(1 for f in risk_findings if f.finding_type == 'missing_clause')
                high = sum(1 for f in risk_findings if f.severity == 'high')
                medium = sum(1 for f in risk_findings if f.severity == 'medium')
                low = sum(1 for f in risk_findings if f.severity == 'low')
                
                print(f"  - Risky clauses: {risky}")
                print(f"  - Missing clauses: {missing}")
                print(f"  - High severity: {high}")
                print(f"  - Medium severity: {medium}")
                print(f"  - Low severity: {low}")
                
                # Check explanations
                with_explanations = sum(
                    1 for f in risk_findings if f.explanation is not None
                )
                print(f"  - With explanations: {with_explanations}/{len(risk_findings)}")
            
            print(f"{'='*70}")
            
            # Step 4: Assertions
            print(f"\n[Step 4] Running assertions...")
            
            assert len(clauses) > 0, "No clauses were extracted"
            print(f"   [OK] Clauses extracted: {len(clauses)}")
            
            assert len(classified_clauses) == len(clauses), \
                f"Not all clauses classified: {len(classified_clauses)}/{len(clauses)}"
            print(f"   [OK] All clauses classified: {len(classified_clauses)}/{len(clauses)}")
            
            # Note: risk_finding_count >= 0 is valid (clean contract may have 0 risks)
            assert len(risk_findings) >= 0, "Risk findings should be non-negative"
            print(f"   [OK] Risk detection completed: {len(risk_findings)} findings")
            
            # Verify all findings have explanations
            if risk_findings:
                assert with_explanations == len(risk_findings), \
                    f"Not all findings have explanations: {with_explanations}/{len(risk_findings)}"
                print(f"   [OK] All findings have explanations: {with_explanations}/{len(risk_findings)}")
            
            # Verify traceability
            for finding in risk_findings:
                assert finding.triggering_rule_or_corpus, \
                    f"Finding {finding.id} missing triggering_rule_or_corpus"
            print(f"   [OK] All findings have traceability citations")
            
            print(f"\n{'='*70}")
            print(f"[SUCCESS] FULL PIPELINE INTEGRATION TEST PASSED")
            print(f"{'='*70}\n")
    
    asyncio.run(verify_database_state())
