"""
Database session management for ScanTract backend.

Provides async database session factory and dependency injection for FastAPI.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

from db_url_utils import to_async_url, is_pooler_url

# Load environment variables
load_dotenv()

# Database URL from environment
raw_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/scantract")
DATABASE_URL = to_async_url(raw_url)

# Detect pgbouncer (pooler hostname) and disable statement cache if needed
connect_args = {}
if is_pooler_url(DATABASE_URL):
    connect_args["statement_cache_size"] = 0

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides database session.
    
    Yields:
        AsyncSession: Database session
        
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
