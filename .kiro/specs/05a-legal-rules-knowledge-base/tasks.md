# Tasks: Legal Rules Knowledge Base Implementation (Stage 5A)

## Overview
Implement pgvector-powered legal rules knowledge base for ScanTract with OpenAI embeddings, state-aware similarity search, and seed data management.

**Critical Design Note**: This spec creates `backend/db/legal_kb/embeddings.py` as a self-contained module. Stage 5B will later refactor it into `backend/rag/embeddings.py` and update imports. Do NOT pre-emptively move it to a shared location - build it exactly as specified here.

**Dependencies**:
- Stage 4 (Clause Classification): Provides the classification pipeline that will call search_legal_rules()
- PostgreSQL with pgvector extension must be available

---

## Task 1: Create Legal KB Module Structure
**Files**: Multiple module files

**Actions**:
- Create `backend/db/legal_kb/` directory
- Create `backend/db/legal_kb/__init__.py` with module docstring
- Create `backend/db/legal_kb/models.py` (empty, populated in Task 3)
- Create `backend/db/legal_kb/embeddings.py` (empty, populated in Task 4)
- Create `backend/db/legal_kb/search.py` (empty, populated in Task 5)
- Create `backend/db/legal_kb/seed_legal_kb.py` (empty, populated in Task 8)
- Create `backend/db/legal_kb/seed_data/` directory
- Create `backend/db/legal_kb/seed_data/.gitkeep`

**Acceptance Criteria**:
- All directories created: `backend/db/legal_kb/` and `backend/db/legal_kb/seed_data/`
- All `__init__.py` files present
- Empty placeholder files for models.py, embeddings.py, search.py, seed_legal_kb.py
- Module is importable: `from backend.db.legal_kb import models` works

---

## Task 2: Create Legal Rules KB Migration
**File**: `backend/alembic/versions/003_create_legal_rules_kb.py`

**Actions**:
- Create Alembic migration with revision ID "003", down_revision "002"
- **Enable pgvector extension:**
  ```python
  op.execute('CREATE EXTENSION IF NOT EXISTS vector')
  ```

- **Create legal_rules table:**
  - `id` INTEGER PRIMARY KEY
  - `state` VARCHAR(50) NULLABLE - State code (e.g., "MH", "KA") or NULL for central laws
  - `act_name` VARCHAR(255) NOT NULL - e.g., "Model Tenancy Act 2021"
  - `section_reference` VARCHAR(100) NOT NULL - e.g., "Section 7(1)"
  - `rule_text` TEXT NOT NULL - Full rule text
  - `embedding` VECTOR(1536) NOT NULL - OpenAI text-embedding-3-small output
  - `created_at` TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  - `updated_at` TIMESTAMP WITH TIME ZONE DEFAULT NOW()

- **Add UNIQUE constraint:**
  - `UNIQUE(act_name, section_reference, state)` - Prevents duplicate rules

- **Create indexes:**
  - Index on `state` for state filtering
  - Index on `act_name` for act-based queries
  - **IVFFlat index on embedding:**
    ```python
    op.execute('''
        CREATE INDEX ix_legal_rules_embedding_ivfflat 
        ON legal_rules 
        USING ivfflat (embedding vector_cosine_ops) 
        WITH (lists = 100)
    ''')
    ```

- **Downgrade:**
  - Drop indexes
  - Drop table
  - Drop extension (optional - may be used by other tables)

**Acceptance Criteria**:
- Migration file follows Alembic naming convention
- pgvector extension enabled before table creation
- legal_rules table has all 8 columns with correct types
- VECTOR(1536) dimension matches text-embedding-3-small output
- UNIQUE constraint enforces no duplicate rules per (act, section, state)
- IVFFlat index uses vector_cosine_ops for cosine similarity
- lists=100 parameter set for IVFFlat index
- Downgrade removes all changes cleanly

---

## Task 3: Implement Legal KB Models
**File**: `backend/db/legal_kb/models.py`

**Actions**:
- Add imports:
  ```python
  from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint, Index
  from sqlalchemy.dialects.postgresql import VECTOR
  from sqlalchemy.orm import declarative_base
  from pydantic import BaseModel, Field
  from datetime import datetime
  from typing import Optional
  ```

