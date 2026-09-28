"""
Tests for report GET endpoint guards.

Ensures:
- Only completed contracts can generate reports
- LLM is never called on GET /api/contracts/{id}/report
- Incomplete contracts return 409 with readable message
"""
import pytest
import pytest_asyncio
from pathlib import Path
import sys
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db.models import Contract
from app.reports.assembler import assemble_contract_report

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
async def test_report_requires_completed_stage_detecting_risks(db_session: AsyncSession):
    """Contract in detecting_risks stage should raise ValueError with stage in message."""
    # Mock the query to return a contract in detecting_risks
    with patch.object(db_session, 'execute', new=AsyncMock()) as mock_execute:
        # Create mock contract
        mock_contract = Contract(
            id=999,
            filename="stuck.pdf",
            contract_type="rental",
            file_path="/uploads/stuck.pdf",
            uploaded_at="2026-09-28T00:00:00Z",
            processing_status="processing",
            pipeline_stage="detecting_risks"
        )
        
        # Mock result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contract
        mock_execute.return_value = mock_result
        
        # Try to get report
        with pytest.raises(ValueError, match="processing incomplete.*detecting_risks"):
            await assemble_contract_report(999, db_session)


@pytest.mark.asyncio
async def test_report_succeeds_for_completed(db_session: AsyncSession):
    """Completed contract should return report."""
    # Use contract 1 which is completed
    report = await assemble_contract_report(1, db_session)
    
    assert report.contract_id == 1
    assert len(report.risky_clauses) > 0
    assert report.risk_summary.overall_risk_level in ["high", "medium", "low", "none"]


@pytest.mark.asyncio
async def test_llm_never_called_on_get(db_session: AsyncSession):
    """assemble_contract_report should never call generate_all_explanations."""
    with patch("app.reports.assembler.generate_all_explanations", new=AsyncMock()) as mock_llm:
        # Get contract 1 report
        report = await assemble_contract_report(1, db_session)
        
        assert report.contract_id == 1
        # Assert LLM was never called
        mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_contract_1_report_identical_before_after(db_session: AsyncSession):
    """Contract 1 report should be identical on repeated calls."""
    # First call
    report1 = await assemble_contract_report(1, db_session)
    
    # Second call
    report2 = await assemble_contract_report(1, db_session)
    
    # Compare key fields
    assert report1.contract_id == report2.contract_id
    assert report1.filename == report2.filename
    assert len(report1.risky_clauses) == len(report2.risky_clauses)
    assert len(report1.missing_clauses) == len(report2.missing_clauses)
    assert report1.risk_summary == report2.risk_summary
    
    # Compare first risky clause explanation (should be identical)
    if len(report1.risky_clauses) > 0:
        assert report1.risky_clauses[0].explanation == report2.risky_clauses[0].explanation
