# Spec: Document Processing Pipeline

## Overview
Build the backend document processing pipeline for ScanTract — Stage 2 of the core pipeline that receives uploaded contracts, extracts text from PDFs and DOCX files, handles OCR for scanned documents, normalizes text, and segments it into individual clauses for downstream analysis.

## Scope
- FastAPI endpoint `POST /api/contracts/upload`
- Background task processing with FastAPI BackgroundTasks
- Text extraction (PyMuPDF for PDF, python-docx for DOCX)
- OCR fallback using PaddleOCR for scanned pages
- Text normalization and cleaning
- Clause segmentation
- PostgreSQL storage with Alembic migrations
- Unit tests with synthetic fixtures

## Requirements

### Functional Requirements

**FR-1: File Upload Endpoint**
- Accept `POST /api/contracts/upload` with multipart/form-data
- Validate file type (.pdf, .docx only)
- Validate file size (max 15MB)
- Store file temporarily in `backend/uploads/temp/`
- Generate unique `contract_id` (UUID)
- Return contract_id immediately (non-blocking)
- Kick off background processing task

**FR-2: Text Extraction - PDF**
- Use PyMuPDF (fitz) to extract text page-by-page
- For each page, count extractable characters
- If page has <50 characters, treat as scanned and route to PaddleOCR
- Preserve page structure (page numbers as metadata, not content)
- Handle password-protected PDFs gracefully (return error)


**FR-3: Text Extraction - DOCX**
- Use python-docx to extract paragraphs
- Preserve structure: distinguish headings from body paragraphs
- Extract paragraph style information (Heading 1, Heading 2, Normal, etc.)
- Maintain paragraph order
- Handle tables gracefully (extract cell text in reading order)

**FR-4: OCR Processing**
- Use PaddleOCR for scanned PDF pages
- Extract text from page images
- Return text in reading order (top-to-bottom, left-to-right)
- Handle multi-column layouts if detected
- Log OCR confidence scores for monitoring (but not contract content)

**FR-5: Text Normalization**
- Fix hyphenation breaks (end-of-line hyphens: "employ-\nment" → "employment")
- Collapse excessive whitespace (multiple spaces/newlines → single)
- Strip common headers/footers (e.g., "Page X of Y", repetitive headers)
- Remove page numbers that aren't part of clause numbering
- Preserve legal wording exactly (do not rephrase or correct spelling)
- Preserve intentional formatting (e.g., numbered lists, bullet points)

**FR-6: Clause Segmentation**
- Detect numbered/lettered clause patterns:
  - "1.", "1.1", "1.1.1" (decimal numbering)
  - "(a)", "(i)", "(ii)" (lettered/roman)
  - "Article 1", "Section 1.1" (labeled sections)
- If no numbering detected, fall back to paragraph-based segmentation
- Each clause must include:
  - Clause number/identifier (or generated ID for paragraphs)
  - Clause text content
  - Position in document (ordinal)
- Preserve parent-child relationships (e.g., 1.1 is child of 1)


**FR-7: Database Storage**
- Store contract metadata in `contracts` table:
  - contract_id, filename, file_size, upload_timestamp, processing_status
- Store extracted clauses in `clauses` table:
  - clause_id, contract_id, clause_number, clause_text, position, parent_clause_id
- Update processing_status: "uploaded" → "processing" → "completed" / "failed"
- Store normalized full text for reference

**FR-8: Error Handling**
- Handle corrupted/unreadable files gracefully
- Handle unsupported PDF features (forms, encryption)
- Set processing_status to "failed" with error message
- Log errors without exposing contract content
- Clean up temporary files on success or failure

### Non-Functional Requirements

**NFR-1: Background Processing**
- Use FastAPI BackgroundTasks for async processing
- Upload endpoint must return in <500ms (before processing starts)
- Processing happens after response sent to client

**NFR-2: Performance**
- Process typical 20-page contracts in <30 seconds
- OCR pages should process in <5 seconds per page
- Database writes should be batched where possible

