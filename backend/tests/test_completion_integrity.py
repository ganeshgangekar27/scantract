"""
Test completion integrity - contracts fail if any explanation is missing/invalid.
"""
import pytest
import pytest_asyncio
from pathlib import Path
import sys
import uuid
import random
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.document_processing.orchestrator import run_full_pipeline
from app.db.models import Contract, RiskFinding
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


async def create_test_contract_with_findings(
    db_session: AsyncSession,
    explanations: list,
    generate_uuid4=uuid.uuid4
):
    """
    Create a contract and findings for testing.
    Uses missing_clause type to avoid needing clause rows.
    Returns (contract_id, finding_ids) for cleanup.
    """
    # Generate random contract ID >= 900000
    contract_id = random.randint(900000, 999999)
    
    contract = Contract(
        id=contract_id,
        contract_type='rental',
        filename=f'test_{generate_uuid4()}.pdf',
        uploaded_at=datetime.now(timezone.utc),
        file_path='/tmp/test.pdf',
        full_text='Test contract text',
        processing_status='processing',
        pipeline_stage='segmented'
    )
    db_session.add(contract)
    
    finding_ids = []
    for explanation in explanations:
        finding_id = str(uuid.uuid4())
        finding = RiskFinding(
            id=finding_id,
            contract_id=contract_id,
            finding_type='missing_clause',
            expected_clause_type='test_clause_type',
            reason='Test reason',
            triggering_rule_or_corpus='test_rule',
            severity='high',
            explanation=explanation
        )
        db_session.add(finding)
        finding_ids.append(finding_id)
    
    await db_session.commit()
    return contract_id, finding_ids


@pytest.mark.asyncio
async def test_all_valid_explanations_completes(db_session: AsyncSession):
    """All findings have valid explanations -> pipeline_stage 'completed', failed_stage None."""
    contract_id = None
    try:
        contract_id, finding_ids = await create_test_contract_with_findings(
            db_session,
            [
                'Valid explanation with enough characters to pass validation checks',
                'Another valid explanation with sufficient length for testing purposes'
            ]
        )
        
        # Patch the earlier stages to skip LLM calls
        with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
            with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
                with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                    mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                    
                    mock_result = MagicMock()
                    mock_result.total_risks = 0
                    mock_result.total_missing = 0
                    mock_result.high_severity_count = 0
                    mock_detect.return_value = mock_result
                    
                    mock_gen.return_value = 0
                    
                    await run_full_pipeline(contract_id=contract_id, db=db_session)
        
        # Reload contract in fresh query
        result = await db_session.execute(select(Contract).where(Contract.id == contract_id))
        reloaded = result.scalar_one()
        
        assert reloaded.pipeline_stage == 'completed'
        assert reloaded.failed_stage is None
        
    finally:
        if contract_id:
            # Cleanup in correct order
            await db_session.execute(select(RiskFinding).where(RiskFinding.contract_id == contract_id))
            findings = (await db_session.execute(select(RiskFinding).where(RiskFinding.contract_id == contract_id))).scalars().all()
            for f in findings:
                await db_session.delete(f)
            
            contract = await db_session.get(Contract, contract_id)
            if contract:
                await db_session.delete(contract)
            await db_session.commit()


@pytest.mark.asyncio
async def test_one_null_explanation_fails(db_session: AsyncSession):
    """One finding with NULL -> 'failed', failed_stage 'generating_explanations', message contains '1 finding'."""
    contract_id = None
    try:
        contract_id, finding_ids = await create_test_contract_with_findings(
            db_session,
            [
                None,  # NULL
                'Valid explanation with enough characters'
            ]
        )
        
        with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
            with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
                with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                    mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                    
                    mock_result = MagicMock()
                    mock_result.total_risks = 0
                    mock_result.total_missing = 0
                    mock_result.high_severity_count = 0
                    mock_detect.return_value = mock_result
                    
                    mock_gen.return_value = 0
                    
                    with pytest.raises(RuntimeError, match="Explanations missing or invalid"):
                        await run_full_pipeline(contract_id=contract_id, db=db_session)
        
        # Reload contract
        result = await db_session.execute(select(Contract).where(Contract.id == contract_id))
        reloaded = result.scalar_one()
        
        assert reloaded.pipeline_stage == 'failed'
        assert reloaded.failed_stage == 'generating_explanations'
        assert '1' in reloaded.error_message
        assert 'finding' in reloaded.error_message.lower()
        
    finally:
        if contract_id:
            findings = (await db_session.execute(select(RiskFinding).where(RiskFinding.contract_id == contract_id))).scalars().all()
            for f in findings:
                await db_session.delete(f)
            
            contract = await db_session.get(Contract, contract_id)
            if contract:
                await db_session.delete(contract)
            await db_session.commit()