- **Implement SQLAlchemy LegalRule model:**
  ```python
  class LegalRule(Base):
      __tablename__ = "legal_rules"
      
      id = Column(Integer, primary_key=True, index=True)
      state = Column(String(50), nullable=True, index=True)
      act_name = Column(String(255), nullable=False, index=True)
      section_reference = Column(String(100), nullable=False)
      rule_text = Column(Text, nullable=False)
      embedding = Column(VECTOR(1536), nullable=False)
      created_at = Column(DateTime(timezone=True), server_default="NOW()")
      updated_at = Column(DateTime(timezone=True), server_default="NOW()", onupdate="NOW()")
      
      __table_args__ = (
          UniqueConstraint('act_name', 'section_reference', 'state', name='uq_legal_rule'),
      )
  ```

- **Implement Pydantic LegalRuleData model:**
  ```python
  class LegalRuleData(BaseModel):
      """Data model for loading legal rules (without embedding)."""
      state: Optional[str] = Field(None, max_length=50, description="State code (e.g., MH, KA) or None for central laws")
      act_name: str = Field(..., max_length=255, description="Name of the act/statute")
      section_reference: str = Field(..., max_length=100, description="Section or clause reference")
      rule_text: str = Field(..., min_length=10, description="Full text of the legal rule")
  ```

- **Implement Pydantic LegalRuleSearchResult model:**
  ```python
  class LegalRuleSearchResult(BaseModel):
      """Search result with similarity score."""
      id: int
      state: Optional[str]
      act_name: str
      section_reference: str
      rule_text: str
      similarity: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score (0.0-1.0)")
      
      class Config:
          from_attributes = True
  ```

**Acceptance Criteria**:
- LegalRule model matches migration schema exactly (all 8 columns)
- VECTOR(1536) type matches embedding dimension
- UniqueConstraint on (act_name, section_reference, state) defined
- LegalRuleData has validation for all fields (state optional, others required)
- LegalRuleSearchResult includes similarity field with 0.0-1.0 range validation
- from_attributes=True allows SQLAlchemy model conversion

---

## Task 4: Implement Embeddings Module
**File**: `backend/db/legal_kb/embeddings.py`

**Actions**:
- Add imports:
  ```python
  import os
  import asyncio
  from typing import Optional
  from openai import AsyncOpenAI
  import logging
  ```

- **Implement get_openai_client() singleton:**
  ```python
  _openai_client: Optional[AsyncOpenAI] = None
  
  def get_openai_client() -> AsyncOpenAI:
      """Lazy singleton for OpenAI client. Reads OPENAI_API_KEY from env."""
      global _openai_client
      if _openai_client is None:
          api_key = os.getenv("OPENAI_API_KEY")
          if not api_key:
              raise ValueError("OPENAI_API_KEY environment variable required")
          _openai_client = AsyncOpenAI(api_key=api_key)
      return _openai_client
  ```

- **Implement embed_text(text: str) -> list[float]:**
  - Call OpenAI API with model="text-embedding-3-small"
  - Extract embedding from response
  - Validate dimension is exactly 1536 (raise ValueError if not)
  - Return embedding as list[float]
  - Handle RateLimitError with logging
  - Handle APIError with logging

- **Implement embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:**
  - Split texts into batches of batch_size
  - For each batch, create tasks with embed_text() for each text
  - Use asyncio.gather() to run batch concurrently
  - Combine all results and return
  - Log batch progress ("Embedding batch X/Y...")

**Acceptance Criteria**:
- get_openai_client() is lazy singleton (only creates client once)
- Raises ValueError if OPENAI_API_KEY missing
- embed_text() calls text-embedding-3-small model
- Validates embedding dimension is exactly 1536
- Raises ValueError if dimension mismatch
- embed_batch() processes in batches of configurable size (default 100)
- Uses asyncio.gather() for concurrent batch processing
- All API errors logged with context

---

## Task 5: Implement Legal Rules Search
**File**: `backend/db/legal_kb/search.py`

**Actions**:
- Add imports:
  ```python
  from sqlalchemy.ext.asyncio import AsyncSession
  from sqlalchemy import select, and_, or_
  from backend.db.legal_kb.models import LegalRule, LegalRuleSearchResult
  from backend.db.legal_kb.embeddings import embed_text
  from typing import Optional
  import logging
  ```

