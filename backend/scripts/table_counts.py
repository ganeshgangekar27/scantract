"""
Print table counts and contracts state for DB snapshot.
"""
import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return
    
    # Don't print the URL (contains password)
    print("=== TABLE COUNTS ===")
    
    engine = create_async_engine(database_url, echo=False)
    
    async with engine.connect() as conn:
        # Get all tables in public schema
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename
        """))
        tables = [row[0] for row in result]
        
        # Count each table
        for table in tables:
            count_result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.scalar()
            print(f"{table}: {count}")
        
        print("\n=== CONTRACTS TABLE ===")
        contracts_result = await conn.execute(text("""
            SELECT id, pipeline_stage, failed_stage, error_message 
            FROM contracts 
            ORDER BY id
        """))
        
        for row in contracts_result:
            print(f"id={row[0]}, pipeline_stage={row[1]}, failed_stage={row[2]}, error_message={row[3]}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
