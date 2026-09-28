"""
FINAL prompt test: 15 fresh classifications with heavy emphasis on "other" disambiguation.

Tests the strengthened prompt with explicit "other" category guidance.
This is the LAST prompt-engineering attempt before final model decision.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from app.llm.classify_clauses import classify_clause


# Final 5 test batches - heavily weighted toward ambiguous/"other" clauses
# that previously failed (governing law, notices, pet policy, compliance, etc.)
TEST_BATCHES = [
    # Batch 1: Governing law, severability, assignment
    [
        ("other", "This Agreement shall be governed by and construed in accordance with the laws of the State of New York, without giving effect to any choice or conflict of law provision or rule."),
        ("other", "If any provision of this Agreement is held to be invalid or unenforceable, the remaining provisions shall continue in full force and effect."),
        ("other", "Tenant shall not assign, sublease, or transfer any interest in this lease without prior written consent of Landlord, which consent may be withheld in Landlord's sole discretion.")
    ],
    # Batch 2: Notice delivery, amendments, pet policy with fee
    [
        ("other", "All notices under this Agreement shall be in writing and delivered by hand, overnight courier, or certified mail, return receipt requested, to the addresses set forth herein."),
        ("other", "No modification, amendment, or waiver of any provision of this Agreement shall be effective unless in writing and signed by the party against whom enforcement is sought."),
        ("other", "Tenant may keep one dog or cat weighing no more than 30 pounds, subject to Landlord's approval and a non-refundable pet deposit of $300.")
    ],
    # Batch 3: Entire agreement, quiet enjoyment, general compliance
    [
        ("other", "This Agreement, including all attached exhibits and addenda, constitutes the entire agreement between the parties and supersedes all prior understandings, written or oral, relating to the subject matter hereof."),
        ("other", "Landlord covenants that Tenant, upon paying the rent and performing all obligations under this lease, shall peacefully and quietly enjoy the premises without disturbance from Landlord."),
        ("other", "Tenant agrees to comply with all applicable building codes, zoning ordinances, and homeowners association rules governing use of the property.")
    ],
    # Batch 4: Mix with actual specific categories to avoid 100% "other" pattern
    [
        ("dispute_resolution", "Any controversy or claim arising out of or relating to this Agreement shall be settled by binding arbitration administered by JAMS in Los Angeles, California, under its Comprehensive Arbitration Rules."),
        ("payment_terms", "Tenant shall pay to Landlord the sum of $2,500 as a security deposit, to be held in an interest-bearing escrow account and returned within 30 days of lease termination, less any deductions for damages."),
        ("other", "Failure by either party to enforce any provision of this Agreement shall not constitute a waiver of that provision or any other provision.")
    ],
    # Batch 5: More "other" + one clear termination
    [
        ("other", "Tenant is responsible for arranging and paying for all utilities, including electricity, gas, water, sewer, trash collection, and internet service at the premises."),
        ("other", "Landlord shall provide Tenant with two parking spaces in the attached garage. No additional vehicles may be parked on the property without Landlord's written permission."),
        ("termination", "In the event Tenant fails to pay rent within 10 days of the due date, Landlord may terminate this lease immediately upon written notice and pursue all available legal remedies including eviction.")
    ]
]


async def test_single_clause(expected_type: str, clause_text: str, run_num: int, clause_num: int) -> dict:
    """Test one clause."""
    try:
        result = await classify_clause(
            clause_text=clause_text,
            clause_index=f"final_run{run_num}_c{clause_num}",
            contract_type="rental",
            retrieved_context=""
        )
        
        if result.classification:
            actual = result.classification.clause_type
            return {
                "success": True,
                "match": actual == expected_type,
                "expected": expected_type,
                "actual": actual,
                "tokens": result.tokens_used
            }
        else:
            return {
                "success": False,
                "match": False,
                "expected": expected_type,
                "error": result.error
            }
    except Exception as e:
        return {
            "success": False,
            "match": False,
            "expected": expected_type,
            "error": str(e)[:150]
        }


async def run_batch(batch_num: int, clauses: list) -> list:
    """Run one batch of 3 clauses."""
    print(f"\n{'='*70}")
    print(f"FINAL TEST - RUN {batch_num}/5")
    print(f"{'='*70}")
    
    results = []
    for i, (expected, text) in enumerate(clauses, 1):
        print(f"\nClause {i}/3: {expected}")
        print(f"  Text: {text[:80]}...")
        
        result = await test_single_clause(expected, text, batch_num, i)
        results.append(result)
        
        if result['success'] and result['match']:
            print(f"  Result: ✓ PASS - '{result['actual']}' ({result['tokens']} tokens)")
        elif result['success']:
            print(f"  Result: ✗ MISMATCH - expected '{result['expected']}', got '{result['actual']}'")
        else:
            print(f"  Result: ✗ ERROR - {result.get('error', 'Unknown')[:100]}")
        
        await asyncio.sleep(0.5)
    
    return results


async def main():
    """Run final 5 batches."""
    print("="*70)
    print("FINAL PROMPT TEST - 15 FRESH CLASSIFICATIONS")
    print("="*70)
    print("Focus: Heavy disambiguation of 'other' category")
    print("Clauses include: governing law, notices, pet policies, etc.")
    print()
    
    all_results = []
    
    for batch_num, clauses in enumerate(TEST_BATCHES, 1):
        batch_results = await run_batch(batch_num, clauses)
        all_results.extend(batch_results)
        await asyncio.sleep(1)
    
    # Final tally
    print(f"\n{'='*70}")
    print("FINAL TALLY - 15 CLASSIFICATIONS")
    print(f"{'='*70}")
    
    success_count = sum(1 for r in all_results if r['success'])
    match_count = sum(1 for r in all_results if r.get('match', False))
    total_tokens = sum(r.get('tokens', 0) for r in all_results)
    
    print(f"API calls succeeded: {success_count}/15")
    print(f"Expected value matches: {match_count}/15")
    print(f"Correctness rate: {match_count/15*100:.1f}%")
    print(f"Total tokens used: {total_tokens}")
    print()
    
    # Show issues
    issues = [r for r in all_results if not r.get('match', False)]
    if issues:
        print(f"ISSUES ({len(issues)} total):")
        for r in issues:
            if r.get('success'):
                print(f"  ✗ Expected '{r['expected']}', got '{r['actual']}'")
            else:
                print(f"  ✗ Expected '{r['expected']}', ERROR: {r.get('error', 'Unknown')[:80]}")
    else:
        print("✓ PERFECT - All 15 classifications matched expected values!")
    
    print(f"{'='*70}")
    
    return all_results


if __name__ == "__main__":
    results = asyncio.run(main())
    success_count = sum(1 for r in results if r.get('match', False))
    sys.exit(0 if success_count == 15 else 1)
