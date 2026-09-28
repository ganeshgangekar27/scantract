"""Regenerate missing explanations for contract 1."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

from app.llm.generate_explanations import generate_all_explanations

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:devpass@db:5432/scantract")


async def main():
    """Regenerate missing explanations for contract 1."""
    print("=" * 80)
    print("REGENERATING MISSING EXPLANATIONS FOR CONTRACT 1")
    print("=" * 80)
    
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            count = await generate_all_explanations(1, db)
            print(f"\n✓ Success! Generated {count} explanations")
        except Exception as e:
            print(f"\n✗ Failed: {e}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
