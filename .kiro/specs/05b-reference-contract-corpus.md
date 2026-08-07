# Spec: Standard Contract Reference Corpus

## Overview
Build the reference contract corpus for ScanTract — Stage 5B of the core pipeline that stores standard/fair contract clauses, enables semantic search via pgvector embeddings, and provides reference examples for comparison. This corpus contains vetted "good practice" clauses that serve as benchmarks for evaluating uploaded contracts.

## Scope
- `reference_clauses` table schema with vector embeddings
- Seed data: 25-30 sample standard clauses for rental and freelance contracts
- Semantic search via pgvector cosine similarity
- Contract type filtering (rental vs freelance)
- Shared embedding module (refactor from Stage 5A)
- Seed script for loading initial data
- Unit tests with test database

## Requirements

### Functional Requirements

**FR-1: Database Schema**
- Table: `reference_clauses`
- Columns:
  - `id`: UUID primary key
  - `contract_type`: VARCHAR(50), not null ("rental" or "freelance")
  - `clause_category`: VARCHAR(100), not null (e.g., "security_deposit", "termination")
  - `clause_text`: TEXT, not null (the standard/fair clause text)
  - `source_label`: VARCHAR(255), not null (description: "Standard practice", "Fair clause example")
  - `embedding`: VECTOR(1536) (pgvector embedding for semantic search)
  - `created_at`: TIMESTAMP
  - `updated_at`: TIMESTAMP
- Indexes on contract_type, clause_category, and vector similarity


**FR-2: Seed Data**
- Location: `backend/db/reference_corpus/seed_data/reference_clauses.json`
- 25-30 sample standard/fair clauses covering:
  
  **Rental Contract Categories:**
  - Security deposit (fair limits, refund terms)
  - Termination notice (reasonable periods)
  - Maintenance obligations (balanced landlord/tenant)
  - Late payment fees (reasonable penalties)
  - Rent increase (fair caps)
  - Inspection rights (balanced access)
  - Subletting restrictions (reasonable)
  - Damage liability (fair allocation)
  
  **Freelance Contract Categories:**
  - Payment terms (fair schedules, milestone-based)
  - Intellectual property (balanced ownership)
  - Termination (notice periods, deliverables)
  - Liability caps (reasonable limits)
  - Confidentiality (mutual obligations)
  - Indemnification (balanced risk)
  - Revision rounds (fair limits)
  - Late payment penalties (reasonable)

- Clearly marked as **SAMPLE DATA** for development only

**FR-3: Semantic Search**
- Function: `search_reference_corpus(clause_text, contract_type, top_k=5)`
- Mirror the interface from Stage 5A for consistency
- Embed query clause using shared embedding module
- Search via pgvector cosine similarity
- Filter by contract_type ("rental" or "freelance")
- Return top-k most similar reference clauses with similarity scores

**FR-4: Shared Embedding Module**
- **REFACTOR**: Move embedding logic from `backend/db/legal_kb/embeddings.py` to `backend/rag/embeddings.py`
- Create shared module used by both Stage 5A and Stage 5B
- Update imports in Stage 5A to use new location
- Avoid code duplication
- Single source of truth for embedding generation

**FR-5: Seed Script**
- Script: `backend/db/reference_corpus/seed_reference_corpus.py`
- Load clauses from JSON file
- Generate embeddings using shared module
- Insert into database with batch commits
- Idempotent: skip already-seeded clauses (check by clause_text hash)
- CLI: `python -m backend.db.reference_corpus.seed_reference_corpus`


### Non-Functional Requirements

**NFR-1: Performance**
- Vector search completes in <100ms for top-k=5
- Seed script processes 30 clauses in <1 minute (including embeddings)
- Consistent with Stage 5A performance targets

**NFR-2: Accuracy**
- Cosine similarity threshold: only return clauses with score >0.7
- Same embedding model as Stage 5A (text-embedding-3-small)
- Vector normalization for accurate similarity comparison

**NFR-3: Data Quality**
- Sample clauses represent fair/standard industry practice
- Clear labeling of clause purpose and fairness
- Balanced clauses (not heavily favoring one party)
- Representative of real-world best practices

**NFR-4: Type Safety**
- All functions use type hints (Python 3.11+)
- Pydantic models for reference clauses
- SQLAlchemy models with proper types

**NFR-5: Code Reuse**
- Zero duplication of embedding logic
- Shared module between Stage 5A and 5B
- Consistent API patterns across both stages

## Technical Design

### Module Structure

**Location:** `backend/db/reference_corpus/`

```
backend/db/reference_corpus/
├── __init__.py
├── models.py              # SQLAlchemy + Pydantic models
├── search.py              # Semantic search functions
├── seed_reference_corpus.py  # Seed script (CLI)
└── seed_data/
    ├── reference_clauses.json  # Sample standard clauses
    └── README.md          # Data disclaimer and instructions
```

