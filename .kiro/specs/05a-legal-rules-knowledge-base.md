# Spec: Indian Legal Rules Knowledge Base

## Overview
Build the Indian legal rules knowledge base for ScanTract — Stage 5A of the core pipeline that stores verified legal provisions, enables semantic search via pgvector embeddings, and provides context for clause risk assessment. This KB contains rules from Indian rental/freelance law that clauses are compared against.

## Scope
- PostgreSQL pgvector extension setup
- `legal_rules` table schema with vector embeddings
- Seed data: 15-20 sample entries from Model Tenancy Act and related provisions
- Embedding generation using consistent model (OpenAI text-embedding-3-small)
- Semantic search via pgvector cosine similarity
- State-filtered queries (e.g., Maharashtra-specific rules)
- Seed script for loading initial data
- Unit tests with test database

## Requirements

### Functional Requirements

**FR-1: Database Schema**
- Table: `legal_rules`
- Columns:
  - `id`: UUID primary key
  - `state`: VARCHAR(100), nullable (NULL = central/all-India acts)
  - `act_name`: VARCHAR(255), not null (e.g., "Model Tenancy Act 2021")
  - `section_reference`: VARCHAR(100), not null (e.g., "Section 7(1)")
  - `rule_text`: TEXT, not null (the actual legal provision)
  - `embedding`: VECTOR(1536) (pgvector embedding for semantic search)
  - `created_at`: TIMESTAMP
  - `updated_at`: TIMESTAMP
- Indexes on state, act_name, and vector similarity

**FR-2: pgvector Extension**
- Enable pgvector extension in PostgreSQL
- Support for vector similarity search (cosine distance)
- Vector dimension: 1536 (OpenAI text-embedding-3-small)


**FR-3: Seed Data**
- Location: `backend/db/legal_kb/seed_data/legal_rules.json`
- 15-20 realistic sample entries covering:
  - Model Tenancy Act 2021 provisions
  - Security deposit limits (central and state-specific)
  - Notice period requirements
  - Maintenance obligations
  - Rent increase caps
  - Eviction grounds
- Clearly marked as **SAMPLE DATA** — must be replaced with verified legal text
- JSON structure: array of rule objects with all required fields

**FR-4: Embedding Generation**
- Function: `embed_and_store(rule_text) -> list[float]`
- Use OpenAI `text-embedding-3-small` model (1536 dimensions)
- Consistent with Stage 5B (corpus embeddings) for comparability
- Cache embeddings to avoid redundant API calls
- Error handling for API failures

**FR-5: Semantic Search**
- Function: `search_legal_rules(clause_text, state=None, contract_type=None, top_k=5)`
- Embed query clause using same model
- Search via pgvector cosine similarity
- Filter by state when provided (NULL state = applicable everywhere)
- Return top-k most similar rules with similarity scores
- Include rule metadata (act_name, section_reference)

**FR-6: Seed Script**
- Script: `backend/db/legal_kb/seed_legal_kb.py`
- Load rules from JSON file
- Generate embeddings for each rule
- Insert into database with batch commits
- Idempotent: skip already-seeded rules (check by section_reference + act_name)
- CLI: `python -m backend.db.legal_kb.seed_legal_kb`

**FR-7: State Filtering Logic**
- If state provided: return state-specific rules + central rules (state IS NULL)
- If state NULL: return only central rules
- Rationale: Central acts apply everywhere, state acts override/supplement


### Non-Functional Requirements

**NFR-1: Performance**
- Vector search completes in <100ms for top-k=5
- Seed script processes 100 rules in <2 minutes (including embeddings)
- Embedding generation: <500ms per rule (network-bound)

**NFR-2: Accuracy**
- Cosine similarity threshold: only return rules with score >0.7
- Embedding model consistent across all vector searches in system
- Vector normalization for accurate similarity comparison

**NFR-3: Data Quality**
- Sample data representative of real legal provisions
- Clear attribution of act name and section
- Proper legal citation format
- Warning label on sample data

**NFR-4: Type Safety**
- All functions use type hints (Python 3.11+)
- Pydantic models for legal rules
- SQLAlchemy models with proper types

**NFR-5: Maintainability**
- Seed data in human-readable JSON (not code)
- Easy to add new rules without code changes
- Clear separation: data vs logic

## Technical Design

