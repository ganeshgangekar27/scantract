"""
Test completion integrity - contracts fail if any explanation is missing/invalid.
"""
import pytest
import pytest_asyncio
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.document_processing.orchestrator import run_full_pipeline
from app.db.models import Contract, RiskFinding, Clause
from tests.db_config import get_test_database_url

TEST_DATABASE_URL = get_test_database_url()


@pytest_asyncio.fixture
async def db_session():
    """Create async database session for tests."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_all_valid_explanations_completes(db_session: AsyncSession):
    """All findings have valid explanations -> pipeline_stage 'completed', failed_stage None."""
    # Create contract with test ID that won't clash
    contract = Contract(
        id=90001,
        contract_type='rental',
        filename='test_complete.pdf',
        uploaded_at=datetime.now(timezone.utc),
        file_path='/tmp/test.pdf',
        full_text='Test contract text',
        processing_status='processing',
        pipeline_stage='segmented'
    )
    db_session.add(contract)
    
    # Create clauses first (required for risky_clause findings)
    clause1 = Clause(
        id=900001,
        contract_id=90001,
        clause_id='C1',
        position=1,
        text='Test clause 1'
    )
    clause2 = Clause(
        id=900002,
        contract_id=90001,
        clause_id='C2',
        position=2,
        text='Test clause 2'
    )
    db_session.add_all([clause1, clause2])
    
    # Create findings with valid explanations
    finding1 = RiskFinding(
        id=str(uuid.uuid4()),
        contract_id=90001,
        finding_type='risky_clause',
        clause_id=900001,
        reason='Test reason',
        triggering_rule_or_corpus='test_rule',
        severity='high',
        explanation='Valid explanation with enough characters to pass validation checks'
    )
    finding2 = RiskFinding(
        id=str(uuid.uuid4()),
        contract_id=90001,
        finding_type='risky_clause',
        clause_id=900002,
        reason='Test reason',
        triggering_rule_or_corpus='test_rule',
        severity='medium',
        explanation='Another valid explanation with sufficient length for testing purposes'
    )
    db_session.add_all([finding1, finding2])
    await db_session.commit()
    
    # Patch the earlier stages to skip LLM calls
    with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
        with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
            with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                
                # Mock detect_risks to return object with required attributes
                mock_result = MagicMock()
                mock_result.total_risks = 0
                mock_result.total_missing = 0
                mock_result.high_severity_count = 0
                mock_detect.return_value = mock_result
                
                mock_gen.return_value = 0  # No new explanations needed
                
                await run_full_pipeline(contract_id=90001, db=db_session)
    
    # Reload contract in fresh query
    result = await db_session.execute(select(Contract).where(Contract.id == 90001))
    reloaded = result.scalar_one()
    
    assert reloaded.pipeline_stage == 'completed'
    assert reloaded.failed_stage is None
    
    # Cleanup
    await db_session.delete(clause1)
    await db_session.delete(clause2)
    await db_session.delete(finding1)
    await db_session.delete(finding2)
    await db_session.delete(contract)
    await db_session.commit()


@pytest.mark.asyncio
async def test_one_null_explanation_fails(db_session: AsyncSession):
    """One finding with NULL -> 'failed', failed_stage 'generating_explanations', message contains '1 finding'."""
    contract = Contract(
        id=90002,
        contract_type='rental',
        filename='test_null.pdf',
        uploaded_at=datetime.now(timezone.utc),
        file_path='/tmp/test.pdf',
        full_text='Test contract text',
        processing_status='processing',
        pipeline_stage='segmented'
    )
    db_session.add(contract)
    
    # Create clauses first (required for risky_clause findings)
    clause1 = Clause(
        id=900011,
        contract_id=90002,
        clause_id='C1',
        position=1,
        text='Test clause 1'
    )
    clause2 = Clause(
        id=900012,
        contract_id=90002,
        clause_id='C2',
        position=2,
        text='Test clause 2'
    )
    db_session.add_all([clause1, clause2])
    
    finding1 = RiskFinding(
        id=str(uuid.uuid4()),
        contract_id=90002,
        finding_type='risky_clause',
        clause_id=900011,
        reason='Test reason',
        triggering_rule_or_corpus='test_rule',
        severity='high',
        explanation=None
    )  # NULL
    finding2 = RiskFinding(
        id=str(uuid.uuid4()),
        contract_id=90002,
        finding_type='risky_clause',
        clause_id=900012,
        reason='Test reason',
        triggering_rule_or_corpus='test_rule',
        severity='medium',
        explanation='Valid explanation with enough characters'
    )
    db_session.add_all([finding1, finding2])
    await db_session.commit()
    
    with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
        with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
            with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                
                # Mock detect_risks to return object with required attributes
                mock_result = MagicMock()
                mock_result.total_risks = 0
                mock_result.total_missing = 0
                mock_result.high_severity_count = 0
                mock_detect.return_value = mock_result
                
                mock_gen.return_value = 0
                
                with pytest.raises(RuntimeError, match="Explanations missing or invalid"):
                    await run_full_pipeline(contract_id=90002, db=db_session)
    
    # Reload contract
    result = await db_session.execute(select(Contract).where(Contract.id == 90002))
    reloaded = result.scalar_one()
    
    assert reloaded.pipeline_stage == 'failed'
    assert reloaded.failed_stage == 'generating_explanations'
    assert '1' in reloaded.error_message
    assert 'finding' in reloaded.error_message.lower()
    
    # Cleanup
    await db_session.delete(clause1)
    await db_session.delete(clause2)
    await db_session.delete(finding1)
    await db_session.delete(finding2)
    await db_session.delete(contract)
    await db_session.commit()


@pytest.mark.asyncio
async def test_invalid_stored_explanation_fails(db_session: AsyncSession):
    """One finding with stored '{"": ""}' (invalid) -> 'failed'."""
    contract = Contract(
        id=90003,
        contract_type='rental',
        filename='test_invalid.pdf',
        uploaded_at=datetime.now(timezone.utc),
        file_path='/tmp/test.pdf',
        full_text='Test contract text',
        processing_status='processing',
        pipeline_stage='segmented'
    )
    db_session.add(contract)
    
    # Create clauses first (required for risky_clause findings)
    clause1 = Clause(
        id=900021,
        contract_id=90003,
        clause_id='C1',
        position=1,
        text='Test clause 1'
    )
    clause2 = Clause(
        id=900022,
        contract_id=90003,
        clause_id='C2',
        position=2,
        text='Test clause 2'
    )
    db_session.add_all([clause1, clause2])
    
    finding1 = RiskFinding(
        id=str(uuid.uuid4()),
        contract_id=90003,
        finding_type='risky_clause',
        clause_id=900021,
        reason='Test reason',
        triggering_rule_or_corpus='test_rule',
        severity='high',
        explanation='{"": ""}'
    )  # Invalid
    finding2 = RiskFinding(
        id=str(uuid.uuid4()),
        contract_id=90003,
        finding_type='risky_clause',
        clause_id=900022,
        reason='Test reason',
        triggering_rule_or_corpus='test_rule',
        severity='medium',
        explanation='Valid explanation with enough characters'
    )
    db_session.add_all([finding1, finding2])
    await db_session.commit()
    
    with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
        with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
            with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                
                # Mock detect_risks to return object with required attributes
                mock_result = MagicMock()
                mock_result.total_risks = 0
                mock_result.total_missing = 0
                mock_result.high_severity_count = 0
                mock_detect.return_value = mock_result
                
                mock_gen.return_value = 0
                
                with pytest.raises(RuntimeError, match="Explanations missing or invalid"):
                    await run_full_pipeline(contract_id=90003, db=db_session)
    
    # Reload contract
    result = await db_session.execute(select(Contract).where(Contract.id == 90003))
    reloaded = result.scalar_one()
    
    assert reloaded.pipeline_stage == 'failed'
    assert reloaded.failed_stage == 'generating_explanations'
    
    # Cleanup
    await db_session.delete(clause1)
    await db_session.delete(clause2)
    await db_session.delete(finding1)
    await db_session.delete(finding2)
    await db_session.delete(contract)
    await db_session.commit()


@pytest.mark.asyncio
async def test_wrapped_but_valid_explanation_completes(db_session: AsyncSession):
    """One stored '{"": "A long enough..."}' (wrapped but valid) -> 'completed'."""
    contract = Contract(
        id=90004,
        contract_type='rental',
        filename='test_wrapped.pdf',
        uploaded_at=datetime.now(timezone.utc),
        file_path='/tmp/test.pdf',
        full_text='Test contract text',
        processing_status='processing',
        pipeline_stage='segmented'
    )
    db_session.add(contract)
    
    # Create clause first (required for risky_clause finding)
    clause1 = Clause(
        id=900031,
        contract_id=90004,
        clause_id='C1',
        position=1,
        text='Test clause 1'
    )
    db_session.add(clause1)
    
    finding1 = RiskFinding(
        id=str(uuid.uuid4()),
        contract_id=90004,
        finding_type='risky_clause',
        clause_id=900031,
        reason='Test reason',
        triggering_rule_or_corpus='test_rule',
        severity='high',
        explanation='{"": "A long enough explanation text that passes validation after unwrapping."}'
    )
    db_session.add(finding1)
    await db_session.commit()
    
    with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
        with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
            with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                
                # Mock detect_risks to return object with required attributes
                mock_result = MagicMock()
                mock_result.total_risks = 0
                mock_result.total_missing = 0
                mock_result.high_severity_count = 0
                mock_detect.return_value = mock_result
                
                mock_gen.return_value = 0
                
                await run_full_pipeline(contract_id=90004, db=db_session)
    
    # Reload contract
    result = await db_session.execute(select(Contract).where(Contract.id == 90004))
    reloaded = result.scalar_one()
    
    assert reloaded.pipeline_stage == 'completed'
    assert reloaded.failed_stage is None
    
    # Cleanup
    await db_session.delete(clause1)
    await db_session.delete(finding1)
    await db_session.delete(contract)
    await db_session.commit()


@pytest.mark.asyncio
async def test_zero_findings_completes(db_session: AsyncSession):
    """Zero findings -> 'completed'."""
    contract = Contract(
        id=90005,
        contract_type='rental',
        filename='test_zero.pdf',
        uploaded_at=datetime.now(timezone.utc),
        file_path='/tmp/test.pdf',
        full_text='Test contract text',
        processing_status='processing',
        pipeline_stage='segmented'
    )
    db_session.add(contract)
    await db_session.commit()
    
    # No findings added
    
    with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
        with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
            with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                
                # Mock detect_risks to return object with required attributes
                mock_result = MagicMock()
                mock_result.total_risks = 0
                mock_result.total_missing = 0
                mock_result.high_severity_count = 0
                mock_detect.return_value = mock_result
                
                mock_gen.return_value = 0
                
                await run_full_pipeline(contract_id=90005, db=db_session)
    
    # Reload contract
    result = await db_session.execute(select(Contract).where(Contract.id == 90005))
    reloaded = result.scalar_one()
    
    assert reloaded.pipeline_stage == 'completed'
    assert reloaded.failed_stage is None
    
    # Cleanup
    await db_session.delete(contract)
    await db_session.commit()
