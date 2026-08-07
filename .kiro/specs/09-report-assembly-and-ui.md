# Spec: Final Report Assembly & Results UI

## Overview
Build the final report assembly and results UI for ScanTract — Stage 9 of the core pipeline that combines all analysis outputs into a structured JSON report for the frontend, generates downloadable PDF reports, and renders an interactive UI showing highlighted risky clauses, missing clauses, explanations, and legal citations.

## Scope

### Backend
- JSON report endpoint combining all pipeline outputs
- PDF report generation with HTML-to-PDF rendering
- Structured response envelope with all contract data

### Frontend
- Interactive report view with highlighted clauses
- Clickable clause highlights showing explanations in side panel
- Missing clause warnings panel
- Risk summary header with severity counts
- PDF download button
- Loading and error states

### Testing
- Backend API tests for both endpoints
- Frontend component tests (React Testing Library)
- E2E tests (Playwright) for user interactions

## Requirements

### Backend Functional Requirements

**FR-1: JSON Report Endpoint**
- Endpoint: `GET /api/contracts/{contract_id}/report`
- Returns complete analysis in structured envelope
- Response includes:
  - Contract metadata (filename, upload timestamp)
  - Full clause list with risk flags
  - Risk summary (counts by severity)
  - Risky clause findings with explanations
  - Missing clause findings with explanations
  - Legal references (deduplicated)
- Single atomic response (no need for multiple API calls)


**FR-2: PDF Report Endpoint**
- Endpoint: `GET /api/contracts/{contract_id}/report/pdf`
- Returns downloadable PDF file
- Content-Type: `application/pdf`
- Content-Disposition: `attachment; filename="contract-report-{id}.pdf"`
- PDF contains:
  - Cover page with contract summary
  - Risk summary section
  - Highlighted clauses with explanations
  - Missing clauses section
  - Legal references appendix
- Use weasyprint (HTML→PDF) or similar lightweight library
- Maintain consistent styling with web UI

**FR-3: Report Data Assembly**
- Function: `assemble_contract_report(contract_id) -> ContractReport`
- Fetch all data from database:
  - Contract metadata
  - Classified clauses
  - Risk findings with explanations
  - Legal references from Stage 6
- Compute summary statistics
- Flag risky clauses with severity
- Deduplicate legal references
- Return structured model

**FR-4: Error Handling**
- Handle contract not found (404)
- Handle incomplete processing (report unavailable)
- Handle missing explanations (graceful degradation)
- Return clear error messages in envelope

### Frontend Functional Requirements

**FR-5: Report View Component**
- Component: `frontend/src/pages/ReportView.tsx`
- Route: `/report/:contractId`
- Fetch report data from JSON endpoint
- Display loading state during fetch
- Handle errors gracefully
- Responsive layout (desktop + mobile)