### Module Structure

**Location:** `backend/db/legal_kb/`

```
backend/db/legal_kb/
├── __init__.py
├── models.py              # SQLAlchemy model for legal_rules
├── embeddings.py          # Embedding generation
├── search.py              # Semantic search functions
├── seed_legal_kb.py       # Seed script (CLI)
└── seed_data/
    ├── legal_rules.json   # Sample legal rules
    └── README.md          # Data disclaimer and instructions
```


### Database Schema Design

**Alembic Migration:** `backend/alembic/versions/003_create_legal_rules_kb.py`

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create legal_rules table
CREATE TABLE legal_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    state VARCHAR(100),  -- NULL = central act, applies to all states
    act_name VARCHAR(255) NOT NULL,
    section_reference VARCHAR(100) NOT NULL,
    rule_text TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,  -- OpenAI text-embedding-3-small
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique rules
    UNIQUE(act_name, section_reference, state)
);

-- Indexes for performance
CREATE INDEX idx_legal_rules_state ON legal_rules(state);
CREATE INDEX idx_legal_rules_act_name ON legal_rules(act_name);

-- Vector similarity index (IVFFlat for performance)
CREATE INDEX idx_legal_rules_embedding ON legal_rules 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Enable faster similarity search
-- Note: IVFFlat requires VACUUM ANALYZE after bulk inserts
```

**SQLAlchemy Model (backend/db/legal_kb/models.py):**

```python
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

from ..base import Base

class LegalRule(Base):
    __tablename__ = "legal_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(String(100), nullable=True)  # NULL = central act
    act_name = Column(String(255), nullable=False)
    section_reference = Column(String(100), nullable=False)
    rule_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<LegalRule {self.act_name} {self.section_reference}>"
```


### Pydantic Models

**File: backend/db/legal_kb/models.py (continued)**

```python
from pydantic import BaseModel, Field
from typing import Optional

class LegalRuleData(BaseModel):
    """Data structure for seed data."""
    state: Optional[str] = None
    act_name: str
    section_reference: str
    rule_text: str

class LegalRuleSearchResult(BaseModel):
    """Search result with similarity score."""
    id: str
    state: Optional[str]
    act_name: str
    section_reference: str
    rule_text: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    
    class Config:
        from_attributes = True
```

### Embedding Generation

**File: backend/db/legal_kb/embeddings.py**

```python
import os
from openai import AsyncOpenAI
from typing import List
import asyncio

_openai_client = None