@pytest.mark.asyncio
async def test_invalid_stored_explanation_fails(db_session: AsyncSession):
    """One finding with stored '{"": ""}' (invalid) -> 'failed'."""
    contract_id = None
    try:
        contract_id, finding_ids = await create_test_contract_with_findings(
            db_session,
            [
                '{"": ""}',  # Invalid
                'Valid explanation with enough characters'
            ]
        )
        
        with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
            with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
                with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                    mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                    
                    mock_result = MagicMock()
                    mock_result.total_risks = 0
                    mock_result.total_missing = 0
                    mock_result.high_severity_count = 0
                    mock_detect.return_value = mock_result
                    
                    mock_gen.return_value = 0
                    
                    with pytest.raises(RuntimeError, match="Explanations missing or invalid"):
                        await run_full_pipeline(contract_id=contract_id, db=db_session)
        
        # Reload contract
        result = await db_session.execute(select(Contract).where(Contract.id == contract_id))
        reloaded = result.scalar_one()
        
        assert reloaded.pipeline_stage == 'failed'
        assert reloaded.failed_stage == 'generating_explanations'
        
    finally:
        if contract_id:
            findings = (await db_session.execute(select(RiskFinding).where(RiskFinding.contract_id == contract_id))).scalars().all()
            for f in findings:
                await db_session.delete(f)
            
            contract = await db_session.get(Contract, contract_id)
            if contract:
                await db_session.delete(contract)
            await db_session.commit()


@pytest.mark.asyncio
async def test_wrapped_but_valid_explanation_completes(db_session: AsyncSession):
    """One stored '{"": "A long enough..."}' (wrapped but valid) -> 'completed'."""
    contract_id = None
    try:
        contract_id, finding_ids = await create_test_contract_with_findings(
            db_session,
            [
                '{"": "A long enough explanation text that passes validation after unwrapping."}'
            ]
        )
        
        with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
            with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
                with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                    mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                    
                    mock_result = MagicMock()
                    mock_result.total_risks = 0
                    mock_result.total_missing = 0
                    mock_result.high_severity_count = 0
                    mock_detect.return_value = mock_result
                    
                    mock_gen.return_value = 0
                    
                    await run_full_pipeline(contract_id=contract_id, db=db_session)
        
        # Reload contract
        result = await db_session.execute(select(Contract).where(Contract.id == contract_id))
        reloaded = result.scalar_one()
        
        assert reloaded.pipeline_stage == 'completed'
        assert reloaded.failed_stage is None
        
    finally:
        if contract_id:
            findings = (await db_session.execute(select(RiskFinding).where(RiskFinding.contract_id == contract_id))).scalars().all()
            for f in findings:
                await db_session.delete(f)
            
            contract = await db_session.get(Contract, contract_id)
            if contract:
                await db_session.delete(contract)
            await db_session.commit()


@pytest.mark.asyncio
async def test_zero_findings_completes(db_session: AsyncSession):
    """Zero findings -> 'completed'."""
    contract_id = None
    try:
        contract_id, finding_ids = await create_test_contract_with_findings(
            db_session,
            []  # No findings
        )
        
        with patch('app.document_processing.orchestrator.classify_all_clauses', new_callable=AsyncMock) as mock_classify:
            with patch('app.document_processing.orchestrator.detect_risks', new_callable=AsyncMock) as mock_detect:
                with patch('app.document_processing.orchestrator.generate_all_explanations', new_callable=AsyncMock) as mock_gen:
                    mock_classify.return_value = {'successful': 1, 'total': 1, 'total_tokens': 0}
                    
                    mock_result = MagicMock()
                    mock_result.total_risks = 0
                    mock_result.total_missing = 0
                    mock_result.high_severity_count = 0
                    mock_detect.return_value = mock_result
                    
                    mock_gen.return_value = 0
                    
                    await run_full_pipeline(contract_id=contract_id, db=db_session)
        
        # Reload contract
        result = await db_session.execute(select(Contract).where(Contract.id == contract_id))
        reloaded = result.scalar_one()
        
        assert reloaded.pipeline_stage == 'completed'
        assert reloaded.failed_stage is None
        
    finally:
        if contract_id:
            contract = await db_session.get(Contract, contract_id)
            if contract:
                await db_session.delete(contract)
            await db_session.commit()