**FR-6: Contract Text Display**
- Render full contract text with original formatting preserved
- Highlight risky clauses by severity:
  - High: Red background (#FEE2E2)
  - Medium: Yellow background (#FEF3C7)
  - Low: Blue background (#DBEAFE)
- Clause highlights are clickable
- Show clause numbers/identifiers
- Maintain readability with proper spacing

**FR-7: Side Panel for Explanations**
- Opens when user clicks highlighted clause
- Display:
  - Clause text
  - Risk severity badge
  - Plain-language explanation
  - Formatted legal citation
  - Link to close panel
- Smooth slide-in animation
- Closes when clicking outside or X button


**FR-8: Missing Clauses Panel**
- Separate section below contract text
- Card-based layout for each missing clause
- Display:
  - Expected clause type
  - Explanation of why expected
  - Severity indicator
  - Legal citation
- Expandable/collapsible cards

**FR-9: Risk Summary Header**
- Sticky header at top of page
- Display counts:
  - Total risky clauses
  - High severity count (red)
  - Medium severity count (yellow)
  - Low severity count (blue)
  - Missing clauses count
- Visual indicators (icons + colors)
- Download PDF button in header

**FR-10: PDF Download**
- Button triggers download from PDF endpoint
- Show loading spinner during generation
- Handle download errors
- Success notification after download

**FR-11: Loading States**
- Skeleton loaders during initial fetch
- Spinner for PDF download
- Progressive loading (show data as it loads)

**FR-12: Error States**
- Display user-friendly error messages
- Offer retry button
- Show contact support option for persistent errors
- Handle specific errors:
  - Contract not found
  - Processing incomplete
  - Network errors

### Non-Functional Requirements

**NFR-1: Performance**
- JSON report endpoint: <500ms
- PDF generation: <5 seconds
- Frontend initial render: <2 seconds
- Clause highlight interaction: <100ms

**NFR-2: Usability**
- Intuitive navigation (no training required)
- Clear visual hierarchy
- Accessible (WCAG 2.1 AA compliant)
- Mobile-responsive

**NFR-3: Data Integrity**
- Report reflects exact database state
- No stale data shown
- Explanations match findings
- Citations traceable to sources

**NFR-4: Reliability**
- Graceful degradation if subsystems unavailable
- Retry logic for transient failures
- Clear error messages


## Technical Design

### Backend Architecture

**Module Structure:**
```
backend/app/api/routes/
├── __init__.py
├── contracts.py           # Upload endpoint (from Stage 2)
├── explanations.py        # Explanation endpoint (from Stage 8)
└── reports.py             # Report endpoints (NEW)

backend/app/reports/
├── __init__.py
├── assembler.py           # Report data assembly
├── models.py              # Report Pydantic models
└── pdf_generator.py       # PDF generation
```

### Backend Data Models

**File: backend/app/reports/models.py**

```python
from pydantic import BaseModel, Field
from typing import Literal

class ClauseWithRisk(BaseModel):
    """Contract clause with risk annotation."""
    clause_id: str
    clause_number: str
    clause_text: str
    clause_type: str | None
    is_risky: bool
    risk_severity: Literal["low", "medium", "high"] | None = None
    position: int

class RiskyClauseReport(BaseModel):
    """Risky clause in report."""
    clause_id: str
    clause_number: str
    clause_text: str
    reason: str
    explanation: str
    formatted_citation: str
    severity: str

class MissingClauseReport(BaseModel):
    """Missing clause in report."""
    expected_clause_type: str
    why_expected: str
    explanation: str
    formatted_citation: str
    severity: str

class RiskSummary(BaseModel):
    """Aggregated risk statistics."""
    total_clauses: int
    total_risky_clauses: int
    total_missing_clauses: int
    high_severity_count: int
    medium_severity_count: int
    low_severity_count: int

class LegalReference(BaseModel):
    """Deduplicated legal reference."""
    citation: str
    source_type: Literal["legal_rule", "reference_corpus"]
    usage_count: int  # How many findings reference this

class ContractReport(BaseModel):
    """Complete contract analysis report."""
    contract_id: str
    filename: str
    upload_timestamp: str
    processing_status: str
    clauses: list[ClauseWithRisk]
    risky_clauses: list[RiskyClauseReport]
    missing_clauses: list[MissingClauseReport]
    risk_summary: RiskSummary
    legal_references: list[LegalReference]
```


### Report Assembly Logic

**File: backend/app/reports/assembler.py**

```python
"""
Report data assembly for ScanTract Stage 9.

Combines all pipeline outputs into structured report.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from collections import Counter
import logging

from ..db.models import Contract, Clause, RiskFinding
from .models import (
    ContractReport, ClauseWithRisk, RiskyClauseReport,
    MissingClauseReport, RiskSummary, LegalReference
)

logger = logging.getLogger(__name__)

async def assemble_contract_report(
    contract_id: str,
    db: AsyncSession
) -> ContractReport:
    """
    Assemble complete contract report from database.
    
    Args:
        contract_id: Contract UUID
        db: Database session
    
    Returns:
        ContractReport with all analysis data
    
    Raises:
        ValueError: If contract not found or not ready
    """
    # Fetch contract
    contract = await _fetch_contract(contract_id, db)
    
    if contract.processing_status != "complete":
        raise ValueError(
            f"Report not available - contract processing status: {contract.processing_status}"
        )
    
    # Fetch clauses
    clauses = await _fetch_clauses(contract_id, db)
    
    # Fetch findings
    findings = await _fetch_findings(contract_id, db)
    
    # Build risk map (clause_id -> severity)
    risk_map = {
        str(f.clause_id): f.severity
        for f in findings
        if f.finding_type == "risky_clause" and f.clause_id
    }
    
    # Annotate clauses with risk flags
    clauses_with_risk = [
        ClauseWithRisk(
            clause_id=str(c.id),
            clause_number=c.clause_number,
            clause_text=c.clause_text,
            clause_type=c.clause_type,
            is_risky=str(c.id) in risk_map,
            risk_severity=risk_map.get(str(c.id)),
            position=c.position
        )
        for c in clauses
    ]
    
    # Build risky clause reports
    risky_clauses = []
    for finding in findings:
        if finding.finding_type == "risky_clause":
            clause = next((c for c in clauses if c.id == finding.clause_id), None)
            if clause:
                risky_clauses.append(RiskyClauseReport(
                    clause_id=str(finding.clause_id),
                    clause_number=clause.clause_number,
                    clause_text=clause.clause_text,
                    reason=finding.reason,
                    explanation=finding.explanation or "Explanation pending...",
                    formatted_citation=finding.formatted_citation or "",
                    severity=finding.severity
                ))
    
    # Build missing clause reports
    missing_clauses = [
        MissingClauseReport(
            expected_clause_type=f.expected_clause_type,
            why_expected=f.reason,
            explanation=f.explanation or "Explanation pending...",
            formatted_citation=f.formatted_citation or "",
            severity=f.severity
        )
        for f in findings
        if f.finding_type == "missing_clause"
    ]
    
    # Compute risk summary
    risk_summary = RiskSummary(
        total_clauses=len(clauses),
        total_risky_clauses=len(risky_clauses),
        total_missing_clauses=len(missing_clauses),
        high_severity_count=sum(1 for f in findings if f.severity == "high"),
        medium_severity_count=sum(1 for f in findings if f.severity == "medium"),
        low_severity_count=sum(1 for f in findings if f.severity == "low")
    )
    
    # Deduplicate and count legal references
    legal_references = _build_legal_references(findings)
    
    return ContractReport(
        contract_id=contract_id,
        filename=contract.filename,
        upload_timestamp=contract.upload_timestamp.isoformat(),
        processing_status=contract.processing_status,
        clauses=clauses_with_risk,
        risky_clauses=risky_clauses,
        missing_clauses=missing_clauses,
        risk_summary=risk_summary,
        legal_references=legal_references
    )

async def _fetch_contract(contract_id: str, db: AsyncSession) -> Contract:
    """Fetch contract from database."""
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")
    
    return contract

async def _fetch_clauses(contract_id: str, db: AsyncSession) -> list[Clause]:
    """Fetch all clauses for contract."""
    result = await db.execute(
        select(Clause)
        .where(Clause.contract_id == contract_id)
        .order_by(Clause.position)
    )
    return result.scalars().all()

async def _fetch_findings(contract_id: str, db: AsyncSession) -> list[RiskFinding]:
    """Fetch all risk findings for contract."""
    result = await db.execute(
        select(RiskFinding)
        .where(RiskFinding.contract_id == contract_id)
        .order_by(RiskFinding.severity.desc(), RiskFinding.created_at)
    )
    return result.scalars().all()

def _build_legal_references(findings: list[RiskFinding]) -> list[LegalReference]:
    """
    Deduplicate and count legal references across all findings.
    """
    # Count citations
    citation_counter = Counter()
    citation_types = {}
    
    for finding in findings:
        citation = finding.formatted_citation or finding.triggering_rule_or_corpus
        if citation:
            citation_counter[citation] += 1
            
            # Determine type
            if not citation in citation_types:
                if citation.startswith("[Legal]"):
                    citation_types[citation] = "legal_rule"
                else:
                    citation_types[citation] = "reference_corpus"
    
    # Build deduplicated list
    references = [
        LegalReference(
            citation=citation,
            source_type=citation_types[citation],
            usage_count=count
        )
        for citation, count in citation_counter.most_common()
    ]
    
    return references
```


### PDF Generation

**File: backend/app/reports/pdf_generator.py**

```python
"""
PDF report generation using weasyprint.
"""

from weasyprint import HTML, CSS
from io import BytesIO
import logging

from .models import ContractReport

logger = logging.getLogger(__name__)

def generate_pdf_report(report: ContractReport) -> bytes:
    """
    Generate PDF report from contract report data.
    
    Args:
        report: ContractReport model
    
    Returns:
        PDF bytes
    """
    # Build HTML content
    html_content = _build_html_report(report)
    
    # Generate PDF
    pdf_bytes = BytesIO()
    HTML(string=html_content).write_pdf(
        pdf_bytes,
        stylesheets=[CSS(string=_get_pdf_styles())]
    )
    
    return pdf_bytes.getvalue()

def _build_html_report(report: ContractReport) -> str:
    """Build HTML content for PDF report."""
    
    # Cover page
    cover = f"""
    <div class="cover-page">
        <h1>Contract Analysis Report</h1>
        <p class="filename">{report.filename}</p>
        <p class="date">Generated: {report.upload_timestamp}</p>
    </div>
    """
    
    # Risk summary
    summary = f"""
    <div class="summary-page">
        <h2>Risk Summary</h2>
        <div class="summary-grid">
            <div class="stat">
                <span class="label">Total Clauses</span>
                <span class="value">{report.risk_summary.total_clauses}</span>
            </div>
            <div class="stat">
                <span class="label">Risky Clauses</span>
                <span class="value">{report.risk_summary.total_risky_clauses}</span>
            </div>
            <div class="stat high">
                <span class="label">High Severity</span>
                <span class="value">{report.risk_summary.high_severity_count}</span>
            </div>
            <div class="stat medium">
                <span class="label">Medium Severity</span>
                <span class="value">{report.risk_summary.medium_severity_count}</span>
            </div>
            <div class="stat low">
                <span class="label">Low Severity</span>
                <span class="value">{report.risk_summary.low_severity_count}</span>
            </div>
            <div class="stat">
                <span class="label">Missing Clauses</span>
                <span class="value">{report.risk_summary.total_missing_clauses}</span>
            </div>
        </div>
    </div>
    """
    
    # Risky clauses
    risky_html = "<div class='risky-clauses'><h2>Risky Clauses</h2>"
    for risky in report.risky_clauses:
        risky_html += f"""
        <div class="finding {risky.severity}">
            <h3>Clause {risky.clause_number}</h3>
            <p class="clause-text">{risky.clause_text}</p>
            <p class="explanation"><strong>Analysis:</strong> {risky.explanation}</p>
            <p class="citation"><strong>Reference:</strong> {risky.formatted_citation}</p>
        </div>
        """
    risky_html += "</div>"
    
    # Missing clauses
    missing_html = "<div class='missing-clauses'><h2>Missing Clauses</h2>"
    for missing in report.missing_clauses:
        missing_html += f"""
        <div class="finding {missing.severity}">
            <h3>Missing: {missing.expected_clause_type}</h3>
            <p class="explanation"><strong>Why Expected:</strong> {missing.explanation}</p>
            <p class="citation"><strong>Reference:</strong> {missing.formatted_citation}</p>
        </div>
        """
    missing_html += "</div>"
    
    # Legal references
    refs_html = "<div class='legal-references'><h2>Legal References</h2><ul>"
    for ref in report.legal_references:
        refs_html += f"<li>{ref.citation} <em>(cited {ref.usage_count}x)</em></li>"
    refs_html += "</ul></div>"
    
    # Combine
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Contract Report</title></head>
    <body>
        {cover}
        <div class="page-break"></div>
        {summary}
        <div class="page-break"></div>
        {risky_html}
        <div class="page-break"></div>
        {missing_html}
        <div class="page-break"></div>
        {refs_html}
    </body>
    </html>
    """

def _get_pdf_styles() -> str:
    """PDF-specific CSS styles."""
    return """
    @page {
        size: A4;
        margin: 2cm;
    }
    
    body {
        font-family: Arial, sans-serif;
        color: #1f2937;
        line-height: 1.6;
    }
    
    .cover-page {
        text-align: center;
        padding-top: 5cm;
    }
    
    .cover-page h1 {
        font-size: 2.5em;
        color: #1e40af;
    }
    
    .filename {
        font-size: 1.2em;
        margin-top: 2em;
    }
    
    .page-break {
        page-break-after: always;
    }
    
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1em;
        margin-top: 2em;
    }
    
    .stat {
        padding: 1em;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
    }
    
    .stat.high { border-left: 4px solid #dc2626; }
    .stat.medium { border-left: 4px solid #f59e0b; }
    .stat.low { border-left: 4px solid #3b82f6; }
    
    .finding {
        margin-bottom: 2em;
        padding: 1em;
        border-left: 4px solid #6b7280;
        background: #f9fafb;
    }
    
    .finding.high { border-left-color: #dc2626; }
    .finding.medium { border-left-color: #f59e0b; }
    .finding.low { border-left-color: #3b82f6; }
    
    .clause-text {
        font-style: italic;
        margin: 1em 0;
    }
    
    .citation {
        font-size: 0.9em;
        color: #6b7280;
    }
    """
```


### FastAPI Endpoints

**File: backend/app/api/routes/reports.py**

```python
"""
Report generation API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO
import logging

from ...db.database import get_db
from ...reports.assembler import assemble_contract_report
from ...reports.pdf_generator import generate_pdf_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["reports"])

@router.get("/{contract_id}/report")
async def get_contract_report(
    contract_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get complete contract analysis report.
    
    Returns all pipeline outputs in single structured response.
    
    Args:
        contract_id: Contract UUID
        db: Database session
    
    Returns:
        {
            "success": true,
            "data": {
                "contract_id": "...",
                "clauses": [...],
                "risky_clauses": [...],
                "missing_clauses": [...],
                "risk_summary": {...},
                "legal_references": [...]
            },
            "error": null
        }
    """
    try:
        report = await assemble_contract_report(contract_id, db)
        
        return {
            "success": True,
            "data": report.model_dump(),
            "error": None
        }
        
    except ValueError as e:
        # Contract not found or not ready
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to assemble report for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{contract_id}/report/pdf")
async def download_pdf_report(
    contract_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Download contract analysis report as PDF.
    
    Args:
        contract_id: Contract UUID
        db: Database session
    
    Returns:
        PDF file download
    """
    try:
        # Assemble report data
        report = await assemble_contract_report(contract_id, db)
        
        # Generate PDF
        pdf_bytes = generate_pdf_report(report)
        
        # Return as downloadable file
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=contract-report-{contract_id[:8]}.pdf"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to generate PDF for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")
```


### Frontend Architecture

**Component Structure:**
```
frontend/src/
├── pages/
│   └── ReportView.tsx           # Main report page
├── components/
│   ├── RiskSummaryHeader.tsx    # Sticky summary header
│   ├── ContractText.tsx         # Highlighted contract display
│   ├── ClauseHighlight.tsx      # Individual highlighted clause
│   ├── ExplanationPanel.tsx     # Side panel with explanation
│   ├── MissingClausesPanel.tsx  # Missing clauses section
│   └── LoadingState.tsx         # Skeleton loaders
├── hooks/
│   ├── useContractReport.ts     # Fetch report hook
│   └── usePDFDownload.ts        # PDF download hook
├── types/
│   └── report.types.ts          # TypeScript interfaces
└── utils/
    └── severity.ts              # Severity color helpers
```

### Frontend Data Types

**File: frontend/src/types/report.types.ts**

```typescript
export type Severity = 'low' | 'medium' | 'high';

export interface ClauseWithRisk {
  clause_id: string;
  clause_number: string;
  clause_text: string;
  clause_type: string | null;
  is_risky: boolean;
  risk_severity: Severity | null;
  position: number;
}

export interface RiskyClauseReport {
  clause_id: string;
  clause_number: string;
  clause_text: string;
  reason: string;
  explanation: string;
  formatted_citation: string;
  severity: Severity;
}

export interface MissingClauseReport {
  expected_clause_type: string;
  why_expected: string;
  explanation: string;
  formatted_citation: string;
  severity: Severity;
}

export interface RiskSummary {
  total_clauses: number;
  total_risky_clauses: number;
  total_missing_clauses: number;
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
}

export interface LegalReference {
  citation: string;
  source_type: 'legal_rule' | 'reference_corpus';
  usage_count: number;
}

export interface ContractReport {
  contract_id: string;
  filename: string;
  upload_timestamp: string;
  processing_status: string;
  clauses: ClauseWithRisk[];
  risky_clauses: RiskyClauseReport[];
  missing_clauses: MissingClauseReport[];
  risk_summary: RiskSummary;
  legal_references: LegalReference[];
}

export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: string | null;
}
```


### Main Report View Component

**File: frontend/src/pages/ReportView.tsx**

```tsx
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useContractReport } from '../hooks/useContractReport';
import { usePDFDownload } from '../hooks/usePDFDownload';
import RiskSummaryHeader from '../components/RiskSummaryHeader';
import ContractText from '../components/ContractText';
import ExplanationPanel from '../components/ExplanationPanel';
import MissingClausesPanel from '../components/MissingClausesPanel';
import LoadingState from '../components/LoadingState';
import type { RiskyClauseReport } from '../types/report.types';

const ReportView: React.FC = () => {
  const { contractId } = useParams<{ contractId: string }>();
  const { report, loading, error, retry } = useContractReport(contractId!);
  const { downloadPDF, downloading } = usePDFDownload(contractId!);
  
  const [selectedClause, setSelectedClause] = useState<RiskyClauseReport | null>(null);
  
  if (loading) {
    return <LoadingState />;
  }
  
  if (error) {
    return (
      <div className="error-container">
        <h2>Unable to Load Report</h2>
        <p>{error}</p>
        <button onClick={retry} className="btn-primary">
          Retry
        </button>
      </div>
    );
  }
  
  if (!report) {
    return null;
  }
  
  const handleClauseClick = (clauseId: string) => {
    const riskyClause = report.risky_clauses.find(
      (c) => c.clause_id === clauseId
    );
    if (riskyClause) {
      setSelectedClause(riskyClause);
    }
  };
  
  return (
    <div className="report-view">
      <RiskSummaryHeader
        summary={report.risk_summary}
        filename={report.filename}
        onDownload={downloadPDF}
        downloading={downloading}
      />
      
      <div className="report-content">
        <main className="contract-section">
          <h2>Contract Analysis</h2>
          <ContractText
            clauses={report.clauses}
            onClauseClick={handleClauseClick}
          />
        </main>
        
        <aside className="missing-section">
          <MissingClausesPanel
            missingClauses={report.missing_clauses}
          />
        </aside>
      </div>
      
      {selectedClause && (
        <ExplanationPanel
          clause={selectedClause}
          onClose={() => setSelectedClause(null)}
        />
      )}
    </div>
  );
};

export default ReportView;
```

### Custom Hooks

**File: frontend/src/hooks/useContractReport.ts**

```typescript
import { useState, useEffect } from 'react';
import type { ContractReport, APIResponse } from '../types/report.types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const useContractReport = (contractId: string) => {
  const [report, setReport] = useState<ContractReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/contracts/${contractId}/report`
      );
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Contract not found or report not ready');
        }
        throw new Error('Failed to load report');
      }
      
      const result: APIResponse<ContractReport> = await response.json();
      
      if (result.success && result.data) {
        setReport(result.data);
      } else {
        throw new Error(result.error || 'Unknown error');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    if (contractId) {
      fetchReport();
    }
  }, [contractId]);
  
  return {
    report,
    loading,
    error,
    retry: fetchReport,
  };
};
```

**File: frontend/src/hooks/usePDFDownload.ts**

```typescript
import { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const usePDFDownload = (contractId: string) => {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const downloadPDF = async () => {
    setDownloading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/contracts/${contractId}/report/pdf`
      );
      
      if (!response.ok) {
        throw new Error('Failed to download PDF');
      }
      
      // Create blob and download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `contract-report-${contractId.slice(0, 8)}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };
  
  return {
    downloadPDF,
    downloading,
    error,
  };
};
```


### UI Components

**File: frontend/src/components/RiskSummaryHeader.tsx**

```tsx
import React from 'react';
import type { RiskSummary } from '../types/report.types';

interface Props {
  summary: RiskSummary;
  filename: string;
  onDownload: () => void;
  downloading: boolean;
}

const RiskSummaryHeader: React.FC<Props> = ({
  summary,
  filename,
  onDownload,
  downloading,
}) => {
  return (
    <header className="risk-summary-header sticky top-0 bg-white shadow-md z-10 p-4">
      <div className="container mx-auto flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">{filename}</h1>
          <p className="text-gray-600">Contract Analysis Report</p>
        </div>
        
        <div className="flex gap-4 items-center">
          <div className="stat">
            <span className="label">Total Clauses</span>
            <span className="value">{summary.total_clauses}</span>
          </div>
          
          <div className="stat high">
            <span className="label">High Risk</span>
            <span className="value text-red-600">{summary.high_severity_count}</span>
          </div>
          
          <div className="stat medium">
            <span className="label">Medium Risk</span>
            <span className="value text-yellow-600">{summary.medium_severity_count}</span>
          </div>
          
          <div className="stat low">
            <span className="label">Low Risk</span>
            <span className="value text-blue-600">{summary.low_severity_count}</span>
          </div>
          
          <div className="stat">
            <span className="label">Missing</span>
            <span className="value">{summary.total_missing_clauses}</span>
          </div>
          
          <button
            onClick={onDownload}
            disabled={downloading}
            className="btn-primary"
            data-testid="download-pdf-button"
          >
            {downloading ? 'Generating PDF...' : 'Download PDF'}
          </button>
        </div>
      </div>
    </header>
  );
};

export default RiskSummaryHeader;
```

**File: frontend/src/components/ContractText.tsx**

```tsx
import React from 'react';
import ClauseHighlight from './ClauseHighlight';
import type { ClauseWithRisk } from '../types/report.types';

interface Props {
  clauses: ClauseWithRisk[];
  onClauseClick: (clauseId: string) => void;
}

const ContractText: React.FC<Props> = ({ clauses, onClauseClick }) => {
  return (
    <div className="contract-text space-y-4">
      {clauses.map((clause) => (
        <ClauseHighlight
          key={clause.clause_id}
          clause={clause}
          onClick={() => {
            if (clause.is_risky) {
              onClauseClick(clause.clause_id);
            }
          }}
        />
      ))}
    </div>
  );
};

export default ContractText;
```

**File: frontend/src/components/ClauseHighlight.tsx**

```tsx
import React from 'react';
import { getSeverityColor } from '../utils/severity';
import type { ClauseWithRisk } from '../types/report.types';

interface Props {
  clause: ClauseWithRisk;
  onClick: () => void;
}

const ClauseHighlight: React.FC<Props> = ({ clause, onClick }) => {
  const isClickable = clause.is_risky;
  const backgroundColor = clause.risk_severity
    ? getSeverityColor(clause.risk_severity)
    : 'transparent';
  
  return (
    <div
      className={`clause ${isClickable ? 'cursor-pointer hover:opacity-80' : ''}`}
      onClick={isClickable ? onClick : undefined}
      style={{ backgroundColor }}
      data-testid={`clause-${clause.clause_number}`}
      data-risky={clause.is_risky}
      data-severity={clause.risk_severity || ''}
    >
      <span className="clause-number font-semibold mr-2">
        {clause.clause_number}
      </span>
      <span className="clause-text">{clause.clause_text}</span>
    </div>
  );
};

export default ClauseHighlight;
```

**File: frontend/src/components/ExplanationPanel.tsx**

```tsx
import React, { useEffect } from 'react';
import type { RiskyClauseReport } from '../types/report.types';
import { getSeverityBadge } from '../utils/severity';

interface Props {
  clause: RiskyClauseReport;
  onClose: () => void;
}

const ExplanationPanel: React.FC<Props> = ({ clause, onClose }) => {
  // Close on ESC key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);
  
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-20"
        onClick={onClose}
        data-testid="explanation-backdrop"
      />
      
      {/* Panel */}
      <aside
        className="fixed right-0 top-0 h-full w-96 bg-white shadow-lg z-30 overflow-y-auto animate-slide-in"
        data-testid="explanation-panel"
      >
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-xl font-bold">Clause {clause.clause_number}</h3>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
              aria-label="Close panel"
            >
              ✕
            </button>
          </div>
          
          <div className="mb-4">
            {getSeverityBadge(clause.severity)}
          </div>
          
          <div className="mb-4">
            <h4 className="font-semibold mb-2">Clause Text</h4>
            <p className="text-sm text-gray-700 italic">{clause.clause_text}</p>
          </div>
          
          <div className="mb-4">
            <h4 className="font-semibold mb-2">Analysis</h4>
            <p className="text-sm text-gray-700">{clause.explanation}</p>
          </div>
          
          <div>
            <h4 className="font-semibold mb-2">Legal Reference</h4>
            <p className="text-sm text-gray-600">{clause.formatted_citation}</p>
          </div>
        </div>
      </aside>
    </>
  );
};

