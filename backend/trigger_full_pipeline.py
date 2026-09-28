"""Trigger full pipeline (risk detection + explanation generation) for contract 1."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

from app.document_processing.orchestrator import _run_risk_detection_stage, _run_explanation_stage
from app.db.models import Contract
from sqlalchemy import select

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:devpass@db:5432/scantract")


async def main():
    """Run risk detection + explanation generation for contract 1."""
    print("=" * 80)
    print("TRIGGERING FULL PIPELINE FOR CONTRACT 1 (Risk Detection + Explanations)")
    print("=" * 80)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # Load contract
            result = await db.execute(select(Contract).where(Contract.id == 1))
            contract = result.scalar_one()
            
            print(f"Current pipeline_stage: {contract.pipeline_stage}")
            
            # Run risk detection
            print("\n--- Stage 7: Risk Detection ---")
            await _run_risk_detection_stage(contract, db)
            print(f"✓ Risk detection complete. Stage now: {contract.pipeline_stage}")
            
            # Run explanation generation
            print("\n--- Stage 8: Explanation Generation ---")
            await _run_explanation_stage(contract, db)
            print(f"✓ Explanation generation complete. Stage now: {contract.pipeline_stage}")
            
            # Mark as completed
            contract.pipeline_stage = 'completed'
            await db.commit()
            
            print(f"\n✓ Success! Full pipeline completed. Final stage: {contract.pipeline_stage}")
            
        except Exception as e:
            print(f"\n✗ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
