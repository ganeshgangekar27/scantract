# Stage 9: Report Assembly and UI - Backend Tasks

**Scope:** Backend half only (PDF generation, API endpoints, report assembly logic)  
**Frontend tasks:** Separate tasks.md after backend verification

---

## Task 1: Create Report Module Structure

**Files to create:**
- `backend/app/reports/__init__.py`
- `backend/app/reports/models.py`
- `backend/app/reports/assembler.py`
- `backend/app/reports/pdf_generator.py`

**Action:**
Create the empty module structure with basic docstrings. The `__init__.py` should export key functions for easy importing:
```python
from .assembler import assemble_contract_report
from .pdf_generator import generate_pdf_report
from .models import ContractReport

__all__ = ['assemble_contract_report', 'generate_pdf_report', 'ContractReport']
```

**Verification:**
- All four files exist
- Module is importable: `from app.reports import assemble_contract_report`

---

## Task 2: Implement Report Pydantic Models

**File:** `backend/app/reports/models.py`

**Models to implement:**

1. **ClauseWithRisk**
   - `clause_id: int` (INTEGER, not UUID)
   - `clause_number: str` (e.g., "4.2")
   - `clause_text: str`
   - `has_risk: bool`
   - `risk_severity: Optional[str]` (None if no risk, else "high"/"medium"/"low")
   - `risk_reason: Optional[str]`

2. **RiskyClauseReport**
   - `finding_id: str` (UUID as string)
   - `clause_id: int` (INTEGER)
   - `clause_number: str`
   - `clause_text: str`
   - `severity: str` ("high"/"medium"/"low")
   - `reason: str`
   - `explanation: str` (from Stage 8 cached value)
   - `formatted_citation: str` (from Stage 8 cached value)

3. **MissingClauseReport**
   - `finding_id: str` (UUID as string)
   - `expected_clause_type: str`
   - `severity: str`
   - `reason: str`
   - `explanation: str`
   - `formatted_citation: str`

4. **RiskSummary**
   - `total_clauses: int`
   - `risky_clauses_count: int`
   - `missing_clauses_count: int`
   - `high_severity_count: int`
   - `medium_severity_count: int`
   - `low_severity_count: int`
   - `overall_risk_level: str` ("high"/"medium"/"low"/"none")
     - Computed: "high" if any high-severity findings, "medium" if any medium (but no high), "low" if any low (but no high/medium), "none" otherwise

5. **LegalReference**
   - `citation: str` (formatted citation from Stage 8)
   - `usage_count: int` (how many findings reference this citation)

6. **ContractReport**
   - `contract_id: int` (INTEGER)
   - `filename: str`
   - `upload_date: datetime`
   - `all_clauses: List[ClauseWithRisk]` (ordered by clause_number)
   - `risky_clauses: List[RiskyClauseReport]` (ordered by severity desc, then clause_number)
   - `missing_clauses: List[MissingClauseReport]` (ordered by severity desc)
   - `risk_summary: RiskSummary`
   - `legal_references: List[LegalReference]` (ordered by usage_count desc, then alphabetically)

**Requirements:**
- All models use Pydantic v2 (inheriting from `BaseModel`)
- All `contract_id` and `clause_id` fields typed as `int` (not UUID)
- Include docstrings explaining each model's purpose

**Verification:**
- All 6 models defined
- Models are importable: `from app.reports.models import ContractReport`
- Type hints correctly use `int` for contract_id and clause_id

---

## Task 3: Implement Report Assembly Logic

**File:** `backend/app/reports/assembler.py`

**Function signature:**
```python
async def assemble_contract_report(
    contract_id: int,
    db: AsyncSession
) -> ContractReport:
    """
    Assemble complete report for a contract.
    
    Args:
        contract_id: Contract ID (INTEGER)
        db: Database session
    
    Returns:
        ContractReport with all clauses, risks, and references
    
    Raises:
        ValueError: If contract not found or processing incomplete
    """
```

**Implementation steps:**

1. **Fetch contract from database**
   - Query `contracts` table by `id` (INTEGER)
   - Raise `ValueError("Contract not found")` if missing
   - Raise `ValueError("Contract processing not complete")` if `processing_status != 'complete'`

2. **Ensure all explanations are cached**
   - Call `generate_all_explanations(contract_id, db)` from Stage 8's `app.llm.generate_explanations`
   - This ensures `explanation` and `formatted_citation` are populated in `risk_findings`

3. **Fetch all clauses for the contract**
   - Query `clauses` table where `contract_id` matches (ordered by `clause_id` for natural ordering)
   - Build `ClauseWithRisk` objects for each clause

