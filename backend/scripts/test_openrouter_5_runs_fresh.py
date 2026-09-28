"""
Run 5 test batches with FRESH varied clauses (different from previous 18 attempts).

Each run tests 3 different clause types with completely new text.
Total: 15 NEW classifications to assess fallback mechanism effectiveness.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from app.llm.classify_clauses import classify_clause


# 5 FRESH test batches - different clause texts from all previous rounds
TEST_BATCHES = [
    # Batch 1: Maintenance/assignment/insurance clauses
    [
        ("other", "The landlord shall be responsible for all major structural repairs including roof, foundation, and exterior walls. The tenant shall promptly notify the landlord of any necessary repairs."),
        ("other", "The tenant may not assign this lease or sublet the premises without obtaining prior written consent from the landlord, which consent shall not be unreasonably withheld."),
        ("liability", "The tenant is required to maintain renter's insurance with minimum coverage of $100,000 for personal liability and shall provide proof of insurance to the landlord upon request.")
    ],
    # Batch 2: Governing law/notices/amendments
    [
        ("other", "This agreement shall be governed by and construed in accordance with the laws of the State of California, without regard to its conflict of law provisions."),
        ("other", "All notices required under this agreement must be delivered in writing via certified mail to the addresses specified in this document, and shall be deemed received three business days after mailing."),
        ("other", "Any amendments or modifications to this agreement must be made in writing and signed by both parties to be valid and enforceable.")
    ],
    # Batch 3: Utilities/access/pets
    [
        ("payment_terms", "The tenant shall be responsible for payment of all utilities including electricity, gas, water, and internet service. The landlord shall pay for trash collection and common area maintenance."),
        ("other", "The landlord reserves the right to enter the premises for inspections, repairs, or showings to prospective tenants, provided 24 hours advance written notice is given except in emergencies."),
        ("other", "No pets are permitted on the premises without prior written approval from the landlord. Unauthorized pets may result in lease termination and forfeiture of security deposit.")
    ],
    # Batch 4: Compliance/quiet enjoyment/default
    [
        ("other", "The tenant agrees to comply with all applicable federal, state, and local laws, ordinances, and regulations, including but not limited to health, safety, and building codes."),
        ("other", "The tenant shall have the right to quiet enjoyment of the premises without interference from the landlord, subject to the landlord's reserved rights under this agreement."),
        ("termination", "In the event of default by the tenant, including non-payment of rent or material breach of this agreement, the landlord may terminate this lease upon 10 days written notice and pursue all available legal remedies.")
    ],
    # Batch 5: Damage/parking/entire agreement
    [
        ("liability", "The tenant shall be liable for any damage to the premises beyond normal wear and tear, including damage caused by the tenant's guests, and shall reimburse the landlord for reasonable repair costs."),
        ("other", "The tenant is assigned one designated parking space in the building garage. Additional parking is not permitted without prior written authorization and payment of applicable fees."),
        ("other", "This document constitutes the entire agreement between the parties and supersedes all prior negotiations, representations, or agreements, whether written or oral, relating to the subject matter herein.")
    ]
]


async def test_single_clause(expected_type: str, clause_text: str, run_num: int, clause_num: int) -> dict:
    """Test one clause and track if fuzzy matching was used."""
    try:
        result = await classify_clause(
            clause_text=clause_text,
            clause_index=f"fresh_run{run_num}_c{clause_num}",
            contract_type="rental",
            retrieved_context=""
        )
        
        if result.classification:
            actual = result.classification.clause_type
            # We can't directly detect if fuzzy matching was used from here
            # (it's logged internally), but we track exact vs non-exact matches
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
    print(f"RUN {batch_num}/5 (FRESH SAMPLE)")
    print(f"{'='*70}")
    
    results = []
    for i, (expected, text) in enumerate(clauses, 1):
        print(f"\nClause {i}/3: {expected}")
        print(f"  Text: {text[:80]}...")
        
        result = await test_single_clause(expected, text, batch_num, i)
        results.append(result)
        
        if result['success'] and result['match']:
            print(f"  Result: PASS - returned '{result['actual']}' ({result['tokens']} tokens)")
        elif result['success']:
            print(f"  Result: MISMATCH - expected '{result['expected']}', got '{result['actual']}'")
        else:
            print(f"  Result: ERROR - {result.get('error', 'Unknown')[:100]}")
        
        await asyncio.sleep(0.5)  # Brief pause between calls
    
    return results


async def main():
    """Run all 5 fresh batches."""
    print("="*70)
    print("OPENROUTER FRESH 15-CLASSIFICATION TEST WITH FALLBACK MECHANISMS")
    print("="*70)
    print("Testing 15 NEW clauses (different from previous 18 attempts)...")
    print("Fallback mechanisms enabled:")
    print("  1. Retry on empty response (3 attempts, 1.5s delay)")
    print("  2. Fuzzy enum matching + fallback to 'other'")
    print()
    
    all_results = []
    
    for batch_num, clauses in enumerate(TEST_BATCHES, 1):
        batch_results = await run_batch(batch_num, clauses)
        all_results.extend(batch_results)
        await asyncio.sleep(1)  # Pause between batches
    
    # Final tally for THIS round
    print(f"\n{'='*70}")
    print("FINAL TALLY - FRESH 15 CLASSIFICATIONS")
    print(f"{'='*70}")
    
    success_count = sum(1 for r in all_results if r['success'])
    match_count = sum(1 for r in all_results if r.get('match', False))
    total_tokens = sum(r.get('tokens', 0) for r in all_results)
    
    print(f"API calls succeeded: {success_count}/15")
    print(f"Expected value matches: {match_count}/15")
    print(f"Pass rate: {match_count/15*100:.1f}%")
    print(f"Total tokens used: {total_tokens}")
    print()
    
    # Show any mismatches/failures
    issues = [r for r in all_results if not r.get('match', False)]
    if issues:
        print(f"ISSUES ({len(issues)} total):")
        for r in issues:
            if r.get('success'):
                print(f"  MISMATCH: Expected '{r['expected']}', got '{r['actual']}'")
            else:
                print(f"  ERROR: Expected '{r['expected']}', error: {r.get('error', 'Unknown')[:80]}")
    else:
        print("NO ISSUES - All 15 classifications matched expected values!")
    
    print(f"{'='*70}")
    print()
    print("NOTE: Check logs above for 'Fuzzy matched' messages to see how often")
    print("      the fuzzy matching fallback was actually used vs exact matches.")
    print(f"{'='*70}")
    
    return all_results


if __name__ == "__main__":
    results = asyncio.run(main())
    
    # Return results for combined analysis
    success_count = sum(1 for r in results if r.get('match', False))
    sys.exit(0 if success_count == 15 else 1)
