"""
Smoke test for Stage 7 risk detection with real Gemini API calls.

Creates minimal test data and runs detect_risks() end-to-end.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import models and functions
from app.db.models import Contract, Clause, RiskFinding
from app.llm.detect_risk import detect_risks

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/scantract")


async def check_existing_contracts(session: AsyncSession):
    """Check if there are any contracts with classified clauses."""
    result = await session.execute(
        select(Contract)
        .join(Clause, Clause.contract_id == Contract.id)
        .where(Clause.clause_type.is_not(None))
        .distinct()
    )
    contracts = result.scalars().all()
    
    if contracts:
        print(f"✓ Found {len(contracts)} existing contract(s) with classified clauses")
        for contract in contracts:
            clause_result = await session.execute(
                select(Clause)
                .where(Clause.contract_id == contract.id)
                .where(Clause.clause_type.is_not(None))
            )
            clause_count = len(clause_result.scalars().all())
            print(f"  - Contract ID {contract.id}: {clause_count} classified clauses")
        return contracts[0].id if contracts else None
    
    return None


async def create_test_contract(session: AsyncSession):
    """Create a minimal test contract with classified clauses."""
    print("\n📝 Creating synthetic test contract...")
    
    # Create contract
    contract = Contract(
        contract_type="rental",
        filename="smoke_test_rental_agreement.pdf",
        uploaded_at=datetime.utcnow()
    )
    session.add(contract)
    await session.flush()  # Get the contract ID
    
    print(f"✓ Created contract ID: {contract.id}")
    
    # Create realistic rental clauses
    test_clauses = [
        {
            "clause_id": "1.1",
            "position": 1,
            "text": "The tenant shall pay a security deposit of Rs. 60,000 (equivalent to 4 months rent) which shall be refundable at the end of the tenancy period subject to deductions for any damages.",
            "clause_type": "payment_terms"
        },
        {
            "clause_id": "2.1",
            "position": 2,
            "text": "The landlord may terminate this agreement with 7 days written notice if the tenant fails to pay rent on time or violates any terms of this agreement.",
            "clause_type": "termination"
        },
        {
            "clause_id": "3.1",
            "position": 3,
            "text": "The tenant shall be solely liable for any and all damages to the property, including normal wear and tear, and shall indemnify the landlord against any claims.",
            "clause_type": "liability"
        },
        {
            "clause_id": "4.1",
            "position": 4,
            "text": "The monthly rent of Rs. 15,000 shall be paid by the 5th of each month. Late payment will incur a penalty of Rs. 500 per day.",
            "clause_type": "payment_terms"
        }
    ]
    
    for clause_data in test_clauses:
        clause = Clause(
            contract_id=contract.id,
            clause_id=clause_data["clause_id"],
            position=clause_data["position"],
            text=clause_data["text"],
            clause_type=clause_data["clause_type"],
            confidence=0.95,
            key_entities=["tenant", "landlord", "rent"],
            classified_at=datetime.utcnow()
        )
        session.add(clause)
    
    await session.commit()
    print(f"✓ Created {len(test_clauses)} classified clauses")
    
    return contract.id


async def run_risk_detection(session: AsyncSession, contract_id: int):
    """Run real risk detection with Gemini API."""
    print(f"\n🔍 Running risk detection for contract {contract_id}...")
    print("⚠️  This will make REAL Gemini API calls (not mocked)")
    print("=" * 70)
    
    try:
        # Call detect_risks with real API
        result = await detect_risks(str(contract_id), session)
        
        print("\n✅ Risk Detection Completed!")
        print("=" * 70)
        print(result.summary())
        print("=" * 70)
        
        # Show detailed findings
        if result.risky_clauses:
            print("\n🚨 RISKY CLAUSES DETECTED:")
            for idx, risky in enumerate(result.risky_clauses, 1):
                print(f"\n  [{idx}] Clause {risky.clause_id} - {risky.severity.value.upper()} severity")
                print(f"      Reason: {risky.reason[:100]}...")
                print(f"      Source: {risky.triggering_rule_or_corpus[:100]}...")
        
        if result.missing_clauses:
            print("\n📋 MISSING CLAUSES IDENTIFIED:")
            for idx, missing in enumerate(result.missing_clauses, 1):
                print(f"\n  [{idx}] {missing.expected_clause_type} - {missing.severity.value.upper()} severity")
                print(f"      Why: {missing.why_expected[:100]}...")
                print(f"      Source: {missing.triggering_rule_or_corpus[:100]}...")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error during risk detection: {e}")
        import traceback
        traceback.print_exc()
        raise


async def verify_database_persistence(session: AsyncSession, contract_id: int):
    """Verify findings were persisted to database."""
    print("\n\n🗄️  Verifying Database Persistence...")
    print("=" * 70)
    
    result = await session.execute(
        select(RiskFinding).where(RiskFinding.contract_id == contract_id)
    )
    findings = result.scalars().all()
    
    print(f"✓ Found {len(findings)} risk findings in database")
    
    risky_count = sum(1 for f in findings if f.finding_type == "risky_clause")
    missing_count = sum(1 for f in findings if f.finding_type == "missing_clause")
    
    print(f"  - Risky clauses: {risky_count}")
    print(f"  - Missing clauses: {missing_count}")
    
    # Show sample records
    if findings:
        print("\n📊 Sample Database Records:")
        for idx, finding in enumerate(findings[:3], 1):
            print(f"\n  [{idx}] ID: {finding.id}")
            print(f"      Type: {finding.finding_type}")
            print(f"      Severity: {finding.severity}")
            print(f"      Reason: {finding.reason[:80]}...")
            print(f"      Citation: {finding.triggering_rule_or_corpus[:80]}...")
            if finding.clause_id:
                print(f"      Clause ID: {finding.clause_id}")
            if finding.expected_clause_type:
                print(f"      Expected Type: {finding.expected_clause_type}")
    
    return findings


async def main():
    """Main smoke test execution."""
    print("\n" + "=" * 70)
    print("🧪 Stage 7 Risk Detection - End-to-End Smoke Test")
    print("=" * 70)
    
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Step 1: Check for existing contracts
        existing_contract_id = await check_existing_contracts(session)
        
        # Step 2: Create test contract if needed
        if existing_contract_id:
            contract_id = existing_contract_id
            print(f"\n→ Using existing contract ID: {contract_id}")
        else:
            print("\n→ No existing contracts found, creating test data...")
            contract_id = await create_test_contract(session)
        
        # Step 3: Run real risk detection
        result = await run_risk_detection(session, contract_id)
        
        # Step 4: Verify database persistence
        findings = await verify_database_persistence(session, contract_id)
        
        # Final summary
        print("\n\n" + "=" * 70)
        print("✅ SMOKE TEST COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"Contract ID: {contract_id}")
        print(f"Total Risks: {result.total_risks}")
        print(f"Total Missing: {result.total_missing}")
        print(f"High Severity: {result.high_severity_count}")
        print(f"Medium Severity: {result.medium_severity_count}")
        print(f"Low Severity: {result.low_severity_count}")
        print(f"Database Records: {len(findings)}")
        print("=" * 70)
        
        # Verify traceability
        print("\n🔍 Traceability Verification:")
        all_traceable = all(
            f.triggering_rule_or_corpus and f.triggering_rule_or_corpus.strip()
            for f in findings
        )
        if all_traceable:
            print("✅ All findings have non-empty triggering_rule_or_corpus citations")
        else:
            print("❌ WARNING: Some findings lack proper citations!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