**NEW Shared Module:** `backend/rag/embeddings.py`

```
backend/rag/
├── __init__.py
├── embeddings.py          # Shared embedding generation (moved from legal_kb)
└── prompts/               # Prompt templates (from Stage 3)
```


### Database Schema Design

**Alembic Migration:** `backend/alembic/versions/004_create_reference_corpus.py`

```sql
-- Create reference_clauses table
CREATE TABLE reference_clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_type VARCHAR(50) NOT NULL,  -- 'rental' or 'freelance'
    clause_category VARCHAR(100) NOT NULL,
    clause_text TEXT NOT NULL,
    source_label VARCHAR(255) NOT NULL,
    embedding VECTOR(1536) NOT NULL,  -- OpenAI text-embedding-3-small
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure reasonable uniqueness (same text shouldn't appear twice)
    CONSTRAINT unique_clause_text UNIQUE (contract_type, clause_category, MD5(clause_text))
);

-- Indexes for performance
CREATE INDEX idx_reference_clauses_contract_type ON reference_clauses(contract_type);
CREATE INDEX idx_reference_clauses_category ON reference_clauses(clause_category);

-- Vector similarity index (IVFFlat for performance)
CREATE INDEX idx_reference_clauses_embedding ON reference_clauses 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Composite index for common query pattern
CREATE INDEX idx_reference_clauses_type_category ON reference_clauses(contract_type, clause_category);
```

**SQLAlchemy Model (backend/db/reference_corpus/models.py):**

```python
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

from ..base import Base

class ReferenceClause(Base):
    __tablename__ = "reference_clauses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_type = Column(String(50), nullable=False)
    clause_category = Column(String(100), nullable=False)
    clause_text = Column(Text, nullable=False)
    source_label = Column(String(255), nullable=False)
    embedding = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ReferenceClause {self.contract_type} - {self.clause_category}>"
```


### Pydantic Models

**File: backend/db/reference_corpus/models.py (continued)**

```python
from pydantic import BaseModel, Field
from typing import Literal

ContractType = Literal["rental", "freelance"]

class ReferenceClauseData(BaseModel):
    """Data structure for seed data."""
    contract_type: ContractType
    clause_category: str
    clause_text: str
    source_label: str

class ReferenceClauseSearchResult(BaseModel):
    """Search result with similarity score."""
    id: str
    contract_type: str
    clause_category: str
    clause_text: str
    source_label: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    
    class Config:
        from_attributes = True
```

### Shared Embedding Module

**File: backend/rag/embeddings.py (REFACTORED from legal_kb/embeddings.py)**

```python
"""
Shared embedding generation module for ScanTract.

Used by:
- Stage 5A: Legal rules knowledge base
- Stage 5B: Reference contract corpus
- Any future vector search features
"""

import os
from openai import AsyncOpenAI
from typing import List
import asyncio
import logging

logger = logging.getLogger(__name__)

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

async def embed_text(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Generate embedding for text using OpenAI.
    
    Args:
        text: Text to embed
        model: OpenAI embedding model (default: text-embedding-3-small)
    
    Returns:
        1536-dimensional embedding vector
    
    Raises:
        RuntimeError: If embedding generation fails
    """
    client = get_openai_client()
    
    try:
        response = await client.embeddings.create(
            model=model,
            input=text,
            encoding_format="float"
        )
        
        embedding = response.data[0].embedding
        
        # Verify dimensions
        expected_dims = 1536 if model == "text-embedding-3-small" else 3072
        if len(embedding) != expected_dims:
            raise ValueError(f"Expected {expected_dims} dimensions, got {len(embedding)}")
        
        return embedding
        
    except Exception as e:
        logger.error(f"Embedding generation failed for text (length={len(text)}): {e}")
        raise RuntimeError(f"Embedding generation failed: {e}")

async def embed_batch(
    texts: List[str],
    batch_size: int = 100,
    model: str = "text-embedding-3-small"
) -> List[List[float]]:
    """
    Embed multiple texts in batches.
    
    Args:
        texts: List of texts to embed
        batch_size: Max texts per API call (OpenAI limit: 2048)
        model: OpenAI embedding model
    
    Returns:
        List of embedding vectors
    """
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        logger.info(f"Embedding batch {i//batch_size + 1}: {len(batch)} texts")
        
        batch_embeddings = await asyncio.gather(
            *[embed_text(t, model=model) for t in batch]
        )
        embeddings.extend(batch_embeddings)
    
    return embeddings
```


### Semantic Search