def get_openai_client() -> AsyncOpenAI:
    """Lazy-load OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client

async def embed_text(text: str) -> List[float]:
    """
    Generate embedding for text using OpenAI text-embedding-3-small.
    
    Args:
        text: Text to embed
    
    Returns:
        1536-dimensional embedding vector
    
    Raises:
        RuntimeError: If embedding generation fails
    """
    client = get_openai_client()
    
    try:
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"
        )
        
        embedding = response.data[0].embedding
        
        if len(embedding) != 1536:
            raise ValueError(f"Expected 1536 dimensions, got {len(embedding)}")
        
        return embedding
        
    except Exception as e:
        raise RuntimeError(f"Embedding generation failed: {e}")

async def embed_batch(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """
    Embed multiple texts in batches.
    
    Args:
        texts: List of texts to embed
        batch_size: Max texts per API call (OpenAI limit: 2048)
    
    Returns:
        List of embedding vectors
    """
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_embeddings = await asyncio.gather(*[embed_text(t) for t in batch])
        embeddings.extend(batch_embeddings)
    
    return embeddings
```


### Semantic Search

**File: backend/db/legal_kb/search.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Optional
import logging

from .models import LegalRule, LegalRuleSearchResult
from .embeddings import embed_text

logger = logging.getLogger(__name__)

async def search_legal_rules(
    clause_text: str,
    state: Optional[str] = None,
    contract_type: Optional[str] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.7,
    db: AsyncSession = None
) -> List[LegalRuleSearchResult]:
    """
    Search legal rules by semantic similarity.
    
    Args:
        clause_text: Clause to find relevant rules for
        state: Filter by state (None = only central rules)
        contract_type: "rental" or "freelance" (for future filtering)
        top_k: Number of results to return
        similarity_threshold: Minimum cosine similarity (0.0-1.0)
        db: Database session
    
    Returns:
        List of matching legal rules with similarity scores
    """
    # Generate embedding for query clause
    try:
        query_embedding = await embed_text(clause_text)
    except Exception as e:
        logger.error(f"Failed to embed query clause: {e}")
        return []
    
    # Build query with state filtering
    # Logic: If state provided, return state-specific + central rules
    #        If state NULL, return only central rules
    query = select(
        LegalRule,
        LegalRule.embedding.cosine_distance(query_embedding).label("distance")
    )
    
    if state:
        # Include state-specific AND central rules
        query = query.where(
            or_(
                LegalRule.state == state,
                LegalRule.state.is_(None)
            )
        )
    else:
        # Only central rules
        query = query.where(LegalRule.state.is_(None))
    
    # Order by similarity (lowest distance = highest similarity)
    query = query.order_by("distance").limit(top_k)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to search results with similarity scores
    search_results = []
    for rule, distance in rows:
        # Convert cosine distance to similarity: similarity = 1 - distance
        similarity = 1.0 - distance
        
        if similarity >= similarity_threshold:
            search_results.append(LegalRuleSearchResult(
                id=str(rule.id),
                state=rule.state,
                act_name=rule.act_name,
                section_reference=rule.section_reference,
                rule_text=rule.rule_text,
                similarity_score=round(similarity, 4)
            ))
    
    logger.info(
        f"Found {len(search_results)} legal rules above threshold "
        f"{similarity_threshold} for state={state}"
    )
    
    return search_results
```


### Seed Data Structure

**File: backend/db/legal_kb/seed_data/legal_rules.json**

```json
[
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 7(1)",
    "rule_text": "The security deposit shall not exceed an amount equivalent to two months' rent in case of residential properties and six months' rent in case of non-residential properties."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 21(1)",
    "rule_text": "The landlord shall give written notice of at least three months before terminating the tenancy agreement, unless otherwise agreed upon in writing by both parties."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 13(1)",
    "rule_text": "The landlord shall be responsible for structural repairs and maintenance of the premises, including repairs to the roof, walls, foundation, and permanent fixtures."
  },
  {
    "state": "Maharashtra",
    "act_name": "Maharashtra Rent Control Act 1999",
    "section_reference": "Section 11(2)",
    "rule_text": "In Mumbai Metropolitan Region, the security deposit for residential premises shall not exceed three months' rent, and for non-residential premises shall not exceed six months' rent."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 8(1)",
    "rule_text": "The rent shall be payable monthly in advance before the 10th day of each month, unless otherwise specified in the tenancy agreement."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 9(1)",
    "rule_text": "The annual increase in rent shall not exceed eight percent of the existing rent, unless mutually agreed upon in writing."
  },
  {
    "state": null,
    "act_name": "Indian Contract Act 1872",
    "section_reference": "Section 73",
    "rule_text": "When a contract has been broken, the party who suffers by such breach is entitled to receive compensation for any loss or damage caused to him thereby, which naturally arose in the usual course of things from such breach."
  }
]
```

**DISCLAIMER (backend/db/legal_kb/seed_data/README.md):**
```markdown
# Legal Rules Seed Data

⚠️ **IMPORTANT: SAMPLE DATA ONLY**

The rules in `legal_rules.json` are SAMPLE DATA for development and testing purposes only.
They are NOT verified legal provisions and must NOT be used in production.

Before deploying ScanTract for real use:
1. Replace all sample data with verified legal provisions
2. Obtain legal review from qualified legal professionals
3. Ensure citations are accurate and current
4. Verify state-specific variations
5. Check for recent amendments to cited acts

## Data Sources (for production replacement)

- Model Tenancy Act 2021: https://prsindia.org/
- State-specific rent control acts
- Indian Contract Act 1872
- Legal databases: Manupatra, SCC Online, etc.

## Adding New Rules

Rules should include:
- `state`: State code (NULL for central acts)
- `act_name`: Full name of the act
- `section_reference`: Section/subsection reference
- `rule_text`: The actual legal provision (verbatim from source)
```


### Complete Sample Data (15-20 Entries)

**Additional entries for legal_rules.json:**

```json
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 14(1)",
    "rule_text": "The tenant shall use the premises only for the purpose specified in the tenancy agreement and shall not sublet or assign the premises without prior written consent of the landlord."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 15(2)",
    "rule_text": "The tenant shall be responsible for day-to-day maintenance including replacement of light bulbs, cleaning, and minor repairs that do not affect the structural integrity of the premises."
  },
  {
    "state": "Karnataka",
    "act_name": "Karnataka Rent Control Act 2001",
    "section_reference": "Section 4(1)",
    "rule_text": "In Bengaluru Urban district, the standard rent for residential premises shall be calculated at the rate of 10% per annum of the aggregate amount of the cost of construction and market value of the land."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 22(2)",
    "rule_text": "The landlord may evict the tenant if the tenant fails to pay rent for two consecutive months despite receiving written notice of default."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 19(1)",
    "rule_text": "Either party may renew the tenancy agreement upon mutual consent before the expiry of the existing agreement. The terms of renewal shall be agreed upon in writing."
  },
  {
    "state": "Delhi",
    "act_name": "Delhi Rent Control Act 1958",
    "section_reference": "Section 6",
    "rule_text": "No tenant shall be evicted from any premises except in accordance with the provisions of this Act, and on one or more of the grounds specified in Section 14."
  },
  {
    "state": null,
    "act_name": "Indian Contract Act 1872",
    "section_reference": "Section 74",
    "rule_text": "When a contract contains a penalty clause, the party complaining of breach is entitled to receive reasonable compensation not exceeding the amount named in the penalty clause."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 12(1)",
    "rule_text": "The landlord shall ensure that the premises are in habitable condition at the time of handover and shall provide essential services including water supply and drainage."
  }
```


```json
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 16(1)",
    "rule_text": "The tenant shall permit the landlord or his authorized agent to inspect the premises at reasonable times upon giving at least 24 hours prior notice."
  },
  {
    "state": "Tamil Nadu",
    "act_name": "Tamil Nadu Buildings (Lease and Rent Control) Act 1960",
    "section_reference": "Section 10",
    "rule_text": "The annual rent increase in Tamil Nadu shall not exceed fifteen percent of the existing rent for residential buildings and twenty percent for non-residential buildings."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 23(1)",
    "rule_text": "Upon termination of tenancy, the landlord shall return the security deposit within one month after deducting any dues for unpaid rent, damages, or repairs attributable to the tenant."
  },
  {
    "state": null,
    "act_name": "Indian Contract Act 1872",
    "section_reference": "Section 56",
    "rule_text": "A contract to do an act which, after the contract is made, becomes impossible or unlawful, becomes void when the act becomes impossible or unlawful. This includes situations of force majeure."
  },
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 20(1)",
    "rule_text": "The tenant shall be liable for any damage to the premises caused by negligence, misuse, or willful act of the tenant or any person residing with or visiting the tenant."
  }
```

**Total: 20 sample rules covering:**
- Security deposit limits (central + state-specific)
- Notice periods for termination
- Maintenance obligations (landlord vs tenant)
- Rent payment terms and increase caps
- Eviction grounds
- Subletting restrictions
- Inspection rights
- Security deposit refund
- Force majeure (Indian Contract Act)
- State-specific variations (Maharashtra, Karnataka, Delhi, Tamil Nadu)


### Seed Script

**File: backend/db/legal_kb/seed_legal_kb.py**

```python
#!/usr/bin/env python3
"""
Seed the legal rules knowledge base.