4. **Fetch all risk findings with cached explanations**
   - Query `risk_findings` table where `contract_id` matches
   - Join with `clauses` table for risky clause findings (where `clause_id IS NOT NULL`)
   - Read `explanation` and `formatted_citation` columns directly (Stage 8 cached values)

5. **Build risk map**
   - Create a dict mapping `clause_id -> List[RiskFinding]` for risky clauses
   - Use this to annotate `ClauseWithRisk.has_risk`, `risk_severity`, `risk_reason`

6. **Build RiskyClauseReport and MissingClauseReport lists**
   - For risky clauses: include clause details + cached explanation/citation
   - For missing clauses: include expected type + cached explanation/citation
   - Order risky clauses by severity (high first), then clause_number
   - Order missing clauses by severity (high first)

7. **Compute RiskSummary**
   - Count total clauses, risky clauses, missing clauses
   - Count high/medium/low severity findings
   - Determine `overall_risk_level` (high if any high-severity, medium if any medium but no high, low if any low but no high/medium, none otherwise)

8. **Deduplicate legal references**
   - Extract all unique `formatted_citation` values from findings
   - Count how many findings reference each citation (`usage_count`)
   - Order by usage_count desc, then alphabetically by citation text

9. **Return ContractReport**

**Dependencies:**
- `from sqlalchemy import select`
- `from sqlalchemy.ext.asyncio import AsyncSession`
- `from ..db.models import Contract, Clause, RiskFinding`
- `from ..llm.generate_explanations import generate_all_explanations`
- `from .models import ContractReport, ClauseWithRisk, ...`

**Error handling:**
- Raise `ValueError` with clear message if contract not found
- Raise `ValueError` if processing_status is not 'complete'

**Verification:**
- Function is async and takes `contract_id: int, db: AsyncSession`
- Returns `ContractReport` object
- Calls `generate_all_explanations()` to ensure cached values exist

---

## Task 4: Verify and Install weasyprint, Implement PDF Generation

**Subtask 4a: Verify weasyprint Installation**

**Action:**
1. Check if weasyprint is installed: `pip show weasyprint`
2. If not installed: `pip install weasyprint`
3. Add to `backend/requirements.txt`:
   ```
   # PDF Generation
   weasyprint>=60.0  # HTML to PDF conversion for reports
   ```
4. Test import: `python -c "import weasyprint; print(weasyprint.__version__)"`

**Expected output:** Version number printed (e.g., "60.2" or similar)

**Verification:**
- `pip show weasyprint` succeeds
- `import weasyprint` works without error
- `requirements.txt` includes weasyprint entry

---

**Subtask 4b: Implement PDF Generator**

**File:** `backend/app/reports/pdf_generator.py`

**Function signature:**
```python
def generate_pdf_report(report: ContractReport) -> bytes:
    """
    Generate PDF report from ContractReport data.
    
    Args:
        report: ContractReport with all data assembled
    
    Returns:
        bytes: PDF file content
    """
```

**Implementation:**

1. **Build HTML structure** (using Python f-strings or template library)
   - Cover page: contract filename, date, overall risk level
   - Risk summary section: counts table (total clauses, risky, missing, severity breakdown)
   - Risky clauses section: for each risky clause, show:
     - Clause number and text (highlighted)
     - Severity badge
     - Reason
     - Plain-language explanation
     - Legal citation
   - Missing clauses section: for each missing clause, show:
     - Expected clause type
     - Severity badge
     - Reason
     - Explanation
     - Legal citation
   - Legal references appendix: table of all citations with usage counts

2. **Apply CSS styling**
   - Cover page: centered title, date, risk level badge (colored by severity)
   - Risk summary: table with borders
   - Clauses: card-style boxes with borders
   - Severity badges: colored backgrounds (red=high, orange=medium, yellow=low)
   - Citations: monospace font, gray background
   - Page breaks: avoid breaking clause boxes mid-content

3. **Generate PDF using weasyprint**
   ```python
   from weasyprint import HTML, CSS
   from io import BytesIO
   
   html = HTML(string=html_content)
   css = CSS(string=css_styles)
   pdf_bytes = BytesIO()
   html.write_pdf(pdf_bytes, stylesheets=[css])
   return pdf_bytes.getvalue()
   ```

**Styling structure (embedded CSS or separate string):**
```css
body { font-family: Arial, sans-serif; margin: 2cm; }
.cover-page { text-align: center; page-break-after: always; }
.risk-badge { padding: 4px 8px; border-radius: 4px; font-weight: bold; }
.risk-badge.high { background: #fee; color: #c00; }
.risk-badge.medium { background: #ffe; color: #c60; }
.risk-badge.low { background: #ffa; color: #960; }
.clause-box { border: 1px solid #ccc; padding: 16px; margin: 16px 0; page-break-inside: avoid; }
.citation { font-family: monospace; background: #f5f5f5; padding: 2px 4px; }
```

