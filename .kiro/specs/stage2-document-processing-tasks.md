# Stage 2: Document Processing Pipeline - Tasks

**Spec:** Document extraction, normalization, and clause segmentation for uploaded contracts  
**Dependencies:** Stage 1 frontend complete, backend database schema exists  
**Status:** Ready to execute

---

## Task 1: Verify PyMuPDF and python-docx Installation

**Goal:** Confirm PyMuPDF (fitz) and python-docx are actually installed and importable before proceeding.

**Files to verify:**
- `backend/requirements.txt` (already lists PyMuPDF>=1.23.0 and python-docx>=1.0.0)

**Actions:**
1. Run: `pip show PyMuPDF python-docx` from `backend/` directory
2. Show real output confirming both are installed with version numbers
3. Test imports:
   ```python
   import fitz  # PyMuPDF
   import docx  # python-docx
   print(f"PyMuPDF version: {fitz.__version__}")
   print(f"python-docx installed successfully")
   ```
4. Show real output confirming both import without errors
5. If either is missing, run: `pip install -r requirements.txt` and re-verify

**Acceptance Criteria:**
- `pip show` confirms both packages installed
- Both imports succeed without ImportError
- PyMuPDF version displayed (1.23.0+)

---

## Task 2: Extend contracts Table Schema (Alembic Migration)

**Goal:** Add document processing fields to existing contracts table.

**Current Contract Model Fields (confirmed via models.py inspection):**
- `id` (Integer, primary key)
- `contract_type` (String(50))
- `filename` (String(255))
- `uploaded_at` (DateTime)

**New Fields to Add:**
- `file_path` (String(512), nullable) - Local storage path for uploaded file
- `full_text` (Text, nullable) - Extracted full contract text
- `processing_status` (String(20), default='uploaded') - Status: uploaded/processing/completed/failed
- `error_message` (Text, nullable) - Processing error details if status=failed
- `page_count` (Integer, nullable) - Number of pages extracted (PDF only)

**File to create:**
- `backend/alembic/versions/007_add_document_processing_fields.py`

**Actions:**
1. Check latest migration in `backend/alembic/versions/` - should be `006_add_explanation_caching.py`
2. Create migration `007_add_document_processing_fields.py`:
   ```python
   """Add document processing fields to contracts table
   
   Revision ID: 007
   Revises: 006
   Create Date: 2026-08-15
   """
   from alembic import op
   import sqlalchemy as sa
   
   revision = '007'
   down_revision = '006'
   branch_labels = None
   depends_on = None
   
   def upgrade():
       op.add_column('contracts', sa.Column('file_path', sa.String(512), nullable=True))
       op.add_column('contracts', sa.Column('full_text', sa.Text(), nullable=True))
       op.add_column('contracts', sa.Column('processing_status', sa.String(20), nullable=False, server_default='uploaded'))
       op.add_column('contracts', sa.Column('error_message', sa.Text(), nullable=True))
       op.add_column('contracts', sa.Column('page_count', sa.Integer(), nullable=True))
   
   def downgrade():
       op.drop_column('contracts', 'page_count')
       op.drop_column('contracts', 'error_message')
       op.drop_column('contracts', 'processing_status')
       op.drop_column('contracts', 'full_text')
       op.drop_column('contracts', 'file_path')
   ```
3. Run: `alembic upgrade head` from `backend/` directory
4. Verify migration applied successfully

**Acceptance Criteria:**
- Migration file created at correct path
- `alembic upgrade head` runs without errors
- New columns exist in contracts table (verify via psql or pgAdmin)

---

## Task 3: Create document_processing Module Structure

**Goal:** Set up module structure for extraction, normalization, and segmentation.

**Files to create:**
- `backend/app/document_processing/__init__.py`
- `backend/app/document_processing/extractor.py`
- `backend/app/document_processing/normalizer.py`
- `backend/app/document_processing/segmenter.py`
- `backend/app/document_processing/utils.py`

