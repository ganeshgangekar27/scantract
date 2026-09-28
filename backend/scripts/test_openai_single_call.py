"""
Standalone script to test OpenAI provider with exactly ONE real API call.

Tests that the provider is correctly wired up without burning quota on a full contract.
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
print("="*70)
print("OPENAI SINGLE-CALL SMOKE TEST")
print("="*70)
print(f"Loading .env from: {Path(__file__).parent / '.env'}")
load_dotenv()

# Verify provider configuration
provider = os.getenv("LLM_PROVIDER")
openai_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

print(f"\nConfiguration:")
print(f"  LLM_PROVIDER: {provider}")
print(f"  OPENAI_API_KEY: {'SET (length: ' + str(len(openai_key)) + ')' if openai_key else 'NOT SET'}")
print(f"  OPENAI_MODEL: {openai_model}")
print()

if provider != "openai":
    print(f"❌ ERROR: LLM_PROVIDER is '{provider}', expected 'openai'")
    sys.exit(1)

if not openai_key:
    print("❌ ERROR: OPENAI_API_KEY not set in .env")
    sys.exit(1)

print("✓ Configuration valid\n")

# Import after env is loaded
from app.llm.classify_clauses import classify_clause

# Test clause: realistic rental contract late fee clause
TEST_CLAUSE = """
Late Payment: If the monthly rent is not received by the 5th day of the month, 
a late fee of $50 will be charged for each month the payment is overdue.
"""

print("="*70)
print("TEST CLAUSE:")
print("="*70)
print(TEST_CLAUSE.strip())
print()

async def test_single_call():
    """Make exactly one call to OpenAI."""
    print("="*70)
    print("MAKING REAL API CALL TO OPENAI...")
    print("="*70)
    
    start_time = datetime.now()
    
    try:
        result = await classify_clause(
            clause_text=TEST_CLAUSE,
            clause_index="test_1",
            contract_type="rental",
            retrieved_context=""
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n✅ API call succeeded in {duration:.2f} seconds\n")
        
        print("="*70)
        print("CLASSIFICATION RESULT:")
        print("="*70)
        
        if result.classification:
            print(f"  clause_type: {result.classification.clause_type}")
            print(f"  confidence: {result.classification.confidence}")
            print(f"  key_entities: {result.classification.key_entities}")
            print(f"  tokens_used: {result.tokens_used}")
            
            if hasattr(result.classification, 'reasoning'):
                print(f"\n  Reasoning:")
                print(f"    {result.classification.reasoning}")
            
            return result
        else:
            print(f"❌ Classification failed with error:")
            print(f"  {result.error}")
            return None
            
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n❌ API call failed after {duration:.2f} seconds\n")
        print("="*70)
        print("ERROR DETAILS:")
        print("="*70)
        print(f"  Exception Type: {type(e).__name__}")
        print(f"  Exception Message: {str(e)}")
        
        import traceback
        print(f"\n  Full Traceback:")
        traceback.print_exc()
        
        raise


async def main():
    """Main entry point."""
    try:
        result = await test_single_call()
        
        if result and result.classification:
            print("\n" + "="*70)
            print("SMOKE TEST PASSED ✅")
            print("="*70)
            print(f"OpenAI provider is correctly wired up.")
            print(f"Classified as: {result.classification.clause_type}")
            print(f"Cost: {result.tokens_used} tokens")
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("SMOKE TEST FAILED ❌")
            print("="*70)
            sys.exit(1)
            
    except Exception as e:
        print("\n" + "="*70)
        print("SMOKE TEST FAILED ❌")
        print("="*70)
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
