"""
Run 5 test batches with varied clauses to build reliable statistics.

Each run tests 3 different clause types with different text variations.
Total: 15 classifications to assess real-world reliability.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from app.llm.classify_clauses import classify_clause


# 5 different test batches, each with 3 varied clauses
TEST_BATCHES = [
    # Batch 1: Original clauses
    [
        ("payment_terms", "Late Payment: If the monthly rent is not received by the 5th day of the month, a late fee of $50 will be charged for each month the payment is overdue."),
        ("termination", "Either party may terminate this agreement by providing thirty (30) days written notice to the other party. Upon termination, the tenant must vacate the premises and return all keys."),
        ("confidentiality", "The freelancer agrees to keep all proprietary information, trade secrets, and business data confidential and shall not disclose such information to any third party without prior written consent.")
    ],
    # Batch 2: Different payment/termination/IP clauses
    [
        ("payment_terms", "The tenant shall pay a security deposit equal to two months' rent, which will be held in an interest-bearing account and returned within 30 days of lease termination, less any deductions for damages."),
        ("termination", "This lease may be terminated immediately if the tenant fails to pay rent for 15 consecutive days or violates any material term of this agreement."),
        ("intellectual_property", "All code, designs, and documentation created by the contractor during this engagement shall remain the exclusive property of the client and constitute works made for hire.")
    ],
    # Batch 3: Liability/dispute/renewal clauses
    [
        ("liability", "The landlord shall not be liable for any injury, loss, or damage to persons or property occurring on the premises, except where such injury or loss results from the landlord's gross negligence or willful misconduct."),
        ("dispute_resolution", "Any disputes arising under this agreement shall be resolved through binding arbitration in accordance with the rules of the American Arbitration Association, with the arbitration venue in the county where the property is located."),
        ("renewal", "This agreement shall automatically renew for successive one-year terms unless either party provides written notice of non-renewal at least 60 days before the end of the current term.")
    ],
    # Batch 4: Warranties/indemnification/force_majeure
    [
        ("warranties", "The contractor warrants that all deliverables will be free from defects in workmanship and will conform to the specifications agreed upon in Exhibit A for a period of 90 days from delivery."),
        ("indemnification", "The tenant agrees to indemnify and hold harmless the landlord from any claims, damages, or liabilities arising from the tenant's use of the premises or any breach of this lease agreement."),
        ("force_majeure", "Neither party shall be liable for delays or failures in performance resulting from acts of God, natural disasters, war, terrorism, strikes, or other events beyond the party's reasonable control.")
    ],
    # Batch 5: Different term_duration/payment/other clauses
    [
        ("term_duration", "This lease agreement shall commence on January 1, 2024 and continue for a fixed term of twelve (12) months, expiring on December 31, 2024, unless terminated earlier in accordance with the terms herein."),
        ("payment_terms", "Rent is due on the first day of each month and shall be paid via electronic transfer to the landlord's designated bank account. A grace period of 5 days is provided, after which a $25 late fee applies."),
        ("other", "The tenant may keep one domestic pet not exceeding 25 pounds in weight, subject to an additional monthly pet fee of $50 and compliance with all applicable pet-related rules and regulations.")
    ]
]


async def test_single_clause(expected_type: str, clause_text: str, run_num: int, clause_num: int) -> dict:
    """Test one clause."""
    try:
        result = await classify_clause(
            clause_text=clause_text,
            clause_index=f"run{run_num}_c{clause_num}",
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
    print(f"RUN {batch_num}/5")
    print(f"{'='*70}")
    
    results = []
    for i, (expected, text) in enumerate(clauses, 1):
        print(f"\nClause {i}/3: {expected}")
        print(f"  Text: {text[:70]}...")
        
        result = await test_single_clause(expected, text, batch_num, i)
        results.append(result)
        
        if result['success'] and result['match']:
            print(f"  Result: PASS - returned '{result['actual']}' ({result['tokens']} tokens)")
        elif result['success']:
            print(f"  Result: FAIL - expected '{result['expected']}', got '{result['actual']}'")
        else:
            print(f"  Result: ERROR - {result.get('error', 'Unknown')[:100]}")
        
        await asyncio.sleep(0.5)  # Brief pause between calls
    
    return results


async def main():
    """Run all 5 batches."""
    print("="*70)
    print("OPENROUTER 5-RUN RELIABILITY TEST")
    print("="*70)
    print("Testing 15 varied clauses across 5 runs...")
    
    all_results = []
    
    for batch_num, clauses in enumerate(TEST_BATCHES, 1):
        batch_results = await run_batch(batch_num, clauses)
        all_results.extend(batch_results)
        await asyncio.sleep(1)  # Pause between batches
    
    # Final tally
    print(f"\n{'='*70}")
    print("FINAL TALLY (15 classifications)")
    print(f"{'='*70}")
    
    success_count = sum(1 for r in all_results if r['success'])
    match_count = sum(1 for r in all_results if r.get('match', False))
    total_tokens = sum(r.get('tokens', 0) for r in all_results)
    
    print(f"API calls succeeded: {success_count}/15")
    print(f"Exact enum matches: {match_count}/15")
    print(f"Pass rate: {match_count/15*100:.1f}%")
    print(f"Total tokens used: {total_tokens}")
    print()
    
    # Show any failures
    failures = [r for r in all_results if not r.get('match', False)]
    if failures:
        print(f"FAILURES ({len(failures)} total):")
        for r in failures:
            if r.get('success'):
                print(f"  Expected '{r['expected']}', got '{r['actual']}'")
            else:
                print(f"  Expected '{r['expected']}', ERROR: {r.get('error', 'Unknown')[:80]}")
    else:
        print("NO FAILURES - All 15 classifications produced exact enum matches!")
    
    print(f"{'='*70}")
    
    sys.exit(0 if match_count == 15 else 1)


if __name__ == "__main__":
    asyncio.run(main())