**File: backend/db/reference_corpus/search.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from .models import ReferenceClause, ReferenceClauseSearchResult
from ...rag.embeddings import embed_text

logger = logging.getLogger(__name__)

async def search_reference_corpus(
    clause_text: str,
    contract_type: str,
    top_k: int = 5,
    similarity_threshold: float = 0.7,
    db: AsyncSession = None
) -> List[ReferenceClauseSearchResult]:
    """
    Search reference corpus by semantic similarity.
    
    Args:
        clause_text: Clause to find similar references for
        contract_type: "rental" or "freelance"
        top_k: Number of results to return
        similarity_threshold: Minimum cosine similarity (0.0-1.0)
        db: Database session
    
    Returns:
        List of matching reference clauses with similarity scores
    """
    # Generate embedding for query clause
    try:
        query_embedding = await embed_text(clause_text)
    except Exception as e:
        logger.error(f"Failed to embed query clause: {e}")
        return []
    
    # Build query with contract type filtering
    query = select(
        ReferenceClause,
        ReferenceClause.embedding.cosine_distance(query_embedding).label("distance")
    ).where(
        ReferenceClause.contract_type == contract_type
    ).order_by(
        "distance"
    ).limit(top_k)
    
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to search results with similarity scores
    search_results = []
    for clause, distance in rows:
        # Convert cosine distance to similarity: similarity = 1 - distance
        similarity = 1.0 - distance
        
        if similarity >= similarity_threshold:
            search_results.append(ReferenceClauseSearchResult(
                id=str(clause.id),
                contract_type=clause.contract_type,
                clause_category=clause.clause_category,
                clause_text=clause.clause_text,
                source_label=clause.source_label,
                similarity_score=round(similarity, 4)
            ))
    
    logger.info(
        f"Found {len(search_results)} reference clauses above threshold "
        f"{similarity_threshold} for contract_type={contract_type}"
    )
    
    return search_results
```


### Sample Seed Data

**File: backend/db/reference_corpus/seed_data/reference_clauses.json**

```json
[
  {
    "contract_type": "rental",
    "clause_category": "security_deposit",
    "clause_text": "The security deposit shall be equivalent to two months' rent for residential properties. The landlord shall return the security deposit within thirty days of the termination of the tenancy, after deducting any legitimate charges for unpaid rent or damages beyond normal wear and tear.",
    "source_label": "Standard practice - fair deposit terms"
  },
  {
    "contract_type": "rental",
    "clause_category": "termination_notice",
    "clause_text": "Either party may terminate this agreement by providing written notice of at least three months to the other party. The notice period shall begin from the date the written notice is received.",
    "source_label": "Balanced termination - adequate notice period"
  },
  {
    "contract_type": "rental",
    "clause_category": "maintenance",
    "clause_text": "The landlord shall be responsible for structural repairs including roof, walls, foundation, and plumbing systems. The tenant shall be responsible for day-to-day maintenance including cleaning, changing light bulbs, and minor repairs that do not affect the structure.",
    "source_label": "Fair allocation - balanced maintenance duties"
  },
  {
    "contract_type": "rental",
    "clause_category": "late_payment",
    "clause_text": "If rent is not paid by the 10th day of the month, a late fee of 5% of the monthly rent will be charged. If rent remains unpaid for 15 days, the landlord may issue a formal notice of default.",
    "source_label": "Reasonable penalty - graduated approach"
  },
  {
    "contract_type": "rental",
    "clause_category": "rent_increase",
    "clause_text": "The annual rent increase shall not exceed 8% of the current rent, subject to mutual agreement. The landlord shall provide written notice of any rent increase at least 90 days before the increase takes effect.",
    "source_label": "Fair rent control - capped increase with notice"
  },
  {
    "contract_type": "rental",
    "clause_category": "inspection",
    "clause_text": "The landlord or authorized agent may inspect the premises at reasonable times for maintenance or repairs, providing at least 24 hours advance written notice to the tenant, except in emergencies.",
    "source_label": "Balanced access - respects tenant privacy"
  },
  {
    "contract_type": "rental",
    "clause_category": "subletting",
    "clause_text": "The tenant shall not sublet or assign the premises without prior written consent of the landlord, which shall not be unreasonably withheld.",
    "source_label": "Reasonable restriction - prevents unreasonable denial"
  },
  {
    "contract_type": "rental",
    "clause_category": "damage_liability",
    "clause_text": "The tenant shall be liable for damages caused by negligence or willful misconduct. Normal wear and tear shall not be considered damage. The tenant shall report any damages to the landlord within 7 days of occurrence.",
    "source_label": "Fair liability - excludes normal wear and tear"
  }
]
```


**Additional Rental Clauses:**

```json
  {
    "contract_type": "rental",
    "clause_category": "utilities",
    "clause_text": "The tenant shall be responsible for all utility charges including electricity, water, and internet. The landlord shall ensure availability of connections for these services.",
    "source_label": "Standard practice - clear utility allocation"
  },
  {
    "contract_type": "rental",
    "clause_category": "renewal",
    "clause_text": "The tenancy may be renewed upon mutual written consent of both parties at least 60 days before the expiry of the current term. The terms of renewal shall be negotiated in good faith.",
    "source_label": "Fair renewal - mutual agreement with adequate notice"
  },
  {
    "contract_type": "rental",
    "clause_category": "force_majeure",
    "clause_text": "Neither party shall be liable for failure to perform obligations due to circumstances beyond reasonable control, including natural disasters, war, or government restrictions. Obligations shall resume when circumstances permit.",
    "source_label": "Balanced force majeure - protects both parties"
  }