- **Implement search_legal_rules() function:**
  ```python
  async def search_legal_rules(
      clause_text: str,
      state: Optional[str] = None,
      contract_type: Optional[str] = None,
      top_k: int = 5,
      similarity_threshold: float = 0.7,
      db: AsyncSession
  ) -> list[LegalRuleSearchResult]:
  ```

- **Implementation logic:**
  1. **Embed query:** `query_embedding = await embed_text(clause_text)`
  2. **Build SQLAlchemy query:**
     - Select from LegalRule
     - Calculate distance: `LegalRule.embedding.cosine_distance(query_embedding).label('distance')`
     - Convert to similarity: `similarity = 1.0 - distance`
  3. **Apply state filtering:**
     - **If state provided:** Include rules where `state == provided_state OR state IS NULL`
     - **If state is None:** Include ONLY rules where `state IS NULL` (central laws only)
  4. **Order by similarity descending**
  5. **Limit to top_k results**
  6. **Execute query**
  7. **Filter results:** Keep only where `similarity >= similarity_threshold`
  8. **Convert to LegalRuleSearchResult** with similarity score
  9. **Return list[LegalRuleSearchResult]**

- **Handle edge cases:**
  - Empty clause_text: Return empty list
  - No matches above threshold: Return empty list
  - Log search parameters and result count

**Acceptance Criteria**:
- Function signature matches specification exactly
- Embeds clause_text using embed_text()
- Uses LegalRule.embedding.cosine_distance() for similarity
- Converts distance to similarity: `1.0 - distance`
- State filtering logic correct:
  - state provided → state-specific OR central (NULL) rules
  - state=None → only central (NULL) rules
- Filters by similarity_threshold (>= threshold)
- Limits to top_k results
- Returns list[LegalRuleSearchResult] with similarity scores
- Empty query returns empty list
- All parameters logged for debugging

---

## Task 6: Create Seed Data JSON
**File**: `backend/db/legal_kb/seed_data/legal_rules.json`

**Actions**:
- Create JSON array with all 20 sample legal rules from spec appendix
- **Structure for each rule:**
  ```json
  {
    "state": null,
    "act_name": "Model Tenancy Act 2021",
    "section_reference": "Section 7(1)",
    "rule_text": "The security deposit shall not exceed two months' rent..."
  }
  ```

- **Include all 20 rules:**
  1. Model Tenancy Act 2021 - Security Deposit - Section 7(1)
  2. Model Tenancy Act 2021 - Termination Notice - Section 21(1)
  3. Model Tenancy Act 2021 - Landlord Maintenance - Section 13(1)
  4. Model Tenancy Act 2021 - Tenant Maintenance - Section 15(2)
  5. Model Tenancy Act 2021 - Rent Payment - Section 8(1)
  6. Model Tenancy Act 2021 - Rent Increase Cap - Section 9(1)
  7. Model Tenancy Act 2021 - Subletting Prohibition - Section 14(1)
  8. Model Tenancy Act 2021 - Eviction Grounds - Section 22(2)
  9. Model Tenancy Act 2021 - Renewal Rights - Section 19(1)
  10. Model Tenancy Act 2021 - Inspection Rights - Section 16(1)
  11. Model Tenancy Act 2021 - Deposit Refund Timeline - Section 23(1)
  12. Model Tenancy Act 2021 - Damage Liability - Section 20(1)
  13. Indian Contract Act 1872 - Breach Compensation - Section 73
  14. Indian Contract Act 1872 - Liquidated Damages - Section 74
  15. Indian Contract Act 1872 - Frustration of Contract - Section 56
  16. Maharashtra Rent Control Act 1999 - Security Deposit (state: "MH")
  17. Karnataka Rent Control Act - Eviction (state: "KA")
  18. Delhi Rent Control Act - Subletting (state: "DL")
  19. Tamil Nadu Buildings (Lease and Rent Control) Act - Rent Increase (state: "TN")
  20. Model Tenancy Act 2021 - Dispute Resolution - Section 24(1)

- **Rule text requirements:**
  - Each rule_text must be complete, self-contained explanation
  - Minimum 50 words per rule
  - Include legal context and practical implications
  - Use Indian legal terminology
  - State-specific rules have state codes: "MH", "KA", "DL", "TN"
  - Central laws have state: null