Usage:
    python -m backend.db.legal_kb.seed_legal_kb
    
Environment:
    Requires OPENAI_API_KEY for embedding generation
"""

import asyncio
import json
import sys
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..database import get_async_session
from .models import LegalRule, LegalRuleData
from .embeddings import embed_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_DATA_PATH = Path(__file__).parent / "seed_data" / "legal_rules.json"

async def load_seed_data() -> list[LegalRuleData]:
    """Load seed data from JSON file."""
    if not SEED_DATA_PATH.exists():
        raise FileNotFoundError(f"Seed data not found: {SEED_DATA_PATH}")
    
    with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return [LegalRuleData(**item) for item in data]

async def rule_exists(
    db: AsyncSession,
    act_name: str,
    section_reference: str,
    state: str | None
) -> bool:
    """Check if rule already exists in database."""
    query = select(LegalRule).where(
        LegalRule.act_name == act_name,
        LegalRule.section_reference == section_reference,
        LegalRule.state == state
    )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None

async def seed_legal_kb():
    """Main seeding function."""
    logger.info("=" * 60)
    logger.info("⚠️  SAMPLE DATA WARNING")
    logger.info("This seed data is for DEVELOPMENT ONLY.")
    logger.info("DO NOT use in production without legal verification.")
    logger.info("=" * 60)
    
    # Load seed data
    logger.info(f"Loading seed data from {SEED_DATA_PATH}")
    rules_data = await load_seed_data()
    logger.info(f"Loaded {len(rules_data)} rules")
    
    # Get database session
    async for db in get_async_session():
        inserted = 0
        skipped = 0
        failed = 0
        
        for rule_data in rules_data:
            try:
                # Check if rule already exists (idempotent)
                if await rule_exists(
                    db,
                    rule_data.act_name,
                    rule_data.section_reference,
                    rule_data.state
                ):
                    logger.debug(
                        f"Skipping existing rule: {rule_data.act_name} "
                        f"{rule_data.section_reference}"
                    )
                    skipped += 1
                    continue
                
                # Generate embedding
                logger.info(
                    f"Embedding: {rule_data.act_name} {rule_data.section_reference}"
                )
                embedding = await embed_text(rule_data.rule_text)
                
                # Create and insert rule
                rule = LegalRule(
                    state=rule_data.state,
                    act_name=rule_data.act_name,
                    section_reference=rule_data.section_reference,
                    rule_text=rule_data.rule_text,
                    embedding=embedding
                )
                
                db.add(rule)
                inserted += 1
                
                logger.info(
                    f"✓ Inserted: {rule_data.act_name} {rule_data.section_reference}"
                )
                
            except Exception as e:
                logger.error(
                    f"✗ Failed to insert {rule_data.act_name} "
                    f"{rule_data.section_reference}: {e}"
                )
                failed += 1
        
        # Commit all insertions
        await db.commit()
        
        logger.info("=" * 60)
        logger.info(f"Seeding complete:")
        logger.info(f"  Inserted: {inserted}")
        logger.info(f"  Skipped:  {skipped}")
        logger.info(f"  Failed:   {failed}")
        logger.info("=" * 60)
        
        if inserted > 0:
            logger.info("Run VACUUM ANALYZE to optimize vector index:")
            logger.info("  psql -c 'VACUUM ANALYZE legal_rules;'")
        
        break  # Exit async generator

if __name__ == "__main__":
    asyncio.run(seed_legal_kb())
```


## Test Plan

### Test Strategy

**Test Database:**
- Use pytest fixtures with test-specific database
- Small subset of seed data (5-10 rules)
- In-memory or temporary PostgreSQL instance with pgvector

### Test Cases

**Test File:** `backend/tests/test_legal_kb.py`

**TC-1: Database Schema - pgvector Extension**
- Verify pgvector extension enabled
- Verify VECTOR type available
- Verify can create vector columns

**TC-2: Database Schema - legal_rules Table**
- Verify table exists with correct columns
- Verify indexes created (state, act_name, embedding)
- Verify UNIQUE constraint on (act_name, section_reference, state)

**TC-3: Embedding Generation - Single Text**
- Call `embed_text("Sample legal text")`
- Verify returns list of 1536 floats
- Verify values in reasonable range (-1.0 to 1.0)

**TC-4: Embedding Generation - Batch**
- Call `embed_batch(["text1", "text2", "text3"])`
- Verify returns 3 embeddings
- Verify each is 1536 dimensions

**TC-5: Embedding Generation - Error Handling**
- Unset OPENAI_API_KEY
- Verify ValueError raised
- Restore key and verify recovery

**TC-6: Seed Script - Load Data**
- Run seed script with test data (5 rules)
- Verify all 5 rules inserted
- Verify embeddings generated and stored

**TC-7: Seed Script - Idempotent**
- Run seed script twice
- Verify second run skips existing rules
- Verify no duplicate entries


**TC-8: Search - Basic Similarity**
- Insert 5 test rules about security deposits
- Search with clause: "The deposit shall be 2 months rent"
- Verify top result relates to security deposit
- Verify similarity score >0.7

**TC-9: Search - State Filtering (State Provided)**
- Insert 3 central rules (state=NULL)
- Insert 2 Maharashtra rules (state="Maharashtra")
- Search with state="Maharashtra"
- Verify returns Maharashtra rules + central rules (5 total)
- Verify no other state rules returned

**TC-10: Search - State Filtering (No State)**
- Insert 3 central rules
- Insert 2 state-specific rules
- Search with state=None
- Verify returns only central rules (3 total)

**TC-11: Search - Top-K Limit**
- Insert 10 rules
- Search with top_k=3
- Verify exactly 3 results returned
- Verify results ordered by similarity (descending)

**TC-12: Search - Similarity Threshold**
- Insert 10 rules
- Search with similarity_threshold=0.9 (high)
- Verify only high-similarity results returned
- Verify no results below threshold

**TC-13: Search - No Matches**
- Insert rules about rental law
- Search with completely unrelated text ("Database configuration")
- Verify returns empty list or very low similarity scores

**TC-14: Search - Empty Query**
- Search with empty string
- Verify handles gracefully (returns empty or error)

**TC-15: Search Result Schema**
- Perform search
- Verify result contains: id, state, act_name, section_reference, rule_text, similarity_score
- Verify similarity_score is float between 0.0 and 1.0


### Test Fixtures

**File: backend/tests/fixtures/test_legal_rules.json**

```json
[
  {
    "state": null,
    "act_name": "Test Act 2024",
    "section_reference": "Section 1",
    "rule_text": "The security deposit shall not exceed two months rent for residential properties."
  },
  {
    "state": null,
    "act_name": "Test Act 2024",
    "section_reference": "Section 2",
    "rule_text": "The landlord shall give at least three months notice before terminating the tenancy."
  },
  {
    "state": "Maharashtra",
    "act_name": "Test State Act 2024",
    "section_reference": "Section 1",
    "rule_text": "In Maharashtra, the security deposit limit is three months rent for residential premises."
  },
  {
    "state": "Karnataka",
    "act_name": "Test State Act 2024",
    "section_reference": "Section 1",
    "rule_text": "In Karnataka, the rent shall be calculated at ten percent per annum of construction cost."
  },
  {
    "state": null,
    "act_name": "Test Act 2024",
    "section_reference": "Section 3",
    "rule_text": "The landlord shall maintain structural integrity including roof, walls, and foundation."
  }
]
```

**Pytest Fixture Example:**

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def test_db():
    """Create test database with pgvector."""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/test_scantract")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()

@pytest.fixture
async def seeded_legal_rules(test_db):
    """Seed test database with sample rules."""
    # Load and insert test rules
    # Return list of inserted rules
    pass
```


## Dependencies

**Python Packages (backend/requirements.txt):**
```
# Already included from previous specs:
# sqlalchemy, asyncpg, openai

# pgvector support
pgvector>=0.2.0

# For seed script
python-dotenv>=1.0.0
```

**System Dependencies:**
- PostgreSQL 14+ with pgvector extension
- pgvector installation:
  ```bash
  # Ubuntu/Debian
  sudo apt install postgresql-14-pgvector
  
  # macOS (Homebrew)
  brew install pgvector
  
  # Or build from source
  git clone https://github.com/pgvector/pgvector.git
  cd pgvector
  make
  sudo make install
  ```

## Environment Variables

**Required (.env):**
```bash
# Already configured from previous specs
OPENAI_API_KEY=sk-xxx

# Database (already configured)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scantract

# Embedding model (optional, defaults to text-embedding-3-small)
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

## Integration with Pipeline

**Updated Classification Flow (Stage 4):**

```python
from backend.db.legal_kb.search import search_legal_rules

async def classify_clause_with_context(
    clause_text: str,
    clause_index: str,
    contract_type: str,
    state: str | None,
    db: AsyncSession
) -> ClauseClassification:
    """Classify clause with legal context from KB."""
    
    # Stage 5A: Retrieve relevant legal rules
    legal_rules = await search_legal_rules(
        clause_text=clause_text,
        state=state,
        top_k=5,
        db=db
    )
    
    # Format context for prompt
    legal_context = "\n\n".join([
        f"{rule.act_name} {rule.section_reference}:\n{rule.rule_text}"
        for rule in legal_rules
    ])
    
    # Stage 4: Classify with context
    classification = await classify_clause(
        clause_text=clause_text,
        clause_index=clause_index,
        contract_type=contract_type,
        retrieved_context=legal_context  # Now filled with actual rules
    )
    
    return classification
```


## Files to Create/Modify

### New Files

**Module Structure:**
1. `backend/db/legal_kb/__init__.py`
2. `backend/db/legal_kb/models.py` - SQLAlchemy + Pydantic models
3. `backend/db/legal_kb/embeddings.py` - Embedding generation
4. `backend/db/legal_kb/search.py` - Semantic search
5. `backend/db/legal_kb/seed_legal_kb.py` - Seed script

**Seed Data:**
6. `backend/db/legal_kb/seed_data/legal_rules.json` - 20 sample rules
7. `backend/db/legal_kb/seed_data/README.md` - Data disclaimer

**Database:**
8. `backend/alembic/versions/003_create_legal_rules_kb.py` - Migration

**Tests:**
9. `backend/tests/test_legal_kb.py` - KB tests
10. `backend/tests/test_legal_search.py` - Search tests
11. `backend/tests/fixtures/test_legal_rules.json` - Test fixtures

### Modified Files

12. `backend/requirements.txt` - Add pgvector package
13. `backend/.env.example` - Document embedding env vars
14. `backend/README.md` - Add seeding instructions

## Deployment Checklist

**Initial Setup:**
1. Install pgvector extension in PostgreSQL
2. Run Alembic migration: `alembic upgrade head`
3. Set OPENAI_API_KEY in .env
4. Run seed script: `python -m backend.db.legal_kb.seed_legal_kb`
5. Run VACUUM ANALYZE: `psql -c 'VACUUM ANALYZE legal_rules;'`

**Production Migration:**
1. Replace sample data with verified legal provisions
2. Obtain legal review of all rule texts
3. Verify citations are accurate and current
4. Test search quality with real contracts
5. Monitor embedding costs (OpenAI API usage)


## Design Tradeoffs

### Embedding Model Choice

**Chosen: OpenAI text-embedding-3-small (1536 dimensions)**

**Pros:**
- High quality embeddings
- Good balance of cost and performance ($0.02 per 1M tokens)
- 1536 dimensions = good semantic capture without excessive storage
- Consistent with Stage 5B (corpus embeddings)

**Cons:**
- Requires external API (network dependency)
- Ongoing cost per embedding
- Vendor lock-in (but model abstraction helps)

**Alternatives Considered:**
- **text-embedding-3-large (3072 dims)**: Better quality but 2x storage, higher cost
- **Sentence transformers (local)**: No API cost but lower quality, requires GPU
- **text-embedding-ada-002 (1536 dims)**: Older model, lower quality

### State Filtering Strategy

**Chosen: Include central rules when state provided**

**Logic:**
```
state=NULL       → Only central rules
state="Maharashtra" → Maharashtra rules + central rules
```

**Rationale:**
- Central acts apply to all states (e.g., Indian Contract Act)
- State acts supplement or override central acts
- This matches legal hierarchy in India

**Alternative Considered:** Strict state filtering (only return exact matches)
- Would miss applicable central provisions
- Not legally sound

### Vector Index Type

**Chosen: IVFFlat with cosine distance**

**Pros:**
- Good balance of speed and accuracy
- Cosine distance appropriate for normalized embeddings
- Well-supported by pgvector

**Cons:**
- Requires VACUUM ANALYZE after bulk inserts
- Approximate search (not exact)

**Alternatives:**
- **Exact search (no index)**: Too slow for >1000 rules
- **HNSW**: Better accuracy but more memory, slower inserts


### Similarity Threshold

**Chosen: 0.7 (configurable)**

**Rationale:**
- Cosine similarity 0.7 = reasonably similar
- Avoids false positives (very unrelated rules)
- Tested empirically with sample data

**Tuning Guidance:**
- If too many irrelevant results: increase threshold (0.75-0.8)
- If missing relevant rules: decrease threshold (0.6-0.65)
- Monitor in production and adjust based on user feedback

## Security & Legal Considerations

**SC-1: Data Verification**
- Sample data is NOT legally verified
- Production deployment requires legal review
- Clear warnings in code, docs, and UI

**SC-2: Data Sources**
- All rules must cite original source
- Track last verification date
- Monitor for legal amendments

**SC-3: Disclaimer Requirement**
- System must display disclaimer: "Not legal advice"
- Users must consent to limitations
- Clear attribution of rule sources in output

**SC-4: Privacy**
- Legal rules are public domain (not sensitive)
- Embedding API sees rule text (acceptable)
- Consider caching embeddings to reduce API calls

**SC-5: Access Control**
- Seed script should be admin-only
- Consider read-only DB user for search queries
- Audit log for rule modifications


## Performance Benchmarks

**Target Performance:**
- Embedding generation: <500ms per rule (network-bound)
- Batch embedding (100 rules): <30 seconds
- Vector search: <100ms for top-k=5
- Seed script (20 rules): <15 seconds

**Optimization Opportunities:**
- Cache embeddings in memory (avoid re-computation)
- Batch API calls for embedding generation
- Use connection pooling for database
- Consider materialized views for frequently-accessed rules

**Scaling Considerations:**
- 1000 rules: current design handles well
- 10,000 rules: may need HNSW index, query optimization
- 100,000+ rules: consider sharding by state/act

## Out of Scope

**Explicitly NOT included in this spec:**
- Stage 5B (reference contract corpus) - separate spec
- Legal rule versioning or history tracking
- User-submitted rule suggestions
- Automatic rule updates from legal databases
- Multi-language support (only English)
- Full-text search (only semantic search)
- Rule conflict detection (overlapping provisions)
- Jurisdiction detection from contract text
- Custom rule weighting or ranking

## Success Criteria

- [ ] pgvector extension enabled in PostgreSQL
- [ ] `legal_rules` table created with vector column
- [ ] IVFFlat index created on embedding column
- [ ] 20 sample rules in seed data (JSON file)
- [ ] Sample data clearly labeled with disclaimer
- [ ] Seed script loads rules and generates embeddings
- [ ] Seed script is idempotent (no duplicates on re-run)
- [ ] `embed_text()` generates 1536-dimensional vectors
- [ ] `search_legal_rules()` returns top-k similar rules
- [ ] Cosine similarity scores calculated correctly
- [ ] State filtering works (central + state-specific rules)
- [ ] Similarity threshold filters low-quality matches
- [ ] All 15 test cases pass
- [ ] Search completes in <100ms
- [ ] Documentation includes production migration checklist


## Notes

- This spec covers Stage 5A (Legal Rules KB) of the ScanTract pipeline
- Stage 5B (Reference Contract Corpus) will use similar embedding approach
- Stage 6 (Merge/Dedupe Context) combines results from 5A and 5B
- Stage 7 (Risk Detection) consumes merged context from stage 6
- Sample data is for development ONLY — legal review required for production
- Use Conventional Commits: `feat:` for features, `chore:` for seed data

## References

- pgvector docs: https://github.com/pgvector/pgvector
- OpenAI embeddings: https://platform.openai.com/docs/guides/embeddings
- Model Tenancy Act 2021: https://prsindia.org/
- PostgreSQL vector operations: https://www.postgresql.org/docs/current/functions-array.html
- Cosine similarity: https://en.wikipedia.org/wiki/Cosine_similarity

## Appendix: Sample Search Scenarios

**Scenario 1: Security Deposit Clause**
- Query: "Landlord requires deposit of 4 months rent"
- Expected Results:
  - Model Tenancy Act Section 7(1): 2 months max (high similarity)
  - Maharashtra Act Section 11(2): 3 months in Mumbai (if state=Maharashtra)
  - Flag: Exceeds legal limit

**Scenario 2: Notice Period**
- Query: "Either party may terminate with 1 month notice"
- Expected Results:
  - Model Tenancy Act Section 21(1): 3 months required (high similarity)
  - Flag: Insufficient notice period

**Scenario 3: Maintenance Obligation**
- Query: "Tenant responsible for all repairs including structural"
- Expected Results:
  - Model Tenancy Act Section 13(1): Landlord responsible for structural (high similarity)
  - Model Tenancy Act Section 15(2): Tenant responsible for minor repairs
  - Flag: Unfair burden on tenant

**Scenario 4: State-Specific Query**
- Query: "Rent increase by 12% annually" (state=Maharashtra)
- Expected Results:
  - Model Tenancy Act Section 9(1): 8% max (central rule)
  - Maharashtra-specific rules if any
  - Flag: Exceeds central limit