**Dependencies:**
- `from weasyprint import HTML, CSS`
- `from io import BytesIO`
- `from .models import ContractReport`

**Verification:**
- Function takes `ContractReport` and returns `bytes`
- PDF contains cover page, risk summary, clause sections, legal references
- Severity badges are styled with colors
- No errors when generating PDF from a complete ContractReport

---

## Task 5: Implement Report API Endpoints

**File:** `backend/app/api/routes/reports.py`

**Create router:**
```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO
import logging

from ...reports import assemble_contract_report, generate_pdf_report
from ...db.models import Contract  # For get_db dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["reports"])

# Placeholder for get_db dependency
async def get_db():
    """Database dependency placeholder."""
    raise NotImplementedError("Database dependency not configured")
```

**Endpoints to implement:**

1. **GET /api/contracts/{contract_id}/report**
   ```python
   @router.get("/{contract_id}/report")
   async def get_contract_report(
       contract_id: int,
       db: AsyncSession = Depends(get_db)
   ) -> dict:
       """
       Get complete contract report (JSON).
       
       Returns:
           {
               "success": true,
               "data": {
                   "contract_id": 1,
                   "filename": "lease.pdf",
                   "all_clauses": [...],
                   "risky_clauses": [...],
                   "missing_clauses": [...],
                   "risk_summary": {...},
                   "legal_references": [...]
               },
               "error": null
           }
       """
   ```
   - Call `assemble_contract_report(contract_id, db)`
   - Return standard envelope with `report.model_dump()`
   - Catch `ValueError` and return 404 with error message
   - Catch other exceptions and return 500

2. **GET /api/contracts/{contract_id}/report/pdf**
   ```python
   @router.get("/{contract_id}/report/pdf")
   async def get_contract_report_pdf(
       contract_id: int,
       db: AsyncSession = Depends(get_db)
   ) -> StreamingResponse:
       """
       Download contract report as PDF.
       
       Returns:
           PDF file with Content-Disposition attachment header
       """
   ```
   - Call `assemble_contract_report(contract_id, db)`
   - Call `generate_pdf_report(report)` to get PDF bytes
   - Create filename: `{sanitized_contract_filename}_report.pdf`
   - Return `StreamingResponse` with:
     - `content=BytesIO(pdf_bytes)`
     - `media_type="application/pdf"`
     - `headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}`
   - Catch `ValueError` and return 404
   - Catch other exceptions and return 500

**Path parameter types:**
- Both endpoints use `contract_id: int` (INTEGER, matching Stage 7/8 convention)

**Verification:**
- Router is created with `/api/contracts` prefix
- Both endpoints declared with correct signatures
- `contract_id` typed as `int` in both
- PDF endpoint returns `StreamingResponse` with attachment header

---

## Task 6: Write Report Assembly Unit Tests

**File:** `backend/tests/test_reports.py`

**Test cases to implement (TC-1 through TC-6 from spec):**

1. **TC-1: Complete Data Assembly**
   - Mock a contract with 10 clauses, 3 risky findings, 2 missing findings
   - Mock cached explanations and citations in risk_findings rows
   - Call `assemble_contract_report(1, mock_db)`
   - Assert:
     - `contract_id == 1`
     - `len(all_clauses) == 10`
     - `len(risky_clauses) == 3`
     - `len(missing_clauses) == 2`
     - `risk_summary.total_clauses == 10`
     - `risk_summary.risky_clauses_count == 3`
     - `risk_summary.missing_clauses_count == 2`
     - Risky clauses ordered by severity (high first)
     - Missing clauses ordered by severity

2. **TC-2: Missing Explanations Handled Gracefully**
   - Mock risk findings where some have `explanation=None`
   - Mock `generate_all_explanations()` to simulate filling in missing values
   - Call `assemble_contract_report(1, mock_db)`
   - Assert `generate_all_explanations` was called
   - Assert report still assembles successfully

3. **TC-3: No Risks Found**
   - Mock contract with 5 clauses, 0 risk findings
   - Call `assemble_contract_report(1, mock_db)`
   - Assert:
     - `len(risky_clauses) == 0`
     - `len(missing_clauses) == 0`
     - `risk_summary.overall_risk_level == "none"`
     - `len(legal_references) == 0`

4. **TC-4: Contract Not Found**
   - Mock database to return None for contract query
   - Call `assemble_contract_report(999, mock_db)`
   - Assert raises `ValueError` with message "Contract not found"