**Acceptance Criteria**:
- JSON file is valid and parseable
- Exactly 20 rules present
- 16 central laws (state: null)
- 4 state-specific laws (MH, KA, DL, TN)
- Each rule has all 4 required fields (state, act_name, section_reference, rule_text)
- Rule text is substantial (50+ words each)
- Covers Model Tenancy Act 2021 and Indian Contract Act 1872
- No duplicate (act_name, section_reference, state) combinations

---

## Task 7: Create Seed Data README
**File**: `backend/db/legal_kb/seed_data/README.md`

**Actions**:
- Create README with SAMPLE DATA disclaimer
- **Include exact text:**
  ```markdown
  # Legal Rules Knowledge Base - Seed Data

  ## ⚠️ SAMPLE DATA DISCLAIMER

  **The legal rules in this directory are SAMPLE DATA ONLY and are NOT suitable for production use.**

  This seed dataset contains simplified, illustrative legal provisions for development and testing purposes. These samples:

  - Are not comprehensive legal references
  - May be outdated or incomplete
  - Are not validated by legal professionals
  - Should NEVER be used for actual contract analysis in production

  ## Production Replacement Checklist

  Before deploying to production, you MUST:

  - [ ] Replace with professionally curated legal database
  - [ ] Validate all provisions with qualified legal counsel
  - [ ] Implement jurisdiction-specific rule sets for all supported states
  - [ ] Add regular update mechanisms for legal changes
  - [ ] Include metadata (effective dates, amendment tracking, case law references)
  - [ ] Obtain proper licensing for commercial legal databases if used

  ## Data Sources for Production

  Consider these authoritative sources for production legal data:

  - **India Code** (https://www.indiacode.nic.in/) - Official central and state legislation
  - **Legislative Department, Ministry of Law and Justice** - Acts and amendments
  - **State Government Gazettes** - State-specific regulations
  - **Commercial Legal Databases** - LexisNexis, Manupatra, SCC Online (requires licensing)

  ## Current Sample Data

  - **Source**: Manually created illustrative examples
  - **Coverage**: Model Tenancy Act 2021, Indian Contract Act 1872, 4 state-specific samples
  - **Last Updated**: [Generated at seed time]
  - **Entry Count**: 20 sample rules
  ```

**Acceptance Criteria**:
- README.md created in seed_data/ directory
- Contains prominent ⚠️ SAMPLE DATA DISCLAIMER
- Lists production replacement checklist with checkboxes
- Includes links to authoritative Indian legal data sources
- Documents current sample data scope and limitations
- Professional tone appropriate for legal compliance documentation

---

## Task 8: Implement Seed Script
**File**: `backend/db/legal_kb/seed_legal_kb.py`

**Actions**:
- Add imports:
  ```python
  import json
  import asyncio
  import logging
  from pathlib import Path
  from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
  from sqlalchemy.orm import sessionmaker
  from sqlalchemy import select
  from backend.db.legal_kb.models import LegalRule, LegalRuleData
  from backend.db.legal_kb.embeddings import embed_batch
  import os
  ```

- **Implement load_seed_data() -> list[LegalRuleData]:**
  - Load `backend/db/legal_kb/seed_data/legal_rules.json`
  - Parse JSON array
  - Validate each entry with LegalRuleData model
  - Return list[LegalRuleData]
  - Raise FileNotFoundError if JSON missing
  - Raise ValueError if JSON invalid

- **Implement rule_exists() check:**
  ```python
  async def rule_exists(
      db: AsyncSession,
      act_name: str,
      section_reference: str,
      state: Optional[str]
  ) -> bool:
      """Check if rule already exists (idempotency)."""
      query = select(LegalRule).where(
          and_(
              LegalRule.act_name == act_name,
              LegalRule.section_reference == section_reference,
              LegalRule.state == state
          )
      )
      result = await db.execute(query)
      return result.scalar_one_or_none() is not None
  ```