```

**Freelance Contract Clauses:**

```json
  {
    "contract_type": "freelance",
    "clause_category": "payment_terms",
    "clause_text": "Payment shall be made within 30 days of invoice submission. The project will be divided into milestones with payments of 30% upon signing, 40% upon mid-project review, and 30% upon final delivery and acceptance.",
    "source_label": "Fair payment structure - milestone-based with reasonable terms"
  },
  {
    "contract_type": "freelance",
    "clause_category": "intellectual_property",
    "clause_text": "Upon full payment, all intellectual property rights in the deliverables shall transfer to the client. The freelancer retains the right to showcase the work in their portfolio after project completion, unless confidentiality restrictions apply.",
    "source_label": "Balanced IP - transfer with portfolio rights"
  },
  {
    "contract_type": "freelance",
    "clause_category": "termination",
    "clause_text": "Either party may terminate this agreement with 14 days written notice. The client shall pay for all work completed up to the termination date, including pro-rated payment for work in progress.",
    "source_label": "Fair termination - reasonable notice with payment for work done"
  },
  {
    "contract_type": "freelance",
    "clause_category": "liability_cap",
    "clause_text": "The freelancer's total liability for any claims arising from this agreement shall not exceed the total amount paid by the client under this contract. This limitation does not apply to claims arising from willful misconduct or gross negligence.",
    "source_label": "Reasonable liability - capped with exceptions for misconduct"
  },
  {
    "contract_type": "freelance",
    "clause_category": "confidentiality",
    "clause_text": "Both parties agree to keep confidential any proprietary information disclosed during the course of this engagement for a period of two years after termination, except where disclosure is required by law.",
    "source_label": "Mutual confidentiality - balanced obligations"
  },
  {
    "contract_type": "freelance",
    "clause_category": "revisions",
    "clause_text": "The project includes up to three rounds of revisions based on the initial scope. Additional revisions beyond this shall be billed separately at the agreed hourly rate.",
    "source_label": "Fair revision policy - clear limits with provision for extras"
  }
]
```


**More Freelance Clauses:**

```json
  {
    "contract_type": "freelance",
    "clause_category": "late_payment",
    "clause_text": "If payment is not received within 30 days of invoice date, a late fee of 1.5% per month (18% per annum) will accrue on the outstanding amount. Work may be suspended after 45 days of non-payment.",
    "source_label": "Reasonable late fee - industry standard with suspension clause"
  },
  {
    "contract_type": "freelance",
    "clause_category": "indemnification",
    "clause_text": "Each party shall indemnify the other against claims arising from their own negligence or breach of this agreement. The client shall indemnify the freelancer against claims arising from the client's use of the deliverables.",
    "source_label": "Mutual indemnification - balanced risk allocation"
  },
  {
    "contract_type": "freelance",
    "clause_category": "scope_changes",
    "clause_text": "Any changes to the project scope must be agreed upon in writing by both parties. Scope changes may result in adjustments to timeline and cost, which shall be documented in a change order.",
    "source_label": "Standard scope management - prevents scope creep"
  },
  {
    "contract_type": "freelance",
    "clause_category": "deliverables",
    "clause_text": "The freelancer shall deliver the completed work in the formats specified in the project brief. Final deliverables shall be provided within the agreed timeline, with interim deliverables as per the milestone schedule.",
    "source_label": "Clear deliverable terms - format and timing specified"
  },
  {
    "contract_type": "freelance",
    "clause_category": "warranties",
    "clause_text": "The freelancer warrants that the work is original and does not infringe any third-party intellectual property rights. The freelancer provides a 30-day warranty to fix any defects in the deliverables at no additional cost.",
    "source_label": "Standard warranties - originality and defect correction"
  },
  {
    "contract_type": "freelance",
    "clause_category": "communication",
    "clause_text": "Both parties agree to maintain regular communication through agreed channels. The freelancer shall provide weekly progress updates, and the client shall respond to queries within 3 business days to avoid project delays.",
    "source_label": "Clear communication protocol - prevents delays"
  },
  {
    "contract_type": "freelance",
    "clause_category": "expenses",
    "clause_text": "Pre-approved expenses directly related to the project shall be reimbursed by the client upon submission of receipts. The freelancer shall seek approval for expenses exceeding $100 before incurring them.",
    "source_label": "Fair expense policy - reimbursement with approval threshold"
  },
  {
    "contract_type": "freelance",
    "clause_category": "non_compete",
    "clause_text": "During the term of this agreement, the freelancer shall not provide similar services to direct competitors of the client within the same market segment. This restriction expires upon project completion.",
    "source_label": "Reasonable non-compete - limited scope and duration"
  },
  {
    "contract_type": "freelance",
    "clause_category": "dispute_resolution",
    "clause_text": "Any disputes arising from this agreement shall first be addressed through good faith negotiation. If unresolved within 30 days, parties may pursue mediation before resorting to legal action.",
    "source_label": "Graduated dispute resolution - encourages settlement"
  }
]
```

**Total: 28 sample clauses**
- 11 rental clauses
- 17 freelance clauses
- Covering all major contract categories
- All marked with fair/standard practice labels


### Seed Script

**File: backend/db/reference_corpus/seed_reference_corpus.py**

```python
#!/usr/bin/env python3
"""
Seed the reference contract corpus.

Usage:
    python -m backend.db.reference_corpus.seed_reference_corpus
    
Environment:
    Requires OPENAI_API_KEY for embedding generation
"""