export default ExplanationPanel;
```


**File: frontend/src/components/MissingClausesPanel.tsx**

```tsx
import React from 'react';
import type { MissingClauseReport } from '../types/report.types';
import { getSeverityBadge } from '../utils/severity';

interface Props {
  missingClauses: MissingClauseReport[];
}

const MissingClausesPanel: React.FC<Props> = ({ missingClauses }) => {
  if (missingClauses.length === 0) {
    return (
      <div className="missing-clauses-panel">
        <h2 className="text-xl font-bold mb-4">Missing Clauses</h2>
        <p className="text-green-600">✓ No critical clauses missing</p>
      </div>
    );
  }
  
  return (
    <div className="missing-clauses-panel" data-testid="missing-clauses-panel">
      <h2 className="text-xl font-bold mb-4">Missing Clauses</h2>
      <p className="text-sm text-gray-600 mb-4">
        These clauses are typically expected in contracts of this type but were not found.
      </p>
      
      <div className="space-y-4">
        {missingClauses.map((missing, index) => (
          <div
            key={index}
            className="card border border-gray-200 rounded-lg p-4"
            data-testid={`missing-clause-${index}`}
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-semibold">{missing.expected_clause_type}</h3>
              {getSeverityBadge(missing.severity)}
            </div>
            
            <p className="text-sm text-gray-700 mb-2">
              {missing.explanation}
            </p>
            
            <p className="text-xs text-gray-500">
              Reference: {missing.formatted_citation}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MissingClausesPanel;
```

**File: frontend/src/utils/severity.ts**

```typescript
import type { Severity } from '../types/report.types';

export const getSeverityColor = (severity: Severity): string => {
  switch (severity) {
    case 'high':
      return '#FEE2E2'; // Light red
    case 'medium':
      return '#FEF3C7'; // Light yellow
    case 'low':
      return '#DBEAFE'; // Light blue
    default:
      return 'transparent';
  }
};

export const getSeverityBadge = (severity: Severity): JSX.Element => {
  const colors = {
    high: 'bg-red-100 text-red-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
  };
  
  return (
    <span
      className={`inline-block px-2 py-1 text-xs font-semibold rounded ${colors[severity]}`}
      data-testid={`severity-badge-${severity}`}
    >
      {severity.toUpperCase()}
    </span>
  );
};
```


## Test Plan

### Backend Tests

**Test File:** `backend/tests/test_reports.py`

**TC-1: Report Assembly - Complete Data**
- Contract with clauses, findings, explanations
- Call assemble_contract_report()
- Verify: All fields populated correctly
- Verify: Risk map accurate
- Verify: Summary counts correct

**TC-2: Report Assembly - Missing Explanations**
- Some findings without explanations
- Verify: Returns "Explanation pending..." placeholder
- Verify: Report still generated successfully

**TC-3: Report Assembly - No Risks Found**
- Contract processed but no risks
- Verify: Empty risky_clauses and missing_clauses arrays
- Verify: Summary shows 0 counts

**TC-4: Report Assembly - Contract Not Found**
- Invalid contract_id
- Verify: ValueError raised with clear message

**TC-5: Report Assembly - Processing Incomplete**
- Contract status = "processing"
- Verify: ValueError raised
- Verify: Message indicates not ready

**TC-6: Legal References Deduplication**
- Multiple findings reference same legal rule
- Verify: Reference appears once with correct usage_count
- Verify: References ordered by usage (most used first)

**TC-7: JSON Endpoint - Success**
- GET /api/contracts/{id}/report
- Verify: 200 status
- Verify: Envelope structure correct
- Verify: success=true, data populated, error=null

**TC-8: JSON Endpoint - Not Found**
- GET with invalid contract_id
- Verify: 404 status
- Verify: Error message clear

**TC-9: PDF Endpoint - Success**
- GET /api/contracts/{id}/report/pdf
- Verify: 200 status
- Verify: Content-Type = application/pdf
- Verify: Content-Disposition header present
- Verify: PDF bytes returned

**TC-10: PDF Generation - Content Validation**
- Generate PDF for known report
- Verify: PDF contains contract filename
- Verify: PDF contains risk summary
- Verify: PDF contains explanations

### Frontend Tests (React Testing Library)

**Test File:** `frontend/src/components/__tests__/RiskSummaryHeader.test.tsx`

**TC-11: Risk Summary Header Rendering**
- Render with mock summary data
- Verify: All counts displayed correctly
- Verify: Filename shown
- Verify: Download button present

**TC-12: Download Button Click**
- Click download button
- Verify: onDownload callback invoked
- Verify: Button shows "Generating PDF..." when downloading

**Test File:** `frontend/src/components/__tests__/ClauseHighlight.test.tsx`

**TC-13: Risky Clause Highlighting - High Severity**
- Render risky clause with severity="high"
- Verify: Background color is red (#FEE2E2)
- Verify: Clickable (cursor-pointer class)
- Verify: data-risky="true"

**TC-14: Risky Clause Highlighting - Medium Severity**
- severity="medium"
- Verify: Background color is yellow (#FEF3C7)

**TC-15: Non-Risky Clause**
- is_risky=false
- Verify: No background color
- Verify: Not clickable

**TC-16: Clause Click Interaction**
- Click risky clause
- Verify: onClick callback invoked with correct clause_id

**Test File:** `frontend/src/components/__tests__/ExplanationPanel.test.tsx**

**TC-17: Explanation Panel Display**
- Render panel with mock clause data
- Verify: Clause number shown
- Verify: Severity badge displayed
- Verify: Explanation text rendered
- Verify: Citation shown

**TC-18: Panel Close - Button**
- Click close button
- Verify: onClose callback invoked

**TC-19: Panel Close - Backdrop**
- Click backdrop
- Verify: onClose callback invoked

**TC-20: Panel Close - ESC Key**
- Press ESC key
- Verify: onClose callback invoked

**Test File:** `frontend/src/components/__tests__/MissingClausesPanel.test.tsx`

**TC-21: Missing Clauses Display**
- Render with 3 missing clauses
- Verify: All 3 cards rendered
- Verify: Each shows expected_clause_type
- Verify: Explanations shown

**TC-22: No Missing Clauses**
- Render with empty array
- Verify: Success message shown
- Verify: No cards rendered

### E2E Tests (Playwright)

**Test File:** `frontend/e2e/report.spec.ts`

**TC-23: Full Report Flow**
- Navigate to /report/:contractId
- Verify: Loading state appears
- Verify: Report loads successfully
- Verify: Summary header visible
- Verify: Clauses displayed

**TC-24: Clause Interaction Flow**
- Click highlighted clause
- Verify: Explanation panel opens
- Verify: Panel contains correct data
- Close panel
- Verify: Panel disappears

**TC-25: PDF Download Flow**
- Click "Download PDF" button
- Verify: Button shows loading state
- Verify: PDF file downloads
- Verify: Filename correct

**TC-26: Error Handling**
- Navigate with invalid contract_id
- Verify: Error message displayed
- Verify: Retry button present
- Click retry
- Verify: Refetch attempted


## Dependencies

**Backend:**
```python
# PDF generation
weasyprint>=60.0
```

**Frontend:**
```json
{
  "dependencies": {
    "react": "^18.x",
    "react-dom": "^18.x",
    "react-router-dom": "^6.x"
  },
  "devDependencies": {
    "@testing-library/react": "^14.x",
    "@testing-library/user-event": "^14.x",
    "@playwright/test": "^1.40.0"
  }
}
```

## Environment Variables

**Backend:** (all already configured from previous stages)

**Frontend:**
```bash
# Already configured from Stage 1
VITE_API_BASE_URL=http://localhost:8000
```

## Performance Benchmarks

**Backend:**
- Report assembly: <500ms (typical 50-clause contract)
- PDF generation: <5 seconds (includes HTML rendering)
- JSON response size: ~50KB (compressed)

**Frontend:**
- Initial render: <2 seconds
- Clause highlight interaction: <100ms
- Panel open/close: <200ms (animated)
- PDF download initiation: <50ms

## Out of Scope

- Inline editing of clauses
- Comparison of multiple contracts
- Contract version history
- Customizable report templates
- Export to Word/Excel
- Sharing/collaboration features
- Automated email distribution
- Print layout optimization (beyond PDF)
- Multi-language UI
- Mobile app version

## Success Criteria

**Backend:**
- [ ] GET /api/contracts/{id}/report returns complete structured data
- [ ] Report includes clauses, risks, missing, summary, references
- [ ] GET /api/contracts/{id}/report/pdf generates valid PDF
- [ ] PDF contains all sections (cover, summary, findings, references)
- [ ] PDF downloadable with correct filename
- [ ] Legal references deduplicated correctly
- [ ] Report assembly handles missing data gracefully

**Frontend:**
- [ ] ReportView renders report successfully
- [ ] Risk summary header shows correct counts
- [ ] Clauses highlighted by severity (red/yellow/blue)
- [ ] Clicking risky clause opens explanation panel
- [ ] Panel shows explanation and citation
- [ ] Panel closes on X, backdrop, or ESC
- [ ] Missing clauses displayed in separate section
- [ ] Download PDF button triggers PDF download
- [ ] Loading states shown during fetch/download
- [ ] Error states handled with retry option
- [ ] Responsive on mobile and desktop
- [ ] All 26 tests pass (backend + frontend + E2E)


## Files to Create/Modify

### Backend Files

**New:**
1. `backend/app/reports/__init__.py`
2. `backend/app/reports/assembler.py` - Report assembly logic
3. `backend/app/reports/models.py` - Report Pydantic models
4. `backend/app/reports/pdf_generator.py` - PDF generation
5. `backend/app/api/routes/reports.py` - Report endpoints

**Modified:**
6. `backend/app/main.py` - Register reports router
7. `backend/requirements.txt` - Add weasyprint

**Tests:**
8. `backend/tests/test_reports.py` - Backend report tests
9. `backend/tests/test_api_reports.py` - API endpoint tests

### Frontend Files

**New:**
10. `frontend/src/pages/ReportView.tsx` - Main report page
11. `frontend/src/components/RiskSummaryHeader.tsx`
12. `frontend/src/components/ContractText.tsx`
13. `frontend/src/components/ClauseHighlight.tsx`
14. `frontend/src/components/ExplanationPanel.tsx`
15. `frontend/src/components/MissingClausesPanel.tsx`
16. `frontend/src/components/LoadingState.tsx`
17. `frontend/src/hooks/useContractReport.ts`
18. `frontend/src/hooks/usePDFDownload.ts`
19. `frontend/src/types/report.types.ts`
20. `frontend/src/utils/severity.ts`

**Modified:**
21. `frontend/src/App.tsx` - Add /report/:contractId route
22. `frontend/src/index.css` - Add report-specific styles

**Tests:**
23. `frontend/src/components/__tests__/RiskSummaryHeader.test.tsx`
24. `frontend/src/components/__tests__/ClauseHighlight.test.tsx`
25. `frontend/src/components/__tests__/ExplanationPanel.test.tsx`
26. `frontend/src/components/__tests__/MissingClausesPanel.test.tsx`
27. `frontend/e2e/report.spec.ts` - Playwright E2E tests

## Design Tradeoffs

### Single JSON Endpoint vs Multiple Endpoints

**Chosen: Single comprehensive endpoint**

**Pros:**
- Single HTTP request (faster load)
- Atomic snapshot of data
- Simpler client logic
- Reduced server load

**Cons:**
- Larger response payload
- Can't lazy-load sections

**Rationale:** Report is typically viewed as a whole, so single request is optimal.

### PDF Generation: weasyprint vs Alternatives

**Chosen: weasyprint (HTML→PDF)**

**Pros:**
- HTML/CSS familiar to developers
- Consistent styling with web UI
- Good rendering quality
- Pure Python (no external dependencies)

**Cons:**
- Slower than native PDF libraries
- Large dependency size

**Alternatives Considered:**
- ReportLab: Programmatic (harder to maintain)
- Puppeteer: Requires Node/Chrome (complex)
- LaTeX: Overkill for this use case

### Client-Side vs Server-Side Clause Highlighting

**Chosen: Client-side (React components)**

**Pros:**
- Interactive (click handlers, hover effects)
- Smooth animations
- No page reloads

**Cons:**
- Requires JavaScript
- Larger initial bundle

**Rationale:** Interactivity is core feature, worth the bundle size.


## Notes

- This spec covers Stage 9 (Final Report Assembly & UI) of the ScanTract pipeline
- Completes the end-to-end pipeline: Upload → Analysis → Results
- Backend provides both JSON (interactive UI) and PDF (download) formats
- Frontend emphasizes usability: clear visual hierarchy, intuitive interactions
- All citations traceable through entire pipeline (Stage 7 → 8 → 9)
- Use Conventional Commits: `feat:` for new features, `test:` for tests

## References

- weasyprint docs: https://doc.courtbouillon.org/weasyprint/
- React Router: https://reactrouter.com/
- React Testing Library: https://testing-library.com/react
- Playwright: https://playwright.dev/
- Tailwind CSS: https://tailwindcss.com/

## Appendix: Complete Pipeline Summary

**Stage 1:** Frontend upload page ✓  
**Stage 2:** Document processing (PDF/DOCX → clauses) ✓  
**Stage 3:** Prompt templating ✓  
**Stage 4:** Clause classification ✓  
**Stage 5A:** Legal rules KB search ✓  
**Stage 5B:** Reference corpus search ✓  
**Stage 6:** Retrieval merge & deduplication ✓  
**Stage 7:** Risk detection with traceability ✓  
**Stage 8:** Explanation generation & citation formatting ✓  
**Stage 9:** Report assembly & interactive UI ✓

**Complete Pipeline Flow:**

1. User uploads contract (PDF/DOCX)
2. Backend extracts text, segments clauses
3. LLM classifies each clause
4. Search legal KB for relevant rules
5. Search corpus for reference examples
6. Merge and dedupe context
7. LLM detects risks with traced citations
8. Generate plain-language explanations
9. Assemble report, render UI with highlights

**User Journey:**
```
Upload → Processing (30-60s) → Report View
         ↓                     ↓
    Loading spinner      Highlighted clauses
                         Risk summary
                         Explanations
                         Download PDF
```

**Data Flow:**
```
File → Text → Clauses → Classifications → Context → Risks → Explanations → Report → UI
  ↓      ↓       ↓           ↓              ↓        ↓          ↓          ↓     ↓
 DB     DB      DB          DB             KB       DB         DB         JSON  PDF
```

All 9 stages integrated into cohesive end-to-end system! 🎉