**NFR-3: Security**
- Temporary files stored with randomized names (prevent enumeration)
- File content never logged in plaintext
- Uploaded files deleted after processing completes
- SQL injection prevented via SQLAlchemy ORM

**NFR-4: Type Safety**
- All functions use type hints (Python 3.11+)
- Pydantic v2 models for request/response
- Async functions where I/O-bound


## Technical Design

### Module Structure

**Location:** `backend/app/document_processing/`

```
backend/app/document_processing/
├── __init__.py
├── extractor.py          # Text extraction (PDF, DOCX)
├── ocr.py                # PaddleOCR wrapper
├── normalizer.py         # Text cleaning and normalization
├── segmenter.py          # Clause segmentation
├── models.py             # Pydantic models
└── utils.py              # File handling, validation
```

### API Endpoint Design

**Endpoint:** `POST /api/contracts/upload`

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (UploadFile)

**Response (Immediate):**
```json
{
  "success": true,
  "data": {
    "contract_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "contract.pdf",
    "size": 1234567,
    "upload_timestamp": "2026-08-06T10:30:00Z",
    "status": "processing"
  },
  "error": null
}
```

**Response (Validation Error):**
```json
{
  "success": false,
  "data": null,
  "error": "Invalid file type. Only PDF and DOCX are supported."
}
```


### Background Task Design

**Choice: FastAPI BackgroundTasks**

**Rationale:**
- **Simpler:** No external dependencies (Redis, Celery, RabbitMQ)
- **Sufficient:** Contracts process in <30s, acceptable for MVP
- **Tradeoff:** Tasks lost if server restarts during processing
- **Future:** Migrate to Celery if we need:
  - Retry logic and task persistence
  - Distributed workers
  - Task prioritization

**Implementation:**
```python
@router.post("/api/contracts/upload")
async def upload_contract(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
) -> dict:
    # Validate file
    # Save to temp storage
    # Create DB record with status="uploaded"
    # Add background task
    background_tasks.add_task(process_contract, contract_id, file_path, db)
    # Return immediately
    return {"success": True, "data": {...}}
```

**Migration Path (documented in design.md):**
If we need robust task queuing later:
1. Add Redis + Celery
2. Replace `background_tasks.add_task()` with `process_contract.delay()`
3. No changes to API contract or database schema


### Text Extraction Design

**PDF Extraction (extractor.py):**
```python
async def extract_text_from_pdf(file_path: str) -> dict[str, Any]:
    """
    Extract text from PDF using PyMuPDF with OCR fallback.
    
    Returns:
        {
            "pages": [{"page_num": 1, "text": "...", "method": "extracted"}],
            "full_text": "concatenated text",
            "page_count": 10
        }
    """
    pages = []
    doc = fitz.open(file_path)
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        
        # If page has minimal extractable text, use OCR
        if len(text.strip()) < 50:
            text = await ocr_page(page)
            method = "ocr"
        else:
            method = "extracted"
        
        pages.append({
            "page_num": page_num,
            "text": text,
            "method": method
        })
    
    doc.close()
    
    full_text = "\n\n".join(p["text"] for p in pages)
    
    return {
        "pages": pages,
        "full_text": full_text,
        "page_count": len(pages)
    }
```

**DOCX Extraction (extractor.py):**
```python
async def extract_text_from_docx(file_path: str) -> dict[str, Any]:
    """
    Extract text from DOCX preserving structure.
    
    Returns:
        {
            "paragraphs": [{"text": "...", "style": "Heading 1"}],
            "full_text": "concatenated text"
        }
    """
    doc = Document(file_path)
    paragraphs = []
    
    for para in doc.paragraphs:
        if para.text.strip():  # Skip empty paragraphs
            paragraphs.append({
                "text": para.text,
                "style": para.style.name
            })
    
    full_text = "\n\n".join(p["text"] for p in paragraphs)
    
    return {
        "paragraphs": paragraphs,
        "full_text": full_text
    }
```


### OCR Design

