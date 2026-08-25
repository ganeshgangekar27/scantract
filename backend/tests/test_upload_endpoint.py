"""
Tests for contract upload endpoint.
"""
import io
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.main import app
from app.db.models import Contract
from app.api.routes.contracts import upload_contract, UploadResponse


# Test fixtures

@pytest.fixture
def test_pdf_content():
    """Minimal valid PDF content."""
    # Minimal PDF structure
    return b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
197
%%EOF"""


@pytest.fixture
def test_docx_content():
    """Minimal valid DOCX content (create real docx bytes)."""
    from docx import Document
    doc = Document()
    doc.add_paragraph("Test content")
    
    docx_io = io.BytesIO()
    doc.save(docx_io)
    docx_io.seek(0)
    return docx_io.read()


@pytest.fixture
def test_pdf_file(test_pdf_content):
    """Create test PDF upload file."""
    return UploadFile(
        filename="test_contract.pdf",
        file=io.BytesIO(test_pdf_content)
    )


@pytest.fixture
def test_docx_file(test_docx_content):
    """Create test DOCX upload file."""
    return UploadFile(
        filename="test_contract.docx",
        file=io.BytesIO(test_docx_content)
    )


@pytest.fixture
def oversized_file():
    """Create file larger than 15MB limit."""
    # Create 20MB of data
    large_content = b"x" * (20 * 1024 * 1024)
    return UploadFile(
        filename="large.pdf",
        file=io.BytesIO(large_content)
    )


@pytest.fixture
def invalid_file():
    """Create file with invalid extension."""
    return UploadFile(
        filename="test.txt",
        file=io.BytesIO(b"Some text content")
    )


@pytest.fixture
def mock_db_session():
    """Mock async database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_background_tasks():
    """Mock BackgroundTasks."""
    tasks = MagicMock(spec=BackgroundTasks)
    tasks.add_task = MagicMock()
    return tasks


# Upload validation tests

@pytest.mark.asyncio
async def test_upload_valid_pdf(test_pdf_file, mock_db_session, mock_background_tasks):
    """Test uploading a valid PDF file."""
    # Mock contract creation
    mock_contract = Contract(
        id=1,
        filename="test_contract.pdf",
        file_path="/uploads/test.pdf",
        uploaded_at=datetime.utcnow(),
        processing_status='uploaded'
    )
    
    # Configure mock to return our contract
    async def mock_refresh(obj):
        obj.id = 1
        obj.uploaded_at = datetime.utcnow()
    
    mock_db_session.refresh.side_effect = mock_refresh
    
    # Call upload endpoint
    with patch('app.api.routes.contracts.Path.mkdir'):
        with patch('builtins.open', create=True):
            response = await upload_contract(
                file=test_pdf_file,
                background_tasks=mock_background_tasks,
                db=mock_db_session
            )
    
    # Verify response
    assert isinstance(response, UploadResponse)
    assert response.contract_id == 1
    assert response.filename == "test_contract.pdf"
    assert response.status == 'uploaded'
    assert isinstance(response.size, int)
    assert response.size > 0
    
    # Verify database interaction
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    
    # Verify background task queued
    mock_background_tasks.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_upload_valid_docx(test_docx_file, mock_db_session, mock_background_tasks):
    """Test uploading a valid DOCX file."""
    # Mock contract creation
    async def mock_refresh(obj):
        obj.id = 2
        obj.uploaded_at = datetime.utcnow()
    
    mock_db_session.refresh.side_effect = mock_refresh
    
    # Call upload endpoint
    with patch('app.api.routes.contracts.Path.mkdir'):
        with patch('builtins.open', create=True):
            response = await upload_contract(
                file=test_docx_file,
                background_tasks=mock_background_tasks,
                db=mock_db_session
            )
    
    # Verify response
    assert response.contract_id == 2
    assert response.filename == "test_contract.docx"
    assert response.status == 'uploaded'


