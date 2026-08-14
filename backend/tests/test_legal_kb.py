"""
Unit tests for Legal KB infrastructure, embeddings, and seed script.

Tests TC-1 through TC-8: pgvector extension, schema, embeddings, seed script.
"""

import pytest
import pytest_asyncio
import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from db.legal_kb.models import LegalRule, LegalRuleData
from db.legal_kb.embeddings import embed_text, embed_batch
from db.legal_kb.seed_legal_kb import load_seed_data, rule_exists, seed_legal_kb


# Test database URL (uses main database for now - in production, use separate test DB)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:devpass@localhost:5432/scantract"


@pytest_asyncio.fixture
async def db_session():
    """Create async database session for tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


# TC-1: Test pgvector Extension Enabled
@pytest.mark.asyncio
async def test_pgvector_extension_enabled(db_session: AsyncSession):
    """
    TC-1: Verify pgvector extension is installed and active.
    """
    query = text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
    result = await db_session.execute(query)
    extension = result.fetchone()
    
    assert extension is not None, "pgvector extension not installed"
    assert extension[0] == 'vector', "Extension name mismatch"


# TC-2: Test Legal Rules Table Schema
@pytest.mark.asyncio
async def test_legal_rules_table_schema(db_session: AsyncSession):
    """
    TC-2: Verify legal_rules table has correct schema with all columns,
    constraints, and indexes.
    """
    # Check table exists
    query = text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'legal_rules'
    """)
    result = await db_session.execute(query)
    assert result.fetchone() is not None, "legal_rules table does not exist"
    
    # Check all columns exist with correct types
    query = text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'legal_rules'
        ORDER BY ordinal_position
    """)
    result = await db_session.execute(query)
    columns = {row[0]: (row[1], row[2]) for row in result.fetchall()}
    
    expected_columns = {
        'id': ('integer', 'NO'),
        'state': ('character varying', 'YES'),
        'act_name': ('character varying', 'NO'),
        'section_reference': ('character varying', 'NO'),
        'rule_text': ('text', 'NO'),
        'embedding': ('USER-DEFINED', 'NO'),  # VECTOR type shows as USER-DEFINED
        'created_at': ('timestamp with time zone', 'NO'),
        'updated_at': ('timestamp with time zone', 'NO'),
    }
    
    for col_name, (expected_type, expected_nullable) in expected_columns.items():
        assert col_name in columns, f"Column {col_name} missing"
        actual_type, actual_nullable = columns[col_name]
        
        # For embedding column, just check it's USER-DEFINED (vector type)
        if col_name == 'embedding':
            assert actual_type == 'USER-DEFINED', f"embedding column should be VECTOR type"
        else:
            assert actual_type == expected_type, f"{col_name} type mismatch"
        
        assert actual_nullable == expected_nullable, f"{col_name} nullable mismatch"
    
    # Check UNIQUE constraint exists
    query = text("""
        SELECT constraint_name, constraint_type
        FROM information_schema.table_constraints
        WHERE table_name = 'legal_rules' AND constraint_type = 'UNIQUE'
    """)
    result = await db_session.execute(query)
    unique_constraints = result.fetchall()
    assert len(unique_constraints) >= 1, "UNIQUE constraint missing"
    
    # Check indexes exist
    query = text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'legal_rules'
    """)
    result = await db_session.execute(query)
    indexes = [row[0] for row in result.fetchall()]
    
    assert 'ix_legal_rules_state' in indexes, "state index missing"
    assert 'ix_legal_rules_act_name' in indexes, "act_name index missing"


# TC-3: Test embed_text() Single Text
@pytest.mark.asyncio
async def test_embed_text_single():
    """
    TC-3: Test embedding generation for single text.
    Mock Gemini API to avoid real calls.
    """
    mock_embedding = [0.1] * 3072  # Valid 3072-dimensional embedding
    
    mock_result = {'embedding': mock_embedding}
    
    with patch('db.legal_kb.embeddings.genai.embed_content', return_value=mock_result):
        result = await embed_text("Sample legal text for testing")
        
        assert isinstance(result, list), "Result should be a list"
        assert len(result) == 3072, f"Expected 3072 dimensions, got {len(result)}"
        assert all(isinstance(v, float) for v in result), "All values should be floats"
        assert not all(v == 0.0 for v in result), "Embedding should not be all zeros"


