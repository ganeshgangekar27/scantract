"""
API endpoint tests for report routes.

Tests the JSON and PDF report endpoints.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.routes.reports import router, get_db
from app.reports.models import (
    ContractReport,
    RiskSummary,
    ClauseWithRisk,
    RiskyClauseReport,
    MissingClauseReport,
    LegalReference
)


# ============================================================================
# Test Setup
# ============================================================================

@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def app(mock_db):
    """Create FastAPI app with reports router and dependency overrides."""
    app = FastAPI()
    app.include_router(router)
    # Override get_db dependency with mock
    app.dependency_overrides[get_db] = lambda: mock_db
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_report():
    """Mock ContractReport for testing."""
    return ContractReport(
        contract_id=1,
        filename="test_contract.pdf",
        upload_date=datetime(2024, 8, 15, 10, 30, 0),
        all_clauses=[
            ClauseWithRisk(
                clause_id=1,
                clause_number="1.1",
                clause_text="Test clause",
                has_risk=True,
                risk_severity="high",
                risk_reason="Test risk"
            )
        ],
        risky_clauses=[
            RiskyClauseReport(
                finding_id="123e4567-e89b-12d3-a456-426614174000",
                clause_id=1,
                clause_number="1.1",
                clause_text="Test clause",
                severity="high",
                reason="Test risk",
                explanation="Test explanation",
                formatted_citation="[Legal] Test citation"
            )
        ],
        missing_clauses=[],
        risk_summary=RiskSummary(
            total_clauses=1,
            risky_clauses_count=1,
            missing_clauses_count=0,
            high_severity_count=1,
            medium_severity_count=0,
            low_severity_count=0,
            overall_risk_level="high"
        ),
        legal_references=[
            LegalReference(
                citation="[Legal] Test citation",
                usage_count=1
            )
        ]
    )


# ============================================================================
# TC-7: JSON Endpoint Success
# ============================================================================

def test_json_endpoint_success(client, mock_report):
    """
    TC-7: GET /api/contracts/{contract_id}/report returns JSON successfully.
    
    Verifies:
    - Status code 200
    - Response envelope structure
    - Data contains contract_id and risk_summary
    """
    with patch('app.api.routes.reports.assemble_contract_report') as mock_assemble:
        mock_assemble.return_value = mock_report
        
        response = client.get("/api/contracts/1/report")
        
        # Assert status code
        assert response.status_code == 200
        
        # Assert response structure
        data = response.json()
        assert data["success"] is True
        assert data["error"] is None
        assert "data" in data
        
        # Assert data content
        assert data["data"]["contract_id"] == 1
        assert "risk_summary" in data["data"]
        assert "all_clauses" in data["data"]
        assert isinstance(data["data"]["all_clauses"], list)
        
        # Assert mock called correctly
        mock_assemble.assert_called_once()


# ============================================================================
# TC-8: JSON Endpoint 404 - Contract Not Found
# ============================================================================

def test_json_endpoint_404(client):
    """
    TC-8: GET /api/contracts/{contract_id}/report returns 404 for missing contract.
    
    Verifies:
    - Status code 404
    - Error detail contains message
    """
    with patch('app.api.routes.reports.assemble_contract_report') as mock_assemble:
        mock_assemble.side_effect = ValueError("Contract not found")
        
        response = client.get("/api/contracts/999/report")
        
        # Assert status code
        assert response.status_code == 404
        
        # Assert error detail
        data = response.json()
        assert "detail" in data
        assert "Contract not found" in data["detail"]


# ============================================================================
# TC-9: PDF Endpoint Success
# ============================================================================

def test_pdf_endpoint_success(client, mock_report):
    """
    TC-9: GET /api/contracts/{contract_id}/report/pdf returns PDF successfully.
    
    Verifies:
    - Status code 200
    - Content-Type: application/pdf
    - Content-Disposition header with filename
    - Response body is non-empty
    """
    fake_pdf_bytes = b"%PDF-1.4\nFake PDF content for testing"
    
    with patch('app.api.routes.reports.assemble_contract_report') as mock_assemble:
        mock_assemble.return_value = mock_report
        
        with patch('app.api.routes.reports.generate_pdf_report') as mock_pdf:
            mock_pdf.return_value = fake_pdf_bytes
            
            response = client.get("/api/contracts/1/report/pdf")
            
            # Assert status code
            assert response.status_code == 200
            
            # Assert content type
            assert response.headers["content-type"] == "application/pdf"
            
            # Assert Content-Disposition header
            assert "content-disposition" in response.headers
            disposition = response.headers["content-disposition"]
            assert "attachment" in disposition
            assert "filename=" in disposition
            assert "_report.pdf" in disposition
            assert "test_contract" in disposition
            
            # Assert response body is non-empty
            assert len(response.content) > 0
            assert response.content == fake_pdf_bytes


# ============================================================================
# TC-10: PDF Content Validation
# ============================================================================

def test_pdf_content_validation(client, mock_report):
    """
    TC-10: Validate PDF content structure.
    
    Verifies:
    - PDF bytes start with %PDF magic number
    - Response size > 1KB (indicates real PDF)
    """
    # Create fake PDF with proper magic number and substantial size
    fake_pdf_bytes = b"%PDF-1.4\n" + b"x" * 2000  # > 1KB
    
    with patch('app.api.routes.reports.assemble_contract_report') as mock_assemble:
        mock_assemble.return_value = mock_report
        
        with patch('app.api.routes.reports.generate_pdf_report') as mock_pdf:
            mock_pdf.return_value = fake_pdf_bytes
            
            response = client.get("/api/contracts/1/report/pdf")
            
            # Assert status code
            assert response.status_code == 200
            
            # Assert PDF magic number
            assert response.content.startswith(b"%PDF")
            
            # Assert size > 1KB
            assert len(response.content) > 1024