- **Implement seed_legal_kb() main function:**
  1. **Log SAMPLE DATA warning banner:**
     ```
     ============================================================
     WARNING: Loading SAMPLE legal data for development only
     ============================================================
     ```
  2. Load seed data via load_seed_data()
  3. Create database session
  4. Initialize counters: inserted=0, skipped=0, failed=0
  5. **For each rule:**
     - Check if exists via rule_exists()
     - If exists: increment skipped, continue
     - If not exists:
       - Embed rule_text via embed_text()
       - Create LegalRule with embedding
       - Add to session
       - Increment inserted
     - On error: log error, increment failed, continue
  6. Commit session
  7. **Log final summary:**
     ```
     Legal KB seeding complete:
     - Inserted: X rules
     - Skipped (already exist): Y rules
     - Failed: Z rules
     ```
  8. **If inserted > 0, log VACUUM ANALYZE reminder:**
     ```
     REMINDER: Run 'VACUUM ANALYZE legal_rules;' to optimize IVFFlat index
     ```

- **Add __main__ block:**
  ```python
  if __name__ == "__main__":
      asyncio.run(seed_legal_kb())
  ```

**Acceptance Criteria**:
- Script runnable as `python -m backend.db.legal_kb.seed_legal_kb`
- Logs SAMPLE DATA warning at start
- Loads legal_rules.json successfully
- Checks idempotency: skips existing rules by (act_name, section_reference, state)
- Embeds rule_text for each new rule
- Inserts new rules with embeddings
- Individual failures don't crash whole script
- Logs inserted/skipped/failed counts
- Logs VACUUM ANALYZE reminder if any rows inserted
- Returns success exit code 0

---

## Task 9: Create Test Fixtures
**File**: `backend/tests/fixtures/test_legal_rules.json`

**Actions**:
- Create JSON array with 5 test legal rules
- **Structure matches seed data format**
- **Include diverse test cases:**
  1. Central law (state: null) - Model Tenancy Act 2021
  2. Central law (state: null) - Indian Contract Act 1872
  3. State-specific (state: "MH") - Maharashtra rule
  4. State-specific (state: "KA") - Karnataka rule
  5. Central law (state: null) - Different section

- **Requirements:**
  - All fields present (state, act_name, section_reference, rule_text)
  - Rule text 50+ words each
  - No duplicate combinations
  - Mix of rental and contract law topics
  - Valid JSON format

**Acceptance Criteria**:
- backend/tests/fixtures/ directory created
- test_legal_rules.json file created
- Exactly 5 test rules
- 3 central laws (state: null), 2 state-specific (MH, KA)
- Valid JSON parseable by json.load()
- All rules pass LegalRuleData validation

---

## Task 10: Write Legal KB Unit Tests
**Files**: 
- `backend/tests/test_legal_kb.py`
- `backend/tests/test_legal_search.py`

**Actions**:

### test_legal_kb.py (Infrastructure & Embeddings Tests)

- **TC-1: Test pgvector Extension Enabled**
  - Query database: `SELECT * FROM pg_extension WHERE extname = 'vector'`
  - Assert extension exists
  - Assert version is present

- **TC-2: Test Legal Rules Table Schema**
  - Query information_schema for legal_rules table
  - Assert all 8 columns exist with correct types
  - Assert UNIQUE constraint on (act_name, section_reference, state)
  - Assert indexes exist on state, act_name, embedding

- **TC-3: Test embed_text() Single Text**
  - Call embed_text() with sample text
  - Assert returns list[float]
  - Assert length is exactly 1536
  - Assert all values are floats
  - Assert not all values are zero

- **TC-4: Test embed_text() Dimension Validation**
  - Mock OpenAI client to return wrong dimension (e.g., 768)
  - Call embed_text()
  - Assert raises ValueError with "1536" in message

- **TC-5: Test embed_batch() Multiple Texts**
  - Call embed_batch() with 5 texts
  - Assert returns list of 5 embeddings
  - Assert each embedding is 1536 dimensions
  - Verify embeddings are different (not duplicates)

- **TC-6: Test embed_batch() Batching Logic**
  - Mock embed_text() to track calls
  - Call embed_batch() with 250 texts, batch_size=100
  - Assert embed_text() called 250 times
  - Assert processed in batches (verify batch boundaries)

- **TC-7: Test Seed Script Load**
  - Run seed_legal_kb() (with test database)
  - Assert 20 rules inserted
  - Query database: assert count(*) = 20
  - Assert no errors logged