import asyncio
import json
import hashlib
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..database import get_async_session
from .models import ReferenceClause, ReferenceClauseData
from ...rag.embeddings import embed_text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEED_DATA_PATH = Path(__file__).parent / "seed_data" / "reference_clauses.json"

async def load_seed_data() -> list[ReferenceClauseData]:
    """Load seed data from JSON file."""
    if not SEED_DATA_PATH.exists():
        raise FileNotFoundError(f"Seed data not found: {SEED_DATA_PATH}")
    
    with open(SEED_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return [ReferenceClauseData(**item) for item in data]

def clause_hash(contract_type: str, clause_category: str, clause_text: str) -> str:
    """Generate hash for clause uniqueness check."""
    content = f"{contract_type}:{clause_category}:{clause_text}"
    return hashlib.md5(content.encode()).hexdigest()

async def clause_exists(
    db: AsyncSession,
    contract_type: str,
    clause_category: str,
    clause_text: str
) -> bool:
    """Check if clause already exists in database."""
    # Check by MD5 hash (same as database constraint)
    text_hash = hashlib.md5(clause_text.encode()).hexdigest()
    
    query = select(ReferenceClause).where(
        ReferenceClause.contract_type == contract_type,
        ReferenceClause.clause_category == clause_category,
        # Note: This is a simplified check; the actual DB uses MD5(clause_text)
    )
    result = await db.execute(query)
    existing = result.scalars().all()
    
    # Check if any existing clause has matching text
    for clause in existing:
        if hashlib.md5(clause.clause_text.encode()).hexdigest() == text_hash:
            return True
    
    return False

async def seed_reference_corpus():
    """Main seeding function."""
    logger.info("=" * 60)
    logger.info("⚠️  SAMPLE DATA WARNING")
    logger.info("This seed data is for DEVELOPMENT ONLY.")
    logger.info("DO NOT use in production without legal verification.")
    logger.info("=" * 60)
    
    # Load seed data
    logger.info(f"Loading seed data from {SEED_DATA_PATH}")
    clauses_data = await load_seed_data()
    logger.info(f"Loaded {len(clauses_data)} reference clauses")
    
    # Get database session
    async for db in get_async_session():
        inserted = 0
        skipped = 0
        failed = 0
        
        for clause_data in clauses_data:
            try:
                # Check if clause already exists (idempotent)
                if await clause_exists(
                    db,
                    clause_data.contract_type,
                    clause_data.clause_category,
                    clause_data.clause_text
                ):
                    logger.debug(
                        f"Skipping existing clause: {clause_data.contract_type} - "
                        f"{clause_data.clause_category}"
                    )
                    skipped += 1
                    continue
                
                # Generate embedding
                logger.info(
                    f"Embedding: {clause_data.contract_type} - {clause_data.clause_category}"
                )
                embedding = await embed_text(clause_data.clause_text)
                
                # Create and insert clause
                clause = ReferenceClause(
                    contract_type=clause_data.contract_type,
                    clause_category=clause_data.clause_category,
                    clause_text=clause_data.clause_text,
                    source_label=clause_data.source_label,
                    embedding=embedding
                )
                
                db.add(clause)
                inserted += 1
                
                logger.info(
                    f"✓ Inserted: {clause_data.contract_type} - {clause_data.clause_category}"
                )
                
            except Exception as e:
                logger.error(
                    f"✗ Failed to insert {clause_data.contract_type} - "
                    f"{clause_data.clause_category}: {e}"
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
            logger.info("  psql -c 'VACUUM ANALYZE reference_clauses;'")
        
        break  # Exit async generator

if __name__ == "__main__":
    asyncio.run(seed_reference_corpus())
```


## Test Plan

### Test Strategy

**Test Database:**
- Use pytest fixtures with test-specific database
- Small subset of seed data (5-10 clauses per contract type)
- Shared with Stage 5A test infrastructure

### Test Cases

**Test File:** `backend/tests/test_reference_corpus.py`

**TC-1: Database Schema - reference_clauses Table**
- Verify table exists with correct columns
- Verify indexes created (contract_type, category, embedding)
- Verify UNIQUE constraint on (contract_type, clause_category, MD5(clause_text))

**TC-2: Shared Embedding Module - Import Path**
- Verify `from backend.rag.embeddings import embed_text` works
- Verify no duplicate embedding code exists
- Verify Stage 5A updated to use shared module

**TC-3: Embedding Generation - Consistency**
- Generate embedding for same text twice
- Verify embeddings are identical (deterministic)
- Verify dimensions = 1536

**TC-4: Seed Script - Load Data**
- Run seed script with test data (10 clauses)
- Verify all 10 clauses inserted
- Verify embeddings generated and stored

**TC-5: Seed Script - Idempotent**
- Run seed script twice
- Verify second run skips existing clauses
- Verify no duplicate entries

**TC-6: Search - Basic Similarity (Rental)**
- Insert 5 rental test clauses
- Search with clause: "Deposit is 2 months rent"
- Verify top result is security_deposit category
- Verify similarity score >0.7
- Verify contract_type filter works (only rental results)

**TC-7: Search - Basic Similarity (Freelance)**
- Insert 5 freelance test clauses
- Search with clause: "Payment in 3 milestones"
- Verify top result is payment_terms category
- Verify only freelance results returned

**TC-8: Search - Contract Type Filtering**
- Insert 3 rental clauses + 3 freelance clauses
- Search with contract_type="rental"
- Verify only rental clauses returned
- Search with contract_type="freelance"
- Verify only freelance clauses returned

**TC-9: Search - Top-K Limit**
- Insert 10 clauses
- Search with top_k=3
- Verify exactly 3 results returned
- Verify results ordered by similarity (descending)

**TC-10: Search - Similarity Threshold**
- Insert 10 clauses
- Search with similarity_threshold=0.9 (high)
- Verify only high-similarity results returned
- Verify no results below threshold

**TC-11: Search - Category Matching**
- Insert clauses from multiple categories
- Search with termination clause
- Verify top result is termination category
- Verify category field populated in results

**TC-12: Search Result Schema**
- Perform search
- Verify result contains: id, contract_type, clause_category, clause_text, source_label, similarity_score
- Verify similarity_score between 0.0 and 1.0


## Files to Create/Modify

### New Files

**Module Structure:**
1. `backend/db/reference_corpus/__init__.py`
2. `backend/db/reference_corpus/models.py` - SQLAlchemy + Pydantic models
3. `backend/db/reference_corpus/search.py` - Semantic search
4. `backend/db/reference_corpus/seed_reference_corpus.py` - Seed script

**Seed Data:**
5. `backend/db/reference_corpus/seed_data/reference_clauses.json` - 28 sample clauses
6. `backend/db/reference_corpus/seed_data/README.md` - Data disclaimer

**Shared Module (REFACTORED):**
7. `backend/rag/embeddings.py` - Shared embedding generation (moved from legal_kb)

**Database:**
8. `backend/alembic/versions/004_create_reference_corpus.py` - Migration

**Tests:**
9. `backend/tests/test_reference_corpus.py` - Corpus tests
10. `backend/tests/fixtures/test_reference_clauses.json` - Test fixtures

### Modified Files

11. `backend/db/legal_kb/search.py` - Update import: `from backend.rag.embeddings import embed_text`
12. `backend/db/legal_kb/seed_legal_kb.py` - Update import
13. `backend/requirements.txt` - Already has pgvector from Stage 5A
14. `backend/.env.example` - Document usage (already from Stage 5A)
15. `backend/README.md` - Add seeding instructions for reference corpus

## Refactoring Checklist

**Moving Embedding Logic to Shared Module:**

1. Create `backend/rag/embeddings.py` with complete embedding functions
2. Update `backend/db/legal_kb/search.py`:
   ```python
   # OLD: from .embeddings import embed_text
   # NEW: from ...rag.embeddings import embed_text
   ```
3. Update `backend/db/legal_kb/seed_legal_kb.py`:
   ```python
   # OLD: from .embeddings import embed_text
   # NEW: from ...rag.embeddings import embed_text
   ```
4. Delete `backend/db/legal_kb/embeddings.py` (now redundant)
5. Run tests to verify Stage 5A still works after refactor
6. Implement Stage 5B using shared module


## Integration with Pipeline

**Updated Classification Flow (Stage 4 + 5A + 5B):**

```python
from backend.db.legal_kb.search import search_legal_rules
from backend.db.reference_corpus.search import search_reference_corpus

async def classify_clause_with_full_context(
    clause_text: str,
    clause_index: str,
    contract_type: str,
    state: str | None,
    db: AsyncSession
) -> ClauseClassification:
    """Classify clause with legal rules + reference corpus context."""
    
    # Stage 5A: Retrieve relevant legal rules
    legal_rules = await search_legal_rules(
        clause_text=clause_text,
        state=state,
        top_k=5,
        db=db
    )
    
    # Stage 5B: Retrieve similar reference clauses
    reference_clauses = await search_reference_corpus(
        clause_text=clause_text,
        contract_type=contract_type,
        top_k=5,
        db=db
    )
    
    # Format combined context (Stage 6 will dedupe/merge these)
    legal_context = "\n\n".join([
        f"Legal Rule - {rule.act_name} {rule.section_reference}:\n{rule.rule_text}"
        for rule in legal_rules
    ])
    
    reference_context = "\n\n".join([
        f"Reference Example - {ref.clause_category} ({ref.source_label}):\n{ref.clause_text}"
        for ref in reference_clauses
    ])
    
    combined_context = f"## Legal Rules:\n{legal_context}\n\n## Reference Clauses:\n{reference_context}"
    
    # Stage 4: Classify with full context
    classification = await classify_clause(
        clause_text=clause_text,
        clause_index=clause_index,
        contract_type=contract_type,
        retrieved_context=combined_context
    )
    
    return classification
```

## Dependencies

**Python Packages:**
```
# Already included from previous specs:
# sqlalchemy, asyncpg, openai, pgvector, pydantic
```

**No New Dependencies Required** - reuses existing packages from Stage 5A.

## Environment Variables

**All Required Variables Already Configured:**
```bash
# From Stage 5A
OPENAI_API_KEY=sk-xxx
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scantract
```


## Design Tradeoffs

### Contract Type Filtering Strategy

**Chosen: Strict contract type filtering**

**Logic:**
```
contract_type="rental"     → Only rental clauses
contract_type="freelance"  → Only freelance clauses
```

**Rationale:**
- Rental and freelance contracts have different legal contexts
- Cross-contamination would reduce relevance
- Clear separation improves search quality

**Alternative Considered:** Include "general" contract clauses
- Would require third contract_type value
- Adds complexity without clear benefit
- Can add later if needed

### Clause Categories

**Chosen: Flexible VARCHAR(100) field**

**Pros:**
- Easy to add new categories without schema changes
- Supports fine-grained categorization
- Queryable for category-specific searches (future)

**Cons:**
- No enum validation at database level
- Possible typos in seed data

**Alternative:** Enum type or separate category table
- More rigid, harder to evolve
- Not necessary for MVP

### Source Label Field

**Chosen: Descriptive text field**

**Purpose:**
- Indicates why this clause is "standard/fair"
- Helps users understand reference quality
- No strict schema (flexible descriptions)

**Examples:**
- "Standard practice - fair deposit terms"
- "Balanced termination - adequate notice"
- "Fair payment structure - milestone-based"


## Performance Benchmarks

**Target Performance:**
- Embedding generation: <500ms per clause (network-bound)
- Batch embedding (30 clauses): <20 seconds
- Vector search: <100ms for top-k=5
- Seed script (30 clauses): <30 seconds

**Optimization Opportunities:**
- Batch API calls for embedding generation (already implemented)
- Connection pooling for database (reuse from Stage 5A)
- Materialized views for frequently-accessed clauses (future)

**Scaling Considerations:**
- 100 clauses: current design handles well
- 1000 clauses: may need query optimization
- 10,000+ clauses: consider sharding by contract_type/category

## Out of Scope

**Explicitly NOT included in this spec:**
- Stage 6 (Merge/Dedupe context from 5A + 5B) - separate spec
- Stage 7 (Risk detection with merged context) - separate spec
- User-submitted reference clauses
- Clause voting/rating system
- Multi-language support
- Real-time clause suggestion during contract drafting
- Clause version history or evolution tracking
- Custom clause libraries per user/organization

## Success Criteria

- [ ] `reference_clauses` table created with vector column
- [ ] IVFFlat index created on embedding column
- [ ] 28 sample clauses in seed data (rental + freelance)
- [ ] Sample data clearly labeled with disclaimer
- [ ] Seed script loads clauses and generates embeddings
- [ ] Seed script is idempotent (no duplicates on re-run)
- [ ] Embedding logic refactored to `backend/rag/embeddings.py`
- [ ] Stage 5A updated to use shared embedding module
- [ ] Zero duplication of embedding code
- [ ] `search_reference_corpus()` returns top-k similar clauses
- [ ] Contract type filtering works correctly
- [ ] Cosine similarity scores calculated correctly
- [ ] All 12 test cases pass
- [ ] Search completes in <100ms
- [ ] Stage 5A still passes all tests after refactor


## Notes

- This spec covers Stage 5B (Reference Corpus) of the ScanTract pipeline
- Stage 5A (Legal Rules KB) provides legal compliance context
- Stage 5B provides best practice comparison context
- Stage 6 will merge/dedupe results from 5A and 5B
- Stage 7 (Risk Detection) uses merged context for LLM analysis
- Sample data is for development ONLY — review required for production
- Use Conventional Commits: `feat:` for features, `refactor:` for embedding module move

## References

- pgvector docs: https://github.com/pgvector/pgvector
- OpenAI embeddings: https://platform.openai.com/docs/guides/embeddings
- Contract best practices: https://www.nolo.com/legal-encyclopedia/
- Freelance contract templates: https://www.rocketlawyer.com/
- PostgreSQL MD5 function: https://www.postgresql.org/docs/current/functions-string.html

## Appendix: Sample Search Scenarios

**Scenario 1: Security Deposit (Rental)**
- Query: "Landlord requires deposit of 4 months rent"
- Expected Reference Results:
  - Standard security_deposit clause: "two months' rent" (high similarity)
  - Fair refund terms clause (medium similarity)
- Combined with Stage 5A: Legal rule "max 2 months" (high similarity)
- Output: Exceeds both legal limit AND standard practice

**Scenario 2: Payment Terms (Freelance)**
- Query: "Payment due 60 days after invoice"
- Expected Reference Results:
  - Standard payment_terms: "30 days" (high similarity)
  - Milestone-based payment example (medium similarity)
- Output: Longer than standard practice (flag as unfavorable to freelancer)

**Scenario 3: Termination Notice (Rental)**
- Query: "Either party may terminate with 7 days notice"
- Expected Reference Results:
  - Standard termination: "three months notice" (high similarity)
  - Balanced termination clause (high similarity)
- Combined with Stage 5A: Legal rule "3 months required"
- Output: Below legal AND standard practice (high risk)

**Scenario 4: IP Rights (Freelance)**
- Query: "Client owns all IP, freelancer has no rights"
- Expected Reference Results:
  - Balanced IP clause: "transfer with portfolio rights" (high similarity)
  - Standard IP transfer example (high similarity)
- Output: More restrictive than standard (flag as unfavorable to freelancer)

## README for Seed Data

**File: backend/db/reference_corpus/seed_data/README.md**

```markdown
# Reference Contract Corpus Seed Data

⚠️ **IMPORTANT: SAMPLE DATA ONLY**

The clauses in `reference_clauses.json` are SAMPLE DATA for development and testing purposes only.
They represent what industry experts generally consider fair/standard practices, but are NOT legal advice.

Before deploying ScanTract for real use:
1. Replace sample data with verified reference clauses
2. Obtain legal review to ensure accuracy
3. Verify clauses represent current best practices
4. Consider regional variations in contract norms
5. Update source labels with proper attribution

## Data Philosophy

Reference clauses should be:
- **Balanced**: Not heavily favoring one party
- **Clear**: Unambiguous language
- **Standard**: Widely accepted in industry
- **Fair**: Reasonable to both parties
- **Legal**: Compliant with applicable laws

## Adding New Clauses

Clauses should include:
- `contract_type`: "rental" or "freelance"
- `clause_category`: Category name (lowercase with underscores)
- `clause_text`: The full clause text (clear, complete)
- `source_label`: Description of why this is standard/fair

Example:
```json
{
  "contract_type": "rental",
  "clause_category": "security_deposit",
  "clause_text": "The security deposit shall not exceed two months' rent...",
  "source_label": "Standard practice - complies with Model Tenancy Act"
}
```

## Data Sources (for production replacement)

- Contract templates from legal services (Rocket Lawyer, LegalZoom)
- Industry best practice guides
- Legal expert recommendations
- Government model contracts (e.g., Model Tenancy Act)
```
