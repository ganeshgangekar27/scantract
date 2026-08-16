"""
Seed reference corpus with sample reference contract clauses.

CRITICAL: This loads SAMPLE DATA for development only.
See seed_data/README.md for production replacement requirements.
"""

import json
import asyncio
import logging
import hashlib
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_, func
from db.reference_corpus.models import ReferenceClause, ReferenceClauseData
from rag.embeddings import embed_batch
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_seed_data() -> list[ReferenceClauseData]:
    """
    Load reference clauses from seed_data/reference_clauses.json.
    
    Returns:
        List of validated ReferenceClauseData objects
    
    Raises:
        FileNotFoundError: If reference_clauses.json does not exist
        ValueError: If JSON is invalid or validation fails
    """
    seed_file = Path(__file__).parent / "seed_data" / "reference_clauses.json"
    
    if not seed_file.exists():
        raise FileNotFoundError(
            f"Seed data file not found: {seed_file}. "
            f"Ensure reference_clauses.json exists in seed_data/ directory."
        )
    
    try:
        with open(seed_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        if not isinstance(raw_data, list):
            raise ValueError("reference_clauses.json must contain a JSON array")
        
        # Validate each entry with Pydantic
        reference_clauses = [ReferenceClauseData(**entry) for entry in raw_data]
        
        logger.info(f"Loaded {len(reference_clauses)} reference clauses from {seed_file}")
        return reference_clauses
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in reference_clauses.json: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load or validate seed data: {e}")


def clause_hash(contract_type: str, clause_category: str, clause_text: str) -> str:
    """
    Generate MD5 hash for unique constraint matching.
    
    This matches the unique constraint: 
    UNIQUE (contract_type, clause_category, MD5(clause_text))
    
    Args:
        contract_type: Contract type
        clause_category: Clause category
        clause_text: Clause text
    
    Returns:
        MD5 hash as hexadecimal string
    """
    return hashlib.md5(clause_text.encode('utf-8')).hexdigest()


async def clause_exists(
    db: AsyncSession,
    contract_type: str,
    clause_category: str,
    clause_text: str
) -> bool:
    """
    Check if a reference clause already exists in the database.
    
    Uses the UNIQUE constraint columns (contract_type, clause_category, MD5(clause_text))
    to determine if a clause is already present.
    
    Args:
        db: Database session
        contract_type: Contract type
        clause_category: Clause category
        clause_text: Clause text
    
    Returns:
        True if clause exists, False otherwise
    """
    # Generate MD5 hash of clause text
    text_hash = clause_hash(contract_type, clause_category, clause_text)
    
    # Query using MD5 function to match database constraint
    query = select(ReferenceClause).where(
        and_(
            ReferenceClause.contract_type == contract_type,
            ReferenceClause.clause_category == clause_category,
            func.md5(ReferenceClause.clause_text) == text_hash
        )
    )
    
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def seed_reference_corpus():
    """
    Main function to seed reference corpus.
    
    Loads clauses from reference_clauses.json, generates embeddings in batch,
    and inserts into database. Idempotent - skips clauses that already exist.
    """
    # Log SAMPLE DATA warning banner
    print("\n" + "=" * 70)
    print("⚠️  WARNING: Loading SAMPLE reference data for development only ⚠️")
    print("=" * 70)
    logger.warning("SAMPLE DATA: Not suitable for production use")
    logger.warning("See backend/db/reference_corpus/seed_data/README.md for details")
    print("=" * 70 + "\n")
    
    # Load seed data
    try:
        reference_clauses = load_seed_data()
    except Exception as e:
        logger.error(f"Failed to load seed data: {e}")
        sys.exit(1)
    
    # Create database connection
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/scantract"
    )
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Counters
    inserted = 0
    skipped = 0
    failed = 0
    
    async with async_session() as db:
        # Check which clauses already exist (idempotency)
        clauses_to_insert = []
        clause_data_to_insert = []
        
        for clause_data in reference_clauses:
            try:
                exists = await clause_exists(
                    db,
                    clause_data.contract_type,
                    clause_data.clause_category,
                    clause_data.clause_text
                )
                
                if exists:
                    logger.info(
                        f"Skipping existing clause: {clause_data.contract_type} / "
                        f"{clause_data.clause_category}"
                    )
                    skipped += 1
                else:
                    clauses_to_insert.append(clause_data)
                    clause_data_to_insert.append(clause_data)
                    
            except Exception as e:
                logger.error(
                    f"Error checking clause existence: {clause_data.contract_type} / "
                    f"{clause_data.clause_category}: {e}"
                )
                failed += 1
        
        # Generate embeddings in batch for new clauses
        if clauses_to_insert:
            logger.info(f"Generating embeddings for {len(clauses_to_insert)} new clauses...")
            
            try:
                # Extract clause texts for batch embedding
                clause_texts = [clause.clause_text for clause in clauses_to_insert]
                
                # Generate embeddings in batch
                embeddings = await embed_batch(clause_texts, batch_size=100)
                
                logger.info(f"Successfully generated {len(embeddings)} embeddings")
                
                # Create ReferenceClause objects with embeddings
                for clause_data, embedding in zip(clauses_to_insert, embeddings):
                    try:
                        reference_clause = ReferenceClause(
                            contract_type=clause_data.contract_type,
                            clause_category=clause_data.clause_category,
                            clause_text=clause_data.clause_text,
                            source_label=clause_data.source_label,
                            embedding=embedding
                        )
                        
                        db.add(reference_clause)
                        inserted += 1
                        
                        logger.info(
                            f"Prepared clause for insertion: {clause_data.contract_type} / "
                            f"{clause_data.clause_category}"
                        )
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to create clause object: {clause_data.contract_type} / "
                            f"{clause_data.clause_category}: {e}"
                        )
                        failed += 1
                        continue
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
                sys.exit(1)
        
        # Commit all insertions
        if inserted > 0:
            try:
                await db.commit()
                logger.info(f"Committed {inserted} new clauses to database")
            except Exception as e:
                logger.error(f"Failed to commit changes: {e}")
                await db.rollback()
                sys.exit(1)
    
    # Log final summary
    print("\n" + "=" * 70)
    print("Reference corpus seeding complete:")
    print(f"  ✓ Inserted: {inserted} clauses")
    print(f"  ⊘ Skipped (already exist): {skipped} clauses")
    print(f"  ✗ Failed: {failed} clauses")
    print("=" * 70)
    
    logger.info(
        f"Seeding summary: {inserted} inserted, {skipped} skipped, {failed} failed"
    )
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_reference_corpus())

