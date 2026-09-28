"""Trigger risk detection for contract 1 to test diagnostic logging."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

from app.llm.detect_risk import detect_risks

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:devpass@db:5432/scantract")


async def main():
    """Run risk detection for contract 1."""
    print("=" * 80)
    print("TRIGGERING RISK DETECTION FOR CONTRACT 1")
    print("=" * 80)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            result = await detect_risks(contract_id="1", db=db)
            print(f"\n✓ Success! Detected {result.total_risks} risky clauses, {result.total_missing} missing clauses")
        except Exception as e:
            print(f"\n✗ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