- **TC-8: Test Seed Script Idempotency**
  - Run seed_legal_kb() twice
  - First run: assert 20 inserted
  - Second run: assert 0 inserted, 20 skipped
  - Assert no duplicates in database

### test_legal_search.py (Search Tests)

- **TC-9: Test Basic Similarity Search**
  - Insert test rule: "Security deposit shall not exceed two months' rent"
  - Search with query: "What is the maximum security deposit?"
  - Assert returns 1 result
  - Assert similarity > 0.7
  - Assert act_name and section_reference correct

- **TC-10: Test State Filtering - State Provided**
  - Insert 3 rules: central (state=NULL), MH-specific, KA-specific
  - Search with state="MH"
  - Assert returns central + MH rules (2 results)
  - Assert KA rule NOT returned

- **TC-11: Test State Filtering - No State**
  - Insert 3 rules: central (state=NULL), MH-specific, KA-specific
  - Search with state=None
  - Assert returns ONLY central rule (1 result)
  - Assert MH and KA rules NOT returned

- **TC-12: Test top_k Limit**
  - Insert 10 similar rules
  - Search with top_k=3
  - Assert returns exactly 3 results
  - Assert ordered by similarity (highest first)

- **TC-13: Test Similarity Threshold**
  - Insert 5 rules with varying similarity to query
  - Search with similarity_threshold=0.8
  - Assert only rules with similarity >= 0.8 returned
  - Assert lower-similarity rules excluded

- **TC-14: Test No Matches Case**
  - Insert rules about rental contracts
  - Search with completely unrelated query: "software licensing terms"
  - Assert returns empty list (no results above threshold)

- **TC-15: Test Empty Query**
  - Call search_legal_rules() with empty string
  - Assert returns empty list
  - Assert no error raised

**Test Infrastructure:**
- Use pytest fixtures for database setup/teardown
- Mock OpenAI API calls (no real API calls in tests)
- Use test_legal_rules.json fixture data
- Test database should be separate from dev database
- All tests should clean up after themselves

**Acceptance Criteria**:
- All 15 test cases implemented (TC-1 through TC-15)
- Tests use pytest framework
- Zero real OpenAI API calls (all mocked)
- Tests use test_legal_rules.json fixture
- Database fixtures properly set up/torn down
- All tests pass independently and in suite
- Coverage includes: extension, schema, embeddings, search, seed script, state filtering, edge cases

---

## Success Criteria (All Tasks Complete)

- [ ] Module structure created: backend/db/legal_kb/ with all files
- [ ] Migration 003 creates legal_rules table with pgvector, indexes, constraints
- [ ] Models defined: LegalRule (SQLAlchemy), LegalRuleData, LegalRuleSearchResult (Pydantic)
- [ ] Embeddings module: get_openai_client(), embed_text(), embed_batch() implemented
- [ ] Search function: search_legal_rules() with state filtering and similarity scoring
- [ ] Seed data: 20 sample legal rules in JSON with README disclaimer
- [ ] Seed script: loads data, checks idempotency, logs progress
- [ ] Test fixtures: 5-entry test_legal_rules.json created
- [ ] All 15 test cases pass (TC-1 through TC-15)
- [ ] Zero real API calls in test suite
- [ ] Migration runs successfully: `alembic upgrade head`
- [ ] Seed script runs successfully: `python -m backend.db.legal_kb.seed_legal_kb`
- [ ] Module ready for Stage 4 integration (classify_clauses can call search_legal_rules)

---

## Notes

**Dependency for Stage 5B:**
- embeddings.py will be refactored to backend/rag/embeddings.py in Stage 5B
- Do NOT move it now - Stage 5B spec handles the refactor
- Build it in backend/db/legal_kb/embeddings.py as specified

**pgvector Index Note:**
- IVFFlat index requires VACUUM ANALYZE for optimal performance
- Seed script reminds user to run this after seeding
- In production, run after bulk inserts

**State Filtering Logic:**
- state=None → central laws only (state IS NULL)
- state="MH" → central laws OR MH laws (state IS NULL OR state = 'MH')
- This ensures central laws apply everywhere, state laws supplement

**OpenAI Embedding Model:**
- text-embedding-3-small produces 1536-dimensional vectors
- Must validate dimension to catch API changes
- More cost-effective than text-embedding-3-large for this use case