**OCR Wrapper (ocr.py):**
```python
from paddleocr import PaddleOCR

# Initialize once (lazy-loaded)
_ocr_engine = None

def get_ocr_engine() -> PaddleOCR:
    """Lazy-load OCR engine (large model)."""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            show_log=False
        )
    return _ocr_engine

async def ocr_page(page: fitz.Page) -> str:
    """
    OCR a single PDF page using PaddleOCR.
    
    Args:
        page: PyMuPDF page object
    
    Returns:
        Extracted text in reading order
    """
    # Render page to image
    pix = page.get_pixmap(dpi=300)
    img_bytes = pix.tobytes("png")
    
    # Run OCR
    ocr = get_ocr_engine()
    result = ocr.ocr(img_bytes, cls=True)
    
    # Extract text in reading order (top-to-bottom)
    if not result or not result[0]:
        return ""
    
    text_lines = []
    for line in result[0]:
        text = line[1][0]  # Extract text from result tuple
        text_lines.append(text)
    
    return "\n".join(text_lines)
```


### Text Normalization Design

**Normalizer (normalizer.py):**
```python
import re

def clean_and_normalize(text: str) -> str:
    """
    Normalize extracted text while preserving legal wording.
    
    Steps:
    1. Fix hyphenation breaks (end-of-line)
    2. Remove headers/footers/page numbers
    3. Collapse excessive whitespace
    4. Preserve legal wording exactly
    """
    # Fix hyphenation breaks: "employ-\nment" → "employment"
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    # Remove common header/footer patterns
    # "Page 1 of 10", "Page 1", etc.
    text = re.sub(r'\nPage \d+ of \d+\n', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'\nPage \d+\n', '\n', text, flags=re.IGNORECASE)
    
    # Remove repetitive headers (appears on every page)
    # This is heuristic: if a line appears 3+ times identically, likely a header
    lines = text.split('\n')
    line_counts = {}
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 10 and len(stripped) < 100:  # Reasonable header length
            line_counts[stripped] = line_counts.get(stripped, 0) + 1
    
    repetitive_headers = {line for line, count in line_counts.items() if count >= 3}
    
    filtered_lines = [
        line for line in lines
        if line.strip() not in repetitive_headers
    ]
    text = '\n'.join(filtered_lines)
    
    # Collapse excessive whitespace
    text = re.sub(r' {2,}', ' ', text)  # Multiple spaces → single
    text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines → double
    
    # Trim leading/trailing whitespace
    text = text.strip()
    
    return text
```


### Clause Segmentation Design

**Segmenter (segmenter.py):**
```python
import re
from typing import List
from pydantic import BaseModel

class Clause(BaseModel):
    """Represents a single contract clause."""
    clause_id: str  # e.g., "1.1", "a", or generated UUID for paragraphs
    clause_text: str
    position: int  # Ordinal position in document
    parent_clause_id: str | None = None  # For hierarchical clauses

def segment_clauses(text: str) -> List[Clause]:
    """
    Segment normalized text into clauses.
    
    Strategy:
    1. Try numbered clause patterns (1., 1.1, 1.1.1)
    2. Try lettered patterns ((a), (i), (ii))
    3. Try labeled sections (Article 1, Section 1.1)
    4. Fall back to paragraph segmentation
    """
    # Attempt numbered clause detection
    numbered_clauses = _detect_numbered_clauses(text)
    if numbered_clauses:
        return numbered_clauses
    
    # Attempt lettered clause detection
    lettered_clauses = _detect_lettered_clauses(text)
    if lettered_clauses:
        return lettered_clauses
    
    # Fall back to paragraph-based segmentation
    return _segment_by_paragraphs(text)

def _detect_numbered_clauses(text: str) -> List[Clause] | None:
    """Detect clauses with decimal numbering: 1., 1.1, 1.1.1"""
    # Pattern: start of line, optional whitespace, number(s) with dots
    pattern = r'^(\d+(?:\.\d+)*)\.\s+(.+?)(?=^\d+(?:\.\d+)*\.\s+|\Z)'
    matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
    
    clauses = []
    for i, match in enumerate(matches, start=1):
        clause_id = match.group(1)
        clause_text = match.group(2).strip()
        
        # Determine parent: 1.1.1 -> parent is 1.1
        parent_id = _get_parent_clause_id(clause_id)
        
        clauses.append(Clause(
            clause_id=clause_id,
            clause_text=clause_text,
            position=i,
            parent_clause_id=parent_id
        ))
    
    return clauses if len(clauses) > 2 else None  # Need at least 3 to confirm pattern
```


