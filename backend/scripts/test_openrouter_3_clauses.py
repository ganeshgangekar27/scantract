"""
Test OpenRouter with 3 different clause types to verify reliable enum matching.

Tests payment, termination, and confidentiality clauses.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from app.llm.classify_clauses import classify_clause


TEST_CLAUSES = [
    {
        "name": "Payment Clause",
        "text": "Late Payment: If the monthly rent is not received by the 5th day of the month, a late fee of $50 will be charged for each month the payment is overdue.",
        "expected_type": "payment_terms"
    },
    {
        "name": "Termination Clause",
        "text": "Either party may terminate this agreement by providing thirty (30) days written notice to the other party. Upon termination, the tenant must vacate the premises and return all keys.",
        "expected_type": "termination"
    },
    {
        "name": "Confidentiality Clause",
        "text": "The freelancer agrees to keep all proprietary information, trade secrets, and business data confidential and shall not disclose such information to any third party without prior written consent.",
        "expected_type": "confidentiality"
    }
]


async def test_clause(clause_data: dict, index: int) -> dict:
    """Test a single clause and return results."""
    print(f"\n{'='*70}")
    print(f"TEST {index + 1}/3: {clause_data['name']}")
    print(f"{'='*70}")
    print(f"Clause text: {clause_data['text'][:80]}...")
    print(f"Expected type: {clause_data['expected_type']}")
    print()
    
    try:
        result = await classify_clause(
            clause_text=clause_data['text'],
            clause_index=f"test_{index + 1}",
            contract_type="rental",
            retrieved_context=""
        )
        
        if result.classification:
            actual_type = result.classification.clause_type
            confidence = result.classification.confidence
            tokens = result.tokens_used
            
            success = (actual_type == clause_data['expected_type'])
            
            print(f"✅ Classification succeeded:")
            print(f"  Returned type: {actual_type}")
            print(f"  Confidence: {confidence}")
            print(f"  Tokens used: {tokens}")
            print(f"  Match: {'✅ CORRECT' if success else '❌ WRONG'}")
            
            return {
                "success": True,
                "match": success,
                "returned": actual_type,
                "expected": clause_data['expected_type'],
                "tokens": tokens
            }
        else:
            print(f"❌ Classification failed: {result.error}")
            return {
                "success": False,
                "match": False,
                "error": result.error
            }
            
    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {str(e)[:200]}")
        return {
            "success": False,
            "match": False,
            "error": str(e)
        }


async def main():
    """Run all 3 tests."""
    print("="*70)
    print("OPENROUTER 3-CLAUSE VALIDATION TEST")
    print("="*70)
    print("Testing with improved prompts across different clause types...")
    
    results = []
    for i, clause_data in enumerate(TEST_CLAUSES):
        result = await test_clause(clause_data, i)
        results.append(result)
        await asyncio.sleep(1)  # Brief pause between calls
    
    # Summary
    print(f"\n{'='*70}")
    print("FINAL RESULTS")
    print(f"{'='*70}")
    
    success_count = sum(1 for r in results if r['success'])
    match_count = sum(1 for r in results if r.get('match', False))
    total_tokens = sum(r.get('tokens', 0) for r in results)
    
    print(f"API calls succeeded: {success_count}/3")
    print(f"Exact enum matches: {match_count}/3")
    print(f"Total tokens used: {total_tokens}")
    print()
    
    if match_count == 3:
        print("✅ ALL 3 TESTS PASSED - Prompt fix successful!")
    elif match_count > 0:
        print(f"⚠️  PARTIAL SUCCESS - {match_count}/3 matched, {3-match_count} still invalid")
        for i, r in enumerate(results):
            if not r.get('match', False):
                print(f"  Test {i+1}: Expected '{r.get('expected')}', got '{r.get('returned', 'ERROR')}'")
    else:
        print("❌ ALL TESTS FAILED - Prompt fix insufficient")
    
    print(f"{'='*70}")
    
    sys.exit(0 if match_count == 3 else 1)


if __name__ == "__main__":
    asyncio.run(main())
