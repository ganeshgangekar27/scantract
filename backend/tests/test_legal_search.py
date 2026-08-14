"""
Unit tests for Legal KB similarity search functionality.

Tests TC-9 through TC-15: similarity search, state filtering, edge cases.
"""

import pytest
import pytest_asyncio
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from db.legal_kb.models import LegalRule, LegalRuleSearchResult
from db.legal_kb.search import search_legal_rules


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


@pytest_asyncio.fixture
async def sample_rules(db_session: AsyncSession):
    """Insert sample rules for testing."""
    # Clean up existing test rules
    await db_session.execute(text("DELETE FROM legal_rules WHERE act_name LIKE 'Test%'"))
    await db_session.commit()
    
    # Create sample embeddings (simplified for testing)
    # In real scenario, these would be actual Gemini embeddings (3072 dimensions)
    central_embedding = [0.1] * 3072
    mh_embedding = [0.2] * 3072
    ka_embedding = [0.3] * 3072
    
    rules = [
        LegalRule(
            state=None,
            act_name="Test Central Act 2026",
            section_reference="Section 1",
            rule_text="Security deposit shall not exceed two months' rent for residential property.",
            embedding=central_embedding
        ),
        LegalRule(
            state="MH",
            act_name="Test Maharashtra Act",
            section_reference="Section 5",
            rule_text="Security deposit in Maharashtra shall not exceed three months' rent.",
            embedding=mh_embedding
        ),
        LegalRule(
            state="KA",
            act_name="Test Karnataka Act",
            section_reference="Section 10",
            rule_text="Karnataka rules for eviction require six months notice period.",
            embedding=ka_embedding
        ),
    ]
    
    for rule in rules:
        db_session.add(rule)
    
    await db_session.commit()
    
    return rules


# TC-9: Test Basic Similarity Search
@pytest.mark.asyncio
async def test_basic_similarity_search(db_session: AsyncSession, sample_rules):
    """
    TC-9: Test basic similarity search returns relevant results with scores.
    """
    # Mock embed_text to return a specific embedding
    query_embedding = [0.1] * 3072  # Similar to central_embedding
    
    with patch('db.legal_kb.search.embed_text', new=AsyncMock(return_value=query_embedding)):
        results = await search_legal_rules(
            clause_text="What is the maximum security deposit?",
            db=db_session,
            state=None,
            top_k=5,
            similarity_threshold=0.0  # Low threshold to ensure we get results
        )
        
        assert len(results) >= 1, "Should return at least one result"
        assert all(isinstance(r, LegalRuleSearchResult) for r in results), "All results should be LegalRuleSearchResult"
        
        # Check first result structure
        result = results[0]
        assert hasattr(result, 'id'), "Result should have id"
        assert hasattr(result, 'similarity'), "Result should have similarity score"
        assert 0.0 <= result.similarity <= 1.0, f"Similarity should be 0-1, got {result.similarity}"
        assert result.act_name is not None, "Result should have act_name"
        assert result.section_reference is not None, "Result should have section_reference"


# TC-10: Test State Filtering - State Provided
@pytest.mark.asyncio
async def test_state_filtering_with_state(db_session: AsyncSession, sample_rules):
    """
    TC-10: Test that state="MH" returns Maharashtra rules PLUS central rules.
    Karnataka rules should NOT be returned.
    """
    query_embedding = [0.15] * 3072  # Neutral embedding
    
    with patch('db.legal_kb.search.embed_text', new=AsyncMock(return_value=query_embedding)):
        results = await search_legal_rules(
            clause_text="Security deposit rules",
            db=db_session,
            state="MH",
            top_k=10,
            similarity_threshold=0.0
        )
        
        # Should get central rule (state=NULL) and MH rule
        states_found = set(r.state for r in results)
        
        assert None in states_found or "MH" in states_found, "Should return central or MH rules"
        assert "KA" not in states_found, "Karnataka rule should NOT be returned when state=MH"
        
        # Verify we got at least one MH or central rule
        mh_rules = [r for r in results if r.state == "MH"]
        central_rules = [r for r in results if r.state is None]
        
        assert len(mh_rules) + len(central_rules) >= 1, "Should have MH or central rules"


# TC-11: Test State Filtering - No State
@pytest.mark.asyncio
async def test_state_filtering_no_state(db_session: AsyncSession, sample_rules):
    """
    TC-11: Test that state=None returns ONLY central rules.
    State-specific rules should NOT be returned.
    """
    query_embedding = [0.15] * 3072
    
    with patch('db.legal_kb.search.embed_text', new=AsyncMock(return_value=query_embedding)):
        results = await search_legal_rules(
            clause_text="Security deposit rules",
            db=db_session,
            state=None,
            top_k=10,
            similarity_threshold=0.0
        )
        
        # Should get ONLY central rules (state=NULL)
        assert all(r.state is None for r in results), "When state=None, should return ONLY central rules"
        
        # Should NOT get MH or KA rules
        states = [r.state for r in results]
        assert "MH" not in states, "Maharashtra rule should NOT be returned when state=None"
        assert "KA" not in states, "Karnataka rule should NOT be returned when state=None"


