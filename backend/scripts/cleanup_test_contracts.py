"""
Clean up leftover test contract data (IDs 90000-99999) from scantract_test.
"""
import asyncio
import sys
from pathlib import Path
import logging

logging.disable(logging.CRITICAL)

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from app.db.models import Contract, RiskFinding, Clause
from tests.db_config import get_test_database_url


async def cleanup():
    TEST_DATABASE_URL = get_test_database_url()
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Verify we're connected to test database
        result = await session.execute(text("SELECT current_database()"))
        db_name = result.scalar()
        assert db_name.endswith('_test'), f"Safety check failed: connected to {db_name}, not a _test database"
        
        # Delete test data in correct order (FK dependencies)
        # Contract IDs 90000-99999 are reserved for tests
        await session.execute(
            delete(RiskFinding).where(RiskFinding.contract_id.between(90000, 99999))
        )
        await session.execute(
            delete(Clause).where(Clause.contract_id.between(90000, 99999))
        )
        await session.execute(
            delete(Contract).where(Contract.id.between(90000, 99999))
        )
        await session.commit()
        print("Cleanup complete")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(cleanup())