5. **TC-5: Processing Incomplete**
   - Mock contract with `processing_status = 'processing'`
   - Call `assemble_contract_report(1, mock_db)`
   - Assert raises `ValueError` with message containing "not complete"

6. **TC-6: Legal Reference Deduplication**
   - Mock 5 risk findings referencing 3 unique citations (2 findings share citation A, 2 share citation B, 1 uses citation C)
   - Call `assemble_contract_report(1, mock_db)`
   - Assert:
     - `len(legal_references) == 3`
     - Citations ordered by usage_count desc (A and B both have count=2, C has count=1)
     - Usage counts correct: A=2, B=2, C=1

**Test structure:**
- Use `pytest.mark.asyncio` for async tests
- Mock database session using `AsyncMock`
- Mock database queries using `MagicMock` with `.scalars().all()` pattern (same pattern as Stage 8 tests)
- Patch `generate_all_explanations` using `unittest.mock.patch`

**Verification:**
- All 6 test cases implemented
- Tests run with: `pytest backend/tests/test_reports.py -v`
- All tests pass (use mocks, no real database)

---

## Task 7: Write Report API Endpoint Tests

**File:** `backend/tests/test_api_reports.py`

**Test cases to implement (TC-7 through TC-10 from spec):**

1. **TC-7: JSON Endpoint Success**
   - Call `GET /api/contracts/1/report` with mocked `assemble_contract_report`
   - Assert:
     - Status code 200
     - Response structure matches envelope: `{"success": true, "data": {...}, "error": null}`
     - `data.contract_id == 1`
     - `data.risk_summary` exists
     - `data.all_clauses` is a list

2. **TC-8: JSON Endpoint 404 - Contract Not Found**
   - Mock `assemble_contract_report` to raise `ValueError("Contract not found")`
   - Call `GET /api/contracts/999/report`
   - Assert:
     - Status code 404
     - Response contains error detail

3. **TC-9: PDF Endpoint Success**
   - Call `GET /api/contracts/1/report/pdf` with mocked functions
   - Assert:
     - Status code 200
     - `Content-Type: application/pdf`
     - `Content-Disposition` header contains `attachment; filename=`
     - Filename includes contract name and `_report.pdf` suffix
     - Response body is non-empty bytes

4. **TC-10: PDF Content Validation**
   - Call `GET /api/contracts/1/report/pdf`
   - Extract PDF text content (can use PyMuPDF/fitz or basic byte check)
   - Assert:
     - PDF bytes start with `%PDF` magic number
     - Response size > 1KB (indicates real PDF, not error message)

**Test approach options:**
- **Option A (Full mocks):** Mock both `assemble_contract_report` and `generate_pdf_report`
- **Option B (Real contract test):** Use a test database with a real contract, let functions execute normally

**Recommended:** Option A (full mocks) for unit testing speed and reliability

**Test structure:**
- Use `pytest.mark.asyncio` for async tests
- Use FastAPI `TestClient` or `httpx.AsyncClient` for API testing
- Mock `get_db` dependency to return mock session
- Patch `assemble_contract_report` and `generate_pdf_report` as needed

**Verification:**
- All 4 test cases implemented
- Tests run with: `pytest backend/tests/test_api_reports.py -v`
- All tests pass

---

## Summary

**7 Tasks total:**
1. Create module structure (4 files)
2. Implement Pydantic models (6 models)
3. Implement report assembly logic (1 async function)
4. Verify/install weasyprint + implement PDF generator (1 function)
5. Implement API endpoints (2 routes)
6. Write report assembly unit tests (6 test cases)
7. Write API endpoint tests (4 test cases)

**Key technical constraints:**
- All `contract_id` and `clause_id` must be `int` (INTEGER, not UUID)
- Use Stage 8's cached `explanation` and `formatted_citation` from `risk_findings` table
- Call `generate_all_explanations()` first to ensure cache populated
- weasyprint must be installed before implementing PDF generation
- Follow FastAPI standard envelope: `{"success": bool, "data": {...}, "error": str|null}`
- Use async/await throughout (database operations are async)

**Dependencies across tasks:**
- Task 2 must complete before Task 3 (models needed for assembler)
- Task 3 must complete before Task 4b (assembler needed for PDF generator)
- Task 4a must complete before Task 4b (weasyprint must be installed)
- Tasks 2-5 must complete before Tasks 6-7 (tests need implementation)

**Files created:**
- `backend/app/reports/__init__.py`
- `backend/app/reports/models.py`
- `backend/app/reports/assembler.py`
- `backend/app/reports/pdf_generator.py`
- `backend/app/api/routes/reports.py`
- `backend/tests/test_reports.py`
- `backend/tests/test_api_reports.py`

**Files modified:**
- `backend/requirements.txt` (add weasyprint)