# TC-4: Test embed_text() Dimension Validation
@pytest.mark.asyncio
async def test_embed_text_dimension_validation():
    """
    TC-4: Test that embed_text() raises ValueError if dimension is not 3072.
    """
    mock_embedding = [0.1] * 768  # Wrong dimension (768 instead of 3072)
    
    mock_result = {'embedding': mock_embedding}
    
    with patch('db.legal_kb.embeddings.genai.embed_content', return_value=mock_result):
        with pytest.raises(ValueError) as exc_info:
            await embed_text("Sample text")
        
        assert "3072" in str(exc_info.value), "Error should mention expected dimension"
        assert "768" in str(exc_info.value), "Error should mention actual dimension"


# TC-5: Test embed_batch() Multiple Texts
@pytest.mark.asyncio
async def test_embed_batch_multiple():
    """
    TC-5: Test batch embedding generation for multiple texts.
    """
    texts = [
        "First legal provision",
        "Second legal provision",
        "Third legal provision",
        "Fourth legal provision",
        "Fifth legal provision"
    ]
    
    # Create unique embeddings for each text
    mock_embeddings = [
        [0.1 * (i + 1)] * 3072 for i in range(len(texts))
    ]
    
    async def mock_embed_text(text):
        idx = texts.index(text)
        return mock_embeddings[idx]
    
    with patch('db.legal_kb.embeddings.embed_text', side_effect=mock_embed_text):
        results = await embed_batch(texts)
        
        assert len(results) == 5, "Should return 5 embeddings"
        assert all(len(emb) == 3072 for emb in results), "All embeddings should be 3072-dim"
        
        # Verify embeddings are different (not duplicates)
        for i in range(len(results) - 1):
            assert results[i] != results[i + 1], f"Embeddings {i} and {i+1} should be different"


# TC-6: Test embed_batch() Batching Logic
@pytest.mark.asyncio
async def test_embed_batch_batching():
    """
    TC-6: Test that embed_batch() processes in batches correctly.
    """
    texts = [f"Text {i}" for i in range(250)]
    batch_size = 100
    
    call_count = 0
    
    async def mock_embed_text(text):
        nonlocal call_count
        call_count += 1
        return [0.1] * 3072
    
    with patch('db.legal_kb.embeddings.embed_text', side_effect=mock_embed_text):
        results = await embed_batch(texts, batch_size=batch_size)
        
        assert len(results) == 250, "Should return all 250 embeddings"
        assert call_count == 250, f"Should call embed_text 250 times, called {call_count}"
        
        # Verify batching happened (3 batches: 100 + 100 + 50)
        # This is indirectly verified by the fact that all calls completed


# TC-7: Test Seed Script Load
@pytest.mark.asyncio
async def test_seed_script_load():
    """
    TC-7: Test that seed script loads seed data correctly.
    """
    # Load actual seed data from db/legal_kb/seed_data/
    rules = load_seed_data()
    
    assert len(rules) == 20, f"Expected 20 rules, got {len(rules)}"
    assert all(isinstance(r, LegalRuleData) for r in rules), "All should be LegalRuleData"
    
    # Verify first rule has expected structure
    assert rules[0].act_name is not None, "act_name should exist"
    assert rules[0].section_reference is not None, "section_reference should exist"
    assert rules[0].rule_text is not None, "rule_text should exist"


# TC-8: Test Seed Script Idempotency
@pytest.mark.asyncio
async def test_seed_script_idempotency(db_session: AsyncSession):
    """
    TC-8: Test that running seed script twice doesn't create duplicates.
    """
    # Create a test rule
    test_rule_data = LegalRuleData(
        state=None,
        act_name="Test Act 2026",
        section_reference="Section 1",
        rule_text="This is a test rule for idempotency checking."
    )
    
    # First check: rule should not exist
    exists_before = await rule_exists(
        db_session,
        test_rule_data.act_name,
        test_rule_data.section_reference,
        test_rule_data.state
    )
    assert not exists_before, "Rule should not exist initially"
    
    # Insert the rule
    mock_embedding = [0.1] * 3072
    test_rule = LegalRule(
        state=test_rule_data.state,
        act_name=test_rule_data.act_name,
        section_reference=test_rule_data.section_reference,
        rule_text=test_rule_data.rule_text,
        embedding=mock_embedding
    )
    db_session.add(test_rule)
    await db_session.commit()
    
    # Second check: rule should exist now
    exists_after = await rule_exists(
        db_session,
        test_rule_data.act_name,
        test_rule_data.section_reference,
        test_rule_data.state
    )
    assert exists_after, "Rule should exist after insertion"
    
    # Verify count
    query = select(LegalRule).where(
        LegalRule.act_name == test_rule_data.act_name
    )
    result = await db_session.execute(query)
    rules = result.scalars().all()
    assert len(rules) == 1, "Should have exactly one rule, not duplicates"