def _detect_lettered_clauses(text: str) -> List[Clause] | None:
    """Detect lettered clauses: (a), (b), (i), (ii)"""
    # Pattern: (a), (b), (c) or (i), (ii), (iii)
    pattern = r'^\(([a-z]|[ivx]+)\)\s+(.+?)(?=^\([a-z]|[ivx]+\)\s+|\Z)'
    matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
    
    clauses = []
    for i, match in enumerate(matches, start=1):
        clause_id = match.group(1)
        clause_text = match.group(2).strip()
        
        clauses.append(Clause(
            clause_id=f"({clause_id})",
            clause_text=clause_text,
            position=i,
            parent_clause_id=None
        ))
    
    return clauses if len(clauses) > 2 else None

def _segment_by_paragraphs(text: str) -> List[Clause]:
    """Fallback: split by paragraphs (double newline)"""
    paragraphs = re.split(r'\n\n+', text)
    
    clauses = []
    for i, para in enumerate(paragraphs, start=1):
        para = para.strip()
        if para and len(para) > 20:  # Skip very short fragments
            clauses.append(Clause(
                clause_id=f"para_{i}",
                clause_text=para,
                position=i,
                parent_clause_id=None
            ))
    
    return clauses

def _get_parent_clause_id(clause_id: str) -> str | None:
    """Extract parent clause ID: '1.1.1' -> '1.1', '1' -> None"""
    parts = clause_id.split('.')
    if len(parts) > 1:
        return '.'.join(parts[:-1])
    return None
```


### Database Schema Design

**Alembic Migration:** `backend/alembic/versions/001_create_contracts_and_clauses.py`

**Tables:**

```sql
-- contracts table
CREATE TABLE contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    -- Status values: 'uploaded', 'processing', 'completed', 'failed'
    full_text TEXT,  -- Normalized full text for reference
    page_count INTEGER,
    error_message TEXT,  -- Populated if status = 'failed'
    processing_completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_contracts_status ON contracts(processing_status);
CREATE INDEX idx_contracts_upload_timestamp ON contracts(upload_timestamp);