**Actions:**
1. Create directory: `backend/app/document_processing/`
2. Create empty `__init__.py` (module marker)
3. Create stub files for extractor.py, normalizer.py, segmenter.py, utils.py
4. Add docstrings explaining each module's purpose

**`__init__.py` content:**
```python
"""
Document processing pipeline for contract extraction and segmentation.
"""
from .extractor import extract_text_from_pdf, extract_text_from_docx
from .normalizer import clean_and_normalize
from .segmenter import segment_clauses

__all__ = [
    'extract_text_from_pdf',
    'extract_text_from_docx',
    'clean_and_normalize',
    'segment_clauses',
]
```

**Acceptance Criteria:**
- All 5 files exist in `backend/app/document_processing/`
- Module imports without errors: `from app.document_processing import extract_text_from_pdf`

---

## Task 4: Implement Text Extraction (extractor.py)

**Goal:** Extract text from PDF and DOCX files using PyMuPDF and python-docx.

**File:** `backend/app/document_processing/extractor.py`

**Functions to implement:**

1. **`extract_text_from_pdf(file_path: str) -> tuple[str, int]`**
   - Use PyMuPDF (fitz) to open PDF
   - Extract text from each page with `page.get_text()`
   - Concatenate pages with page breaks (e.g., `\n\n--- PAGE {i} ---\n\n`)
   - Return: (full_text, page_count)
   - Handle errors: FileNotFoundError, corrupted PDFs

2. **`extract_text_from_docx(file_path: str) -> tuple[str, int]`**
   - Use python-docx to open DOCX
   - Extract text from each paragraph: `doc.paragraphs`
   - Preserve paragraph structure with double newlines
   - Count paragraphs as "pages" (for consistency)
   - Return: (full_text, paragraph_count)
   - Handle errors: FileNotFoundError, corrupted DOCX

**Error handling:**
- Raise descriptive exceptions for file not found, permission denied, corrupted files
- Log extraction start/end with file path and text length

**Acceptance Criteria:**
- Both functions implemented with type hints and docstrings
- Handle common file errors gracefully
- Return consistent tuple format: (text, count)

---

## Task 5: Implement Text Normalization (normalizer.py)

**Goal:** Clean and normalize extracted text while preserving legal wording exactly.

**File:** `backend/app/document_processing/normalizer.py`

**Function to implement:**

**`clean_and_normalize(text: str) -> str`**

**Normalization steps:**
1. Fix hyphenation breaks: `prop-\nerty` → `property`
2. Collapse multiple whitespace/newlines: `\n\n\n` → `\n\n`
3. Strip obvious headers/footers:
   - Remove page numbers (e.g., `Page 1 of 10`, `- 3 -`)
   - Remove date/time stamps in headers
4. Remove leading/trailing whitespace
5. Preserve:
   - Legal wording exactly (no rephrasing)
   - Clause numbering (1., 1.1, (a), (i))
   - Special characters ($, %, legal symbols)

**Regex patterns to use:**
```python
# Fix hyphenation: word-\n → word
text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)

# Collapse whitespace
text = re.sub(r'\n{3,}', '\n\n', text)
text = re.sub(r'[ \t]+', ' ', text)

# Strip page numbers (basic patterns)
text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
text = re.sub(r'- \d+ -', '', text)
```

**Acceptance Criteria:**
- Function implemented with type hints and docstring
- Hyphenation fixed correctly
- Whitespace collapsed without losing structure
- Legal text preserved exactly

---

## Task 6: Implement Clause Segmentation (segmenter.py)

**Goal:** Segment normalized text into individual clauses with numbering and position.

**File:** `backend/app/document_processing/segmenter.py`

**Function to implement:**

**`segment_clauses(text: str) -> list[dict]`**

**Returns:** List of clause dictionaries:
```python
[
    {
        'clause_number': '1',
        'clause_text': 'The Tenant agrees to...',
        'position': 0
    },
    {
        'clause_number': '1.1',
        'clause_text': 'Payment is due on...',
        'position': 1
    },
    ...
]
```

**Segmentation logic:**

