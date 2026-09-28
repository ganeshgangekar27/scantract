"""
Tests for explanation response parser.

Ensures:
- Invalid/short responses ({}), ({\n\n}), "null", short strings) are rejected and return None
- Valid JSON-wrapped explanations are unwrapped
- Plain text explanations pass through
"""
import pytest
import pytest_asyncio
from pathlib import Path
import sys
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db.models import RiskFinding
from app.llm.generate_explanations import generate_explanation

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:devpass@localhost:5432/scantract"


@pytest_asyncio.fixture
async def db_session():
    """Create async database session for tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_parser_rejects_empty_braces(db_session: AsyncSession):
    """Parser should reject '{}' and return None."""
    finding = RiskFinding(
        contract_id=1,
        finding_type="risky_clause",
        clause_id=1,
        severity="high",
        reason="Test",
        triggering_rule_or_corpus="Test"
    )
    
    with patch("app.llm.generate_explanations.call_llm", new=AsyncMock(return_value=("{}", 100))):
        result = await generate_explanation(finding, db_session)
        assert result is None


@pytest.mark.asyncio
async def test_parser_rejects_braces_with_newlines(db_session: AsyncSession):
    """Parser should reject '{\n\n}' and return None."""
    finding = RiskFinding(
        contract_id=1,
        finding_type="risky_clause",
        clause_id=1,
        severity="high",
        reason="Test",
        triggering_rule_or_corpus="Test"
    )
    
    with patch("app.llm.generate_explanations.call_llm", new=AsyncMock(return_value=("{\n\n}", 100))):
        result = await generate_explanation(finding, db_session)
        assert result is None


@pytest.mark.asyncio
async def test_parser_rejects_null_string(db_session: AsyncSession):
    """Parser should reject 'null' and return None."""
    finding = RiskFinding(
        contract_id=1,
        finding_type="risky_clause",
        clause_id=1,
        severity="high",
        reason="Test",
        triggering_rule_or_corpus="Test"
    )
    
    with patch("app.llm.generate_explanations.call_llm", new=AsyncMock(return_value=("null", 100))):
        result = await generate_explanation(finding, db_session)
        assert result is None


@pytest.mark.asyncio
async def test_parser_accepts_valid_json_wrapped(db_session: AsyncSession):
    """Parser should unwrap valid JSON {"explanation": "..."}."""
    finding = RiskFinding(
        contract_id=1,
        finding_type="risky_clause",
        clause_id=1,
        severity="high",
        reason="Test",
        triggering_rule_or_corpus="Test"
    )
    
    json_response = '{"explanation": "This clause differs from standard practice because it requires three months rent as security deposit, which exceeds the two-month limit set by the Model Tenancy Act."}'
    
    with patch("app.llm.generate_explanations.call_llm", new=AsyncMock(return_value=(json_response, 100))):
        with patch.object(db_session, 'execute', new=AsyncMock()):
            with patch.object(db_session, 'commit', new=AsyncMock()):
                result = await generate_explanation(finding, db_session)
                assert result is not None
                assert "This clause differs" in result
                assert "{" not in result  # Unwrapped


@pytest.mark.asyncio
async def test_parser_accepts_plain_text(db_session: AsyncSession):
    """Parser should pass through plain text explanation."""
    finding = RiskFinding(
        contract_id=1,
        finding_type="risky_clause",
        clause_id=1,
        severity="high",
        reason="Test",
        triggering_rule_or_corpus="Test"
    )
    
    plain_text = "This clause differs from standard practice because it requires three months rent as security deposit."
    
    with patch("app.llm.generate_explanations.call_llm", new=AsyncMock(return_value=(plain_text, 100))):
        with patch.object(db_session, 'execute', new=AsyncMock()):
            with patch.object(db_session, 'commit', new=AsyncMock()):
                result = await generate_explanation(finding, db_session)
                assert result == plain_text