@pytest.mark.asyncio
async def test_upload_invalid_file_type(invalid_file, mock_db_session, mock_background_tasks):
    """Test uploading file with invalid extension returns 400."""
    from fastapi import HTTPException
    
    # Should raise HTTPException with 400 status
    with pytest.raises(HTTPException) as exc_info:
        await upload_contract(
            file=invalid_file,
            background_tasks=mock_background_tasks,
            db=mock_db_session
        )
    
    assert exc_info.value.status_code == 400
    assert "Invalid file type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_oversized_file(oversized_file, mock_db_session, mock_background_tasks):
    """Test uploading file exceeding 15MB limit returns 400."""
    from fastapi import HTTPException
    
    # Should raise HTTPException with 400 status
    with pytest.raises(HTTPException) as exc_info:
        await upload_contract(
            file=oversized_file,
            background_tasks=mock_background_tasks,
            db=mock_db_session
        )
    
    assert exc_info.value.status_code == 400
    assert "exceeds maximum" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_creates_contract_row(test_pdf_file, mock_db_session, mock_background_tasks):
    """Test that upload creates Contract row with correct fields."""
    async def mock_refresh(obj):
        obj.id = 3
        obj.uploaded_at = datetime.utcnow()
    
    mock_db_session.refresh.side_effect = mock_refresh
    
    with patch('app.api.routes.contracts.Path.mkdir'):
        with patch('builtins.open', create=True):
            await upload_contract(
                file=test_pdf_file,
                background_tasks=mock_background_tasks,
                db=mock_db_session
            )
    
    # Verify Contract object was created and added
    mock_db_session.add.assert_called_once()
    
    # Get the Contract object that was added
    added_contract = mock_db_session.add.call_args[0][0]
    
    assert isinstance(added_contract, Contract)
    assert added_contract.filename == "test_contract.pdf"
    assert added_contract.processing_status == 'uploaded'
    assert added_contract.file_path is not None


@pytest.mark.asyncio
async def test_upload_queues_background_task(test_pdf_file, mock_db_session, mock_background_tasks):
    """Test that upload queues background processing task."""
    async def mock_refresh(obj):
        obj.id = 4
        obj.uploaded_at = datetime.utcnow()
    
    mock_db_session.refresh.side_effect = mock_refresh
    
    with patch('app.api.routes.contracts.Path.mkdir'):
        with patch('builtins.open', create=True):
            await upload_contract(
                file=test_pdf_file,
                background_tasks=mock_background_tasks,
                db=mock_db_session
            )
    
    # Verify background task was added (not awaited)
    mock_background_tasks.add_task.assert_called_once()
    
    # Verify the task is the process_contract function
    task_call = mock_background_tasks.add_task.call_args
    from app.document_processing.processor import process_contract
    assert task_call[0][0] == process_contract


@pytest.mark.asyncio
async def test_response_format(test_pdf_file, mock_db_session, mock_background_tasks):
    """Test that response matches UploadResponse schema with contract_id as int."""
    async def mock_refresh(obj):
        obj.id = 5
        obj.uploaded_at = datetime.utcnow()
    
    mock_db_session.refresh.side_effect = mock_refresh
    
    with patch('app.api.routes.contracts.Path.mkdir'):
        with patch('builtins.open', create=True):
            response = await upload_contract(
                file=test_pdf_file,
                background_tasks=mock_background_tasks,
                db=mock_db_session
            )
    
    # Verify response type
    assert isinstance(response, UploadResponse)
    
    # Verify contract_id is int (not UUID or string)
    assert isinstance(response.contract_id, int)
    assert response.contract_id == 5
    
    # Verify all required fields present
    assert isinstance(response.filename, str)
    assert isinstance(response.size, int)
    assert isinstance(response.upload_timestamp, datetime)
    assert isinstance(response.status, str)
    assert response.status == 'uploaded'