1. **Detect numbered clause patterns** (regex):
   - `1.` `2.` `3.` (top-level)
   - `1.1` `1.2` (nested)
   - `(a)` `(b)` `(i)` `(ii)` (lettered/roman)
   - Pattern: `r'^(\d+\.|\d+\.\d+|\([a-z]\)|\([ivxIVX]+\))\s+'`

2. **Split on detected patterns:**
   - If patterns found: split text into clauses based on numbering
   - Each clause includes its number + text until next number

3. **Fallback: paragraph-based segmentation:**
   - If no numbering detected: split on double newlines `\n\n`
   - Assign sequential numbers: `P1`, `P2`, `P3`, etc.

4. **Assign position:** Sequential integer (0, 1, 2, ...)

**Edge cases to handle:**
- No clause numbering → fallback to paragraphs
- Mixed numbering styles → detect most common pattern
- Empty clauses → filter out (< 20 characters)

**Acceptance Criteria:**
- Function returns list of clause dicts with required fields
- Numbered clauses detected correctly
- Paragraph fallback works when no numbering exists
- Empty clauses filtered out

---

## Task 7: Implement Upload Endpoint (contracts.py)

**Goal:** Create POST /api/contracts/upload endpoint accepting multipart file uploads.

**File to create:** `backend/app/api/routes/contracts.py`

**Endpoint specification:**

```python
@router.post("/upload", response_model=UploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> UploadResponse:
    """
    Upload a contract file (PDF or DOCX) for processing.
    
    - Validates file type (.pdf, .docx only)
    - Validates file size (max 15MB)
    - Saves to local temp/uploads directory
    - Creates Contract DB entry with status='uploaded'
    - Kicks off background extraction task
    - Returns contract_id (int), filename, size, upload_timestamp immediately
    """
```

**Response model (matches Stage 1 frontend):**
```python
class UploadResponse(BaseModel):
    contract_id: int  # INTEGER, not UUID
    filename: str
    size: int  # bytes
    upload_timestamp: datetime
    status: str  # 'uploaded'
```

**Validation:**
- File type: `.pdf` or `.docx` only (check `file.filename.endswith()`)
- File size: max 15MB (15 * 1024 * 1024 bytes)
- Raise HTTPException(400) for invalid files

**Upload flow:**
1. Validate file type and size
2. Generate unique filename: `{timestamp}_{uuid}_{original_name}`
3. Save to: `backend/uploads/{unique_filename}`
4. Create Contract row:
   - `filename`: original filename
   - `file_path`: relative path to saved file
   - `uploaded_at`: current UTC timestamp
   - `processing_status`: 'uploaded'
