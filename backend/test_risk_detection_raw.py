"""
Standalone script to reproduce the exact risk detection call that failed.
Prints the raw LLM response before any JSON parsing.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.db.models import Clause
from app.rag.merge_context import merge_retrieval_results, format_merged_context
from app.rag.prompt_builder import build_risk_prompt
from db.legal_kb.search import search_legal_rules
from db.reference_corpus.search import search_reference_corpus
from app.llm.llm_client import call_llm

# Load environment
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:devpass@db:5432/scantract")


async def main():
    """Reproduce the risk detection call for contract 1."""
    print("=" * 80)
    print("REPRODUCING RISK DETECTION CALL FOR CONTRACT 1")
    print("=" * 80)
    
    # Connect to DB
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Load classified clauses
        result = await db.execute(
            select(Clause).where(Clause.contract_id == 1).order_by(Clause.position)
        )
        clauses = result.scalars().all()
        
        print(f"\nLoaded {len(clauses)} clauses from contract 1")
        
        # Retrieve context for each clause (capped at 10 like the real run)
        all_legal = []
        all_corpus = []
        
        for i, clause in enumerate(clauses[:10], 1):
            print(f"\nClause {i}: Retrieving context...")
            
            # Search legal KB
            legal_results = await search_legal_rules(
                clause_text=clause.text,
                db=db,
                state=None,
                top_k=3,
                similarity_threshold=0.7
            )
            all_legal.extend(legal_results)
            print(f"  - Legal rules: {len(legal_results)} results")
            
            # Search reference corpus
            corpus_results = await search_reference_corpus(
                clause_text=clause.text,
                contract_type='rental',
                db=db,
                top_k=3,
                similarity_threshold=0.7
            )
            all_corpus.extend(corpus_results)
            print(f"  - Reference corpus: {len(corpus_results)} results")
        
        # Merge and rank context
        print(f"\nMerging context: {len(all_legal)} legal + {len(all_corpus)} corpus")
        merge_result = merge_retrieval_results(all_legal, all_corpus, max_chunks=20)
        context_chunks = merge_result.chunks
        print(f"Merged to {len(context_chunks)} chunks")
        
        # Build the risk detection prompt
        print("\nBuilding risk detection prompt...")
        
        # Format clauses for prompt (as list of dicts)
        clauses_list = [
            {
                "clause_id": c.clause_id,
                "clause_type": c.clause_type or "unknown",
                "clause_text": c.text
            }
            for c in clauses
        ]
        
        # Format retrieved context
        context_text = format_merged_context(merge_result)
        
        # Build prompt using the actual function
        messages = build_risk_prompt(
            clauses_list=clauses_list,
            retrieved_context=context_text,
            contract_type='rental'
        )
        
        prompt = messages[0]["content"]
        print(f"Prompt length: {len(prompt)} characters")
        
        # Call LLM (same as the real run)
        print("\n" + "=" * 80)
        print("CALLING LLM (OpenRouter)...")
        print("=" * 80)
        
        try:
            response_text = await call_llm(
                messages=messages,
                temperature=0.3,
                max_tokens=4000
            )
            
            print("\n" + "=" * 80)
            print("RAW LLM RESPONSE (BEFORE ANY PARSING):")
            print("=" * 80)
            print(response_text)
            print("=" * 80)
            print(f"\nResponse length: {len(response_text)} characters")
            print(f"First 50 chars: {repr(response_text[:50])}")
            print(f"Last 50 chars: {repr(response_text[-50:])}")
            
        except Exception as e:
            print(f"\nERROR calling LLM: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
