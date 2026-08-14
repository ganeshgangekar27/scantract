"""
Seed legal knowledge base with sample legal rules.

CRITICAL: This loads SAMPLE DATA for development only.
See seed_data/README.md for production replacement requirements.
"""

import json
import asyncio
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
from db.legal_kb.models import LegalRule, LegalRuleData
from db.legal_kb.embeddings import embed_text
from typing import Optional
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


def load_seed_data() -> list[LegalRuleData]:
    """
    Load legal rules from seed_data/legal_rules.json.
    
    Returns:
        List of validated LegalRuleData objects
    
    Raises:
        FileNotFoundError: If legal_rules.json does not exist
        ValueError: If JSON is invalid or validation fails
    """
    seed_file = Path(__file__).parent / "seed_data" / "legal_rules.json"
    
    if not seed_file.exists():
        raise FileNotFoundError(
            f"Seed data file not found: {seed_file}. "
            f"Ensure legal_rules.json exists in seed_data/ directory."
        )
    
    try:
        with open(seed_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        if not isinstance(raw_data, list):
            raise ValueError("legal_rules.json must contain a JSON array")
        
        # Validate each entry with Pydantic
        legal_rules = [LegalRuleData(**entry) for entry in raw_data]
        
        logger.info(f"Loaded {len(legal_rules)} legal rules from {seed_file}")
        return legal_rules
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in legal_rules.json: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load or validate seed data: {e}")


async def rule_exists(
    db: AsyncSession,
    act_name: str,
    section_reference: str,
    state: Optional[str]
) -> bool:
    """
    Check if a legal rule already exists in the database.
    
    Uses the UNIQUE constraint columns (act_name, section_reference, state)
    to determine if a rule is already present.
    
    Args:
        db: Database session
        act_name: Name of the act
        section_reference: Section reference
        state: State code or None
    
    Returns:
        True if rule exists, False otherwise
    """
    query = select(LegalRule).where(
        and_(
            LegalRule.act_name == act_name,
            LegalRule.section_reference == section_reference,
            LegalRule.state == state if state is not None else LegalRule.state.is_(None)
        )
    )
    
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def seed_legal_kb():
    """
    Main function to seed legal knowledge base.
    
    Loads rules from legal_rules.json, generates embeddings, and inserts
    into database. Idempotent - skips rules that already exist.
    """
    # Log SAMPLE DATA warning banner
    print("\n" + "=" * 60)
    print("WARNING: Loading SAMPLE legal data for development only")
    print("=" * 60)
    logger.warning("SAMPLE DATA: Not suitable for production use")
    logger.warning("See backend/db/legal_kb/seed_data/README.md for details")
    print("=" * 60 + "\n")
    
    # Load seed data
    try:
        legal_rules = load_seed_data()
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
        for rule_data in legal_rules:
            try:
                # Check if rule already exists (idempotency)
                exists = await rule_exists(
                    db,
                    rule_data.act_name,
                    rule_data.section_reference,
                    rule_data.state
                )
                
                if exists:
                    logger.info(
                        f"Skipping existing rule: {rule_data.act_name} "
                        f"{rule_data.section_reference} (state={rule_data.state})"
                    )
                    skipped += 1
                    continue
                
                # Generate embedding
                logger.info(
                    f"Embedding rule: {rule_data.act_name} "
                    f"{rule_data.section_reference} (state={rule_data.state})"
                )
                embedding = await embed_text(rule_data.rule_text)
                
                # Create LegalRule with embedding
                legal_rule = LegalRule(
                    state=rule_data.state,
                    act_name=rule_data.act_name,
                    section_reference=rule_data.section_reference,
                    rule_text=rule_data.rule_text,
                    embedding=embedding
                )
                
                db.add(legal_rule)
                inserted += 1
                
                logger.info(
                    f"Inserted rule: {rule_data.act_name} "
                    f"{rule_data.section_reference}"
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to process rule {rule_data.act_name} "
                    f"{rule_data.section_reference}: {e}"
                )
                failed += 1
                continue
        
        # Commit all insertions
        if inserted > 0:
            try:
                await db.commit()
                logger.info(f"Committed {inserted} new rules to database")
            except Exception as e:
                logger.error(f"Failed to commit changes: {e}")
                await db.rollback()
                sys.exit(1)
    
    # Log final summary
    print("\n" + "=" * 60)
    print("Legal KB seeding complete:")
    print(f"  - Inserted: {inserted} rules")
    print(f"  - Skipped (already exist): {skipped} rules")
    print(f"  - Failed: {failed} rules")
    print("=" * 60)
    
    logger.info(
        f"Seeding summary: {inserted} inserted, {skipped} skipped, {failed} failed"
    )
    
    # VACUUM ANALYZE reminder
    if inserted > 0:
        print("\n" + "!" * 60)
        print("REMINDER: Run 'VACUUM ANALYZE legal_rules;' to optimize")
        print("the IVFFlat index for better similarity search performance.")
        print("!" * 60 + "\n")
        logger.warning(
            "Run 'VACUUM ANALYZE legal_rules;' to optimize IVFFlat index"
        )
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_legal_kb())