5. Commit to DB
6. Add background task: `background_tasks.add_task(process_contract, contract.id, file_path, db_session)`
7. Return UploadResponse immediately (don't wait for processing)

**File to also create:** `backend/app/api/routes/__init__.py` (if doesn't exist)

**Acceptance Criteria:**
- Endpoint accepts multipart/form-data
- Validates file type and size correctly
- Saves file to local uploads/ directory
- Creates Contract row with status='uploaded'
- Returns contract_id as int (not string/UUID)
- Background task queued but not awaited

---

## Task 8: Implement Background Processing Function

**Goal:** Extract, normalize, segment contract in background after upload response sent.

**File:** `backend/app/document_processing/processor.py` (new file)

**Function to implement:**

```python
async def process_contract(
    contract_id: int,
    file_path: str,
    db_session: AsyncSession
) -> None:
    """
    Background task to process uploaded contract.
    
    Steps:
    1. Determine file type (.pdf or .docx)
    2. Extract text (extractor.py)
    3. Normalize text (normalizer.py)
    4. Segment into clauses (segmenter.py)
    5. Insert Clause rows linked to contract_id
    6. Update Contract:
       - full_text = normalized_text
       - page_count = extracted_page_count
       - processing_status = 'completed' or 'failed'
       - error_message if failed
    7. Clean up temp file (optional: keep for debugging)
    """
```

**Error handling:**
- Wrap entire function in try/except
- On error:
  - Update processing_status='failed'
  - Set error_message with exception details
  - Log error with contract_id and file_path
- Always commit DB changes even on failure

**Clause insertion:**
```python
for clause_dict in clauses:
    clause = Clause(
        contract_id=contract_id,
        clause_id=clause_dict['clause_number'],
        position=clause_dict['position'],
        text=clause_dict['clause_text']
    )
    db_session.add(clause)
```

**Acceptance Criteria:**
- Function processes PDF and DOCX correctly
- Creates Clause rows for all segmented clauses
- Updates Contract with full_text and status
- Handles errors gracefully (sets status='failed')
- Logs processing start/end with contract_id

---

## Task 9: Register Contracts Router in main.py

**Goal:** Mount contracts router in FastAPI app alongside existing routers.

**File to modify:** `backend/app/main.py`

**Actions:**
1. Import contracts router: `from app.api.routes import contracts`
2. Add router with prefix: `app.include_router(contracts.router, prefix="/api/contracts", tags=["contracts"])`
3. Verify existing routers still mounted: reports, explanations

**Current main.py routers (confirmed this session):**
- `/api/contracts/{id}/report` (reports router)
- `/api/explanations/generate` (explanations router)

**Expected final routes:**
- POST `/api/contracts/upload` (new)
- GET `/api/contracts/{id}/report` (existing)
- POST `/api/explanations/generate` (existing)

**Acceptance Criteria:**
- Contracts router imported and mounted
- App starts without errors: `uvicorn app.main:app --reload`
- Routes visible in OpenAPI docs: http://localhost:8000/docs
- Existing routes still functional

---

## Task 10: OPTIONAL - PaddleOCR Integration for Scanned PDFs

**Goal:** Attempt PaddleOCR installation and integration for image-only PDF pages (OCR).

**⚠️ STRETCH SCOPE - Skip if installation fails on Windows**

**Files to modify:**
- `backend/app/document_processing/extractor.py` (add OCR fallback)

**Installation attempt:**
1. Check if already installed: `pip show paddleocr paddlepaddle`
2. If not, attempt: `pip install paddleocr paddlepaddle`
3. Test import: `from paddleocr import PaddleOCR`
4. **If installation fails or errors occur:**
   - Document failure in code comment
   - Skip OCR integration entirely
   - Return early from this task with status: "OCR unsupported on Windows"

**OCR integration (only if installation succeeds):**

```python
def extract_text_from_pdf_with_ocr(file_path: str) -> tuple[str, int]:
    """
    Extract text from PDF with OCR fallback for scanned pages.
    
    Logic:
    1. Extract text normally with PyMuPDF
    2. For each page with < 50 characters extracted:
       - Render page as image
       - Run PaddleOCR on image
       - Append OCR text
    3. Return combined text + page_count
    """
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='en')
    except ImportError:
        # OCR not available, fall back to regular extraction
        return extract_text_from_pdf(file_path)
    
    # ... OCR logic for pages with minimal text
```

**Acceptance Criteria (if attempted):**
- Installation succeeds OR clearly documented as unsupported
- If working: OCR fallback activates for pages with < 50 chars
- If failed: extraction still works without OCR (graceful degradation)

**Decision point:** If paddlepaddle fails to install (native dependency issues), stop here and note in comments that OCR requires Linux/Docker environment.

---

## Task 11: Write Document Processing Tests

**Goal:** Test extraction, normalization, segmentation with synthetic fixtures.

**File to create:** `backend/tests/test_document_processing.py`

**Test fixtures to create programmatically:**

1. **Minimal PDF fixture:**
   ```python
   def create_test_pdf(text: str, output_path: str) -> None:
       """Create minimal PDF with reportlab or PyMuPDF."""
       import fitz
       doc = fitz.open()
       page = doc.new_page()
       page.insert_text((72, 72), text)
       doc.save(output_path)
       doc.close()
   ```

2. **Minimal DOCX fixture:**
   ```python
   def create_test_docx(paragraphs: list[str], output_path: str) -> None:
       """Create minimal DOCX with python-docx."""
       from docx import Document
       doc = Document()
       for para in paragraphs:
           doc.add_paragraph(para)
       doc.save(output_path)
   ```

**Tests to write:**

1. **test_extract_pdf_text** - Create test PDF, extract, verify text and page_count
2. **test_extract_docx_text** - Create test DOCX, extract, verify text and para_count
3. **test_normalize_hyphenation** - Input: `"prop-\nerty"`, expect: `"property"`
4. **test_normalize_whitespace** - Input: `"a\n\n\nb"`, expect: `"a\n\nb"`
5. **test_segment_numbered_clauses** - Input text with `1.` `2.` numbering, verify clause_number extracted
6. **test_segment_paragraph_fallback** - Input text without numbering, verify `P1` `P2` assigned
7. **test_segment_filters_empty_clauses** - Input with short clauses (< 20 chars), verify filtered

**Mock database usage:**
- Use pytest fixtures for async DB session mocking
- Don't require real PostgreSQL for these unit tests

**Acceptance Criteria:**
- All 7+ tests pass
- Test fixtures created programmatically (no external files needed)
- Tests run with: `pytest backend/tests/test_document_processing.py -v`

---

## Task 12: Write Upload Endpoint Tests

**Goal:** Test upload endpoint validation and background task queueing.

**File to create:** `backend/tests/test_upload_endpoint.py`

**Tests to write:**

1. **test_upload_valid_pdf** - Upload valid PDF, verify 200 response, contract_id is int
2. **test_upload_valid_docx** - Upload valid DOCX, verify 200 response
3. **test_upload_invalid_file_type** - Upload .txt file, verify 400 error
4. **test_upload_oversized_file** - Upload 20MB file, verify 400 error
5. **test_upload_creates_contract_row** - Verify Contract row created with correct fields
6. **test_upload_queues_background_task** - Mock BackgroundTasks, verify task added (not awaited)
7. **test_response_format** - Verify response matches UploadResponse schema (contract_id as int)

**Test setup:**
```python
@pytest.fixture
def test_pdf_file():
    """Create minimal test PDF in memory."""
    content = b"%PDF-1.4\n..."  # Minimal valid PDF bytes
    return UploadFile(filename="test.pdf", file=BytesIO(content))

@pytest.fixture
def test_client(db_session):
    """FastAPI test client with mocked DB."""
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client
```

**Mock background tasks:**
```python
@pytest.fixture
def mock_background_tasks(monkeypatch):
    tasks = []
    def mock_add_task(func, *args, **kwargs):
        tasks.append((func, args, kwargs))
    
    monkeypatch.setattr(BackgroundTasks, 'add_task', mock_add_task)
    return tasks
```

**Acceptance Criteria:**
- All 7 tests pass
- Tests use mocked DB and background tasks
- Tests run with: `pytest backend/tests/test_upload_endpoint.py -v`
- Response contract_id verified as int type

---

## Summary

**Total Tasks:** 12 (10 required + 1 optional OCR + 1 test suite)

**Critical Requirements:**
- ✅ contract_id as INTEGER throughout (matches Stage 1 frontend)
- ✅ Use existing get_db() dependency from backend/app/db/database.py
- ✅ Extend existing Contract model with new fields (migration 007)
- ✅ Prioritize PyMuPDF + python-docx (core deliverable)
- ⚠️ PaddleOCR optional/stretch (skip if Windows installation issues)

**Expected Deliverables:**
1. Working POST /api/contracts/upload endpoint
2. Background processing pipeline (extract → normalize → segment)
3. Clause rows inserted into database
4. Contract status tracking (uploaded → processing → completed/failed)
5. Full test coverage (unit + integration)

**Post-completion verification:**
1. Upload a real PDF via Stage 1 frontend
2. Verify contract_id returned as int
3. Check database: Contract row + Clause rows created
4. Verify processing_status = 'completed'
5. Confirm full_text stored correctly

**Next Stage Dependencies:**
- Stage 3 (Prompt Templating) will read full_text from Contract rows
- Stage 4 (Clause Classification) will process Clause rows created here
- Stage 5 (RAG Retrieval) will use clause_text for embeddings