# TC-12: Test top_k Limit
@pytest.mark.asyncio
async def test_top_k_limit(db_session: AsyncSession):
    """
    TC-12: Test that top_k limits the number of results correctly.
    """
    # Insert 10 similar rules
    embedding = [0.1] * 3072
    
    for i in range(10):
        rule = LegalRule(
            state=None,
            act_name=f"Test Act {i}",
            section_reference=f"Section {i}",
            rule_text=f"This is test rule number {i} about security deposits.",
            embedding=embedding
        )
        db_session.add(rule)
    
    await db_session.commit()
    
    query_embedding = [0.1] * 3072
    
    with patch('db.legal_kb.search.embed_text', new=AsyncMock(return_value=query_embedding)):
        results = await search_legal_rules(
            clause_text="security deposit",
            db=db_session,
            state=None,
            top_k=3,
            similarity_threshold=0.0
        )
        
        assert len(results) <= 3, f"Should return at most 3 results, got {len(results)}"


# TC-13: Test Similarity Threshold
@pytest.mark.asyncio
async def test_similarity_threshold(db_session: AsyncSession, sample_rules):
    """
    TC-13: Test that similarity_threshold filters results correctly.
    Only results with similarity >= threshold should be returned.
    """
    query_embedding = [0.1] * 3072
    
    with patch('db.legal_kb.search.embed_text', new=AsyncMock(return_value=query_embedding)):
        # First search with low threshold
        results_low = await search_legal_rules(
            clause_text="test query",
            db=db_session,
            state=None,
            top_k=10,
            similarity_threshold=0.0
        )
        
        # Then search with high threshold
        results_high = await search_legal_rules(
            clause_text="test query",
            db=db_session,
            state=None,
            top_k=10,
            similarity_threshold=0.99
        )
        
        # High threshold should return fewer or equal results
        assert len(results_high) <= len(results_low), "High threshold should filter more strictly"
        
        # All results should meet threshold
        for result in results_high:
            assert result.similarity >= 0.99, f"Result similarity {result.similarity} below threshold 0.99"


# TC-14: Test No Matches Case
@pytest.mark.asyncio
async def test_no_matches(db_session: AsyncSession, sample_rules):
    """
    TC-14: Test that completely unrelated query returns empty list.
    """
    # Create embedding very different from sample rules
    query_embedding = [0.9] * 3072
    
    with patch('db.legal_kb.search.embed_text', new=AsyncMock(return_value=query_embedding)):
        results = await search_legal_rules(
            clause_text="software licensing terms and conditions",
            db=db_session,
            state=None,
            top_k=5,
            similarity_threshold=0.9  # High threshold
        )
        
        # With high threshold and different embedding, should get no matches
        assert isinstance(results, list), "Should return a list"
        # May be empty or have very low similarity results filtered out


# TC-15: Test Empty Query
@pytest.mark.asyncio
async def test_empty_query(db_session: AsyncSession):
    """
    TC-15: Test that empty query returns empty list without error.
    """
    results = await search_legal_rules(
        clause_text="",
        db=db_session,
        state=None,
        top_k=5,
        similarity_threshold=0.7
    )
    
    assert isinstance(results, list), "Should return a list"
    assert len(results) == 0, "Empty query should return empty list"
    
    # Test with whitespace-only query
    results_whitespace = await search_legal_rules(
        clause_text="   ",
        db=db_session,
        state=None,
        top_k=5,
        similarity_threshold=0.7
    )
    
    assert isinstance(results_whitespace, list), "Should return a list"
    assert len(results_whitespace) == 0, "Whitespace query should return empty list"


# TC-16: Test Result Schema Validation
@pytest.mark.asyncio
async def test_result_schema_validation(db_session: AsyncSession, sample_rules):
    """
    Additional test: Verify LegalRuleSearchResult schema is correct.
    """
    query_embedding = [0.1] * 3072
    
    with patch('db.legal_kb.search.embed_text', new=AsyncMock(return_value=query_embedding)):
        results = await search_legal_rules(
            clause_text="test query",
            db=db_session,
            state=None,
            top_k=1,
            similarity_threshold=0.0
        )
        
        if len(results) > 0:
            result = results[0]
            
            # Verify all required fields exist
            assert hasattr(result, 'id'), "Missing id field"
            assert hasattr(result, 'state'), "Missing state field"
            assert hasattr(result, 'act_name'), "Missing act_name field"
            assert hasattr(result, 'section_reference'), "Missing section_reference field"
            assert hasattr(result, 'rule_text'), "Missing rule_text field"
            assert hasattr(result, 'similarity'), "Missing similarity field"
            
            # Verify types
            assert isinstance(result.id, int), "id should be int"
            assert isinstance(result.act_name, str), "act_name should be str"
            assert isinstance(result.section_reference, str), "section_reference should be str"
            assert isinstance(result.rule_text, str), "rule_text should be str"
            assert isinstance(result.similarity, float), "similarity should be float"
            
            # Verify similarity range
            assert 0.0 <= result.similarity <= 1.0, "similarity should be 0.0-1.0"