-- clauses table
CREATE TABLE clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    clause_number VARCHAR(50) NOT NULL,  -- e.g., "1.1", "(a)", "para_1"
    clause_text TEXT NOT NULL,
    position INTEGER NOT NULL,  -- Ordinal position in contract
    parent_clause_id UUID REFERENCES clauses(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_clauses_contract_id ON clauses(contract_id);
CREATE INDEX idx_clauses_position ON clauses(contract_id, position);
```


**SQLAlchemy Models (backend/app/db/models.py):**

```python
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base

class Contract(Base):
    __tablename__ = "contracts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    processing_status = Column(String(50), nullable=False, default="uploaded")
    full_text = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clauses = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")

class Clause(Base):
    __tablename__ = "clauses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False)
    clause_number = Column(String(50), nullable=False)
    clause_text = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    parent_clause_id = Column(UUID(as_uuid=True), ForeignKey("clauses.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    contract = relationship("Contract", back_populates="clauses")
    parent_clause = relationship("Clause", remote_side=[id], backref="sub_clauses")
```


### Pydantic Models

**Request/Response Models (backend/app/document_processing/models.py):**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class UploadResponse(BaseModel):
    """Response for contract upload."""
    contract_id: UUID
    filename: str
    size: int
    upload_timestamp: datetime
    status: str = "processing"

class ContractStatus(BaseModel):
    """Contract processing status."""
    contract_id: UUID
    status: str  # uploaded, processing, completed, failed
    error_message: str | None = None
    processing_completed_at: datetime | None = None

class ClauseData(BaseModel):
    """Individual clause data."""
    clause_id: str
    clause_text: str
    position: int
    parent_clause_id: str | None = None

class ProcessingResult(BaseModel):
    """Complete processing result."""
    contract_id: UUID
    full_text: str
    page_count: int
    clauses: list[ClauseData]
```


### Processing Pipeline Flow

**Main Processing Function:**

```python
async def process_contract(
    contract_id: UUID,
    file_path: str,
    db: AsyncSession
) -> None:
    """
    Background task: process uploaded contract.
    
    Steps:
    1. Extract text (PDF or DOCX)
    2. Normalize text
    3. Segment clauses
    4. Store in database
    5. Clean up temp file
    """
    try:
        # Update status to processing
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(processing_status="processing")
        )
        await db.commit()
        
        # Step 1: Extract text based on file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext == ".pdf":
            extraction_result = await extract_text_from_pdf(file_path)
        elif file_ext == ".docx":
            extraction_result = await extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Step 2: Normalize text
        normalized_text = clean_and_normalize(extraction_result["full_text"])
        
        # Step 3: Segment clauses
        clauses = segment_clauses(normalized_text)
        
        # Step 4: Store in database
        await _save_processing_result(
            db, contract_id, normalized_text, clauses,
            extraction_result.get("page_count")
        )
        
        # Mark as completed
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(
                processing_status="completed",
                processing_completed_at=datetime.utcnow()
            )
        )
        await db.commit()
        
    except Exception as e:
        # Mark as failed, log error (but not contract content)
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(
                processing_status="failed",
                error_message=str(e)
            )
        )
        await db.commit()
        logger.error(f"Processing failed for contract {contract_id}: {e}")
    
    finally:
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)
```


## Test Plan

### Test Fixtures

**Location:** `backend/tests/fixtures/`

**1. Text PDF (fixtures/sample_text.pdf):**
- 2-page synthetic contract with clear extractable text
- Contains numbered clauses (1., 1.1, 2., 2.1)
- Example content:
  ```
  RENTAL AGREEMENT
  
  1. Parties
  This agreement is between Landlord and Tenant.
  
  1.1 Landlord Details
  Name: ABC Properties Ltd.
  
  2. Term
  The rental term is 12 months starting January 1, 2026.
  ```

**2. Scanned PDF (fixtures/sample_scanned.pdf):**
- 1-page synthetic contract rendered as image (no extractable text)
- Contains simple text that OCR can handle
- Example: "This is a scanned contract. Section 1: Payment terms."

**3. DOCX (fixtures/sample.docx):**
- Simple contract with headings and paragraphs
- Contains:
  - Heading 1: "Agreement"
  - Normal paragraphs with numbered sections
  - Example structure similar to text PDF

**Fixture Generation Script:** `backend/tests/fixtures/generate_fixtures.py`
- Uses ReportLab to create PDF fixtures
- Uses python-docx to create DOCX fixture
- Creates scanned PDF by rendering text as image


### Test Cases

**Test File:** `backend/tests/test_document_processing.py`

**TC-1: Upload Endpoint - Valid PDF**
- POST valid PDF to `/api/contracts/upload`
- Verify immediate response with contract_id
- Verify status = "processing"
- Verify file saved to temp directory

**TC-2: Upload Endpoint - Invalid File Type**
- POST .txt file
- Verify 400 error with message "Invalid file type..."

**TC-3: Upload Endpoint - File Too Large**
- POST 20MB file
- Verify 400 error with message "File size exceeds 15MB limit"

**TC-4: Text Extraction - PDF with Extractable Text**
- Extract text from `fixtures/sample_text.pdf`
- Verify text extracted correctly
- Verify page_count = 2
- Verify method = "extracted" for both pages

**TC-5: Text Extraction - Scanned PDF**
- Extract text from `fixtures/sample_scanned.pdf`
- Verify OCR triggered (page has <50 extractable chars)
- Verify method = "ocr"
- Verify text extracted (at least partial match)

**TC-6: Text Extraction - DOCX**
- Extract text from `fixtures/sample.docx`
- Verify paragraphs extracted
- Verify heading styles preserved
- Verify full_text concatenated correctly

**TC-7: Text Normalization**
- Input: "employ-\nment" (hyphenation break)
- Output: "employment"
- Input: "Page 1 of 2\nContent\nPage 2 of 2"
- Output: "Content" (headers removed)
- Input: "Word    word" (multiple spaces)
- Output: "Word word" (collapsed)


**TC-8: Clause Segmentation - Numbered Clauses**
- Input: Text with "1. First\n\n1.1 Sub-first\n\n2. Second"
- Output: 3 clauses with correct IDs and parent relationships
- Verify clause "1.1" has parent_clause_id pointing to "1"

**TC-9: Clause Segmentation - Lettered Clauses**
- Input: Text with "(a) First\n\n(b) Second\n\n(c) Third"
- Output: 3 clauses with IDs "(a)", "(b)", "(c)"

**TC-10: Clause Segmentation - Paragraph Fallback**
- Input: Plain text with no numbering, double-newline separated
- Output: Clauses with generated IDs "para_1", "para_2", etc.

**TC-11: Database Storage**
- Process complete contract
- Verify `contracts` table has record with status="completed"
- Verify `clauses` table has all extracted clauses
- Verify full_text stored
- Verify parent-child relationships in clauses

**TC-12: Error Handling - Corrupted PDF**
- Process invalid/corrupted PDF file
- Verify status="failed"
- Verify error_message populated
- Verify temp file cleaned up

**TC-13: Background Task Execution**
- Mock background task
- Verify upload endpoint returns before processing completes
- Verify processing happens asynchronously


## Dependencies

**Python Packages (backend/requirements.txt):**
```
# Web framework
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6  # For file uploads

# Database
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0  # Async PostgreSQL driver
alembic>=1.12.0

# Document processing
PyMuPDF>=1.23.0  # PDF text extraction
python-docx>=1.1.0  # DOCX processing
paddleocr>=2.7.0  # OCR
paddlepaddle>=2.5.0  # PaddleOCR dependency

# Utilities
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.25.0  # For async test client
```

**System Dependencies:**
- PostgreSQL 14+ with pgvector extension
- Python 3.11+
- Sufficient disk space for temp file storage (15MB per upload)


## Files to Create/Modify

### New Files

**Module Structure:**
1. `backend/app/document_processing/__init__.py`
2. `backend/app/document_processing/extractor.py` - PDF/DOCX extraction
3. `backend/app/document_processing/ocr.py` - PaddleOCR wrapper
4. `backend/app/document_processing/normalizer.py` - Text cleaning
5. `backend/app/document_processing/segmenter.py` - Clause segmentation
6. `backend/app/document_processing/models.py` - Pydantic models
7. `backend/app/document_processing/utils.py` - File validation, temp storage

**API:**
8. `backend/app/api/routes/contracts.py` - Upload endpoint

**Database:**
9. `backend/app/db/models.py` - SQLAlchemy models (Contract, Clause)
10. `backend/alembic/versions/001_create_contracts_and_clauses.py` - Migration

**Tests:**
11. `backend/tests/test_document_processing.py` - Unit tests
12. `backend/tests/test_upload_endpoint.py` - API tests
13. `backend/tests/fixtures/generate_fixtures.py` - Fixture generator
14. `backend/tests/fixtures/sample_text.pdf` - Generated fixture
15. `backend/tests/fixtures/sample_scanned.pdf` - Generated fixture
16. `backend/tests/fixtures/sample.docx` - Generated fixture

**Configuration:**
17. `backend/uploads/temp/.gitkeep` - Temp storage directory

### Modified Files
18. `backend/app/main.py` - Register contracts router
19. `backend/requirements.txt` - Add dependencies
20. `backend/.env.example` - Document required env vars


## Environment Variables

**Required (.env):**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/scantract

# File Upload
UPLOAD_TEMP_DIR=./uploads/temp
MAX_UPLOAD_SIZE_MB=15

# OCR
PADDLEOCR_LANG=en
PADDLEOCR_USE_GPU=false  # Set to true if GPU available

# Logging
LOG_LEVEL=INFO
```

## Design Tradeoffs

**Background Task Choice: FastAPI BackgroundTasks vs Celery**

**Chosen: FastAPI BackgroundTasks**

**Pros:**
- Zero external dependencies (no Redis, RabbitMQ)
- Simple implementation, easy to debug
- Sufficient for MVP (contracts process in <30s)
- Lower operational complexity

**Cons:**
- Tasks lost if server restarts during processing
- No built-in retry mechanism
- No task prioritization or rate limiting
- Cannot distribute across multiple workers

**When to migrate to Celery:**
- Processing time exceeds 1 minute regularly
- Need task persistence across restarts
- Need retry logic for transient failures
- Need distributed processing (multiple workers)
- Need task monitoring dashboard

**Migration path:** Replace `background_tasks.add_task()` with `process_contract.delay()`. No changes to API contract or database schema required.


## Security Considerations

**SC-1: File Storage**
- Temp files stored with randomized UUID filenames (prevent enumeration)
- Temp directory not web-accessible
- Files deleted immediately after processing

**SC-2: Content Logging**
- Never log contract text content
- Only log metadata (contract_id, filename, file_size)
- Error messages must not include contract excerpts

**SC-3: SQL Injection**
- All queries through SQLAlchemy ORM (parameterized queries)
- No raw SQL with user input

**SC-4: File Validation**
- Check file extension AND MIME type
- Enforce size limits before processing
- Handle malformed/malicious files gracefully

**SC-5: Resource Limits**
- Limit concurrent processing tasks (prevent DoS)
- Set timeouts on OCR operations (prevent hangs)
- Monitor disk space in temp directory

## Performance Benchmarks

**Target Performance:**
- Upload response time: <500ms (before processing)
- Text PDF (20 pages): <10 seconds processing
- Scanned PDF (20 pages): <2 minutes processing (OCR bottleneck)
- DOCX (20 pages): <5 seconds processing
- Database write: <1 second

**Optimization Opportunities (future):**
- Parallel OCR processing (process multiple pages simultaneously)
- Caching OCR models in memory (avoid reload)
- Batch database inserts for clauses
- Use GPU for PaddleOCR if available


## Out of Scope

**Explicitly NOT included in this spec:**
- Stage 3+ (LLM clause classification, RAG lookup) - separate specs
- Contract versioning or history tracking
- Multi-file batch upload
- Resume/retry for interrupted uploads
- User authentication/authorization
- Rate limiting per user
- Real-time progress updates (WebSocket/SSE)
- Contract comparison or diff functionality
- Export functionality (PDF annotations, etc.)

## Success Criteria

- [ ] `POST /api/contracts/upload` accepts PDF/DOCX, returns contract_id in <500ms
- [ ] Background processing extracts text from PDF using PyMuPDF
- [ ] Scanned PDF pages (<50 chars) trigger PaddleOCR fallback
- [ ] DOCX files extract paragraphs with style preservation
- [ ] Text normalization fixes hyphenation, removes headers/footers
- [ ] Clause segmentation detects numbered patterns (1., 1.1)
- [ ] Clause segmentation falls back to paragraphs if no numbering
- [ ] Contract and clauses stored in PostgreSQL correctly
- [ ] Alembic migration creates tables with proper indexes
- [ ] Parent-child clause relationships preserved
- [ ] Processing status tracked: uploaded → processing → completed/failed
- [ ] Temp files cleaned up after processing
- [ ] All 13 test cases pass
- [ ] No contract content logged in plaintext
- [ ] Error handling covers corrupted/invalid files

## Notes

- This spec covers Stage 2 (Document Processing) of the ScanTract pipeline
- Stage 1 (frontend upload) is in spec `01-contract-upload-page.md`
- Stages 3-9 (LLM analysis, RAG, etc.) will be covered in subsequent specs
- Use Conventional Commits: `feat:` for new features, `test:` for test files

## References

- PyMuPDF docs: https://pymupdf.readthedocs.io/
- python-docx docs: https://python-docx.readthedocs.io/
- PaddleOCR docs: https://github.com/PaddlePaddle/PaddleOCR
- FastAPI BackgroundTasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
