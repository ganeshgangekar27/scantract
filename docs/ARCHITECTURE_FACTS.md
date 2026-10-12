# ScanTract Architecture Facts

**Generated:** 2026-10-07  
**Source:** Code inspection and runtime queries  
**Purpose:** Verified architectural documentation extracted from implementation

---

## Part 1: Infrastructure and Backend

### 1. Docker Compose Services

**File:** `docker-compose.yml`

**Services:**
- `db` (container: scantract-db)
  - Image: ankane/pgvector:latest
  - Ports: 5432:5432
  - Volumes: postgres_data:/var/lib/postgresql/data
  - Depends on: none
  - Healthcheck: pg_isready -U postgres (10s interval, 5s timeout, 5 retries)

- `backend` (container: scantract-backend)
  - Build: ./backend/Dockerfile
  - Ports: 8000:8000
  - Volumes: ./uploads:/app/uploads
  - Depends on: db (condition: service_healthy)
  - Command: runs migrations (alembic upgrade head), seeds legal KB and reference corpus, starts uvicorn

- `frontend` (container: scantract-frontend)
  - Build: ./frontend/Dockerfile
  - Ports: 3000:80
  - Depends on: backend

**Volume:** postgres_data (persistent PostgreSQL data)

---

### 2. Frontend Container

**File:** `frontend/Dockerfile`

**Build stage:**
- Base image: node:20-alpine
- Workdir: /app
- Install: npm ci (from package.json/package-lock.json)
- Build: npm run build (outputs to /app/dist)
- Note: Removes .env.production to prevent absolute API URL from being baked in

**Runtime stage:**
- Base image: nginx:alpine
- Serves: /usr/share/nginx/html (built React app from /app/dist)
- Config: nginx.conf → /etc/nginx/conf.d/default.conf
- Expose: 80
- Command: nginx -g "daemon off;"

**File:** `frontend/nginx.conf` (lines 1-25)

```
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing - serve index.html for all non-file requests
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for long-running LLM requests
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
        proxy_send_timeout 120s;
    }
}
```

**What is served:** Static React build (HTML, JS, CSS)  
**What /api proxies to:** http://backend:8000 (FastAPI backend container)

---

### 3. Backend Container

**File:** `backend/Dockerfile`

**Base image:** python:3.11-slim

**System dependencies installed:**
- GTK for weasyprint PDF generation: libpango-1.0-0, libpangocairo-1.0-0, libgdk-pixbuf-2.0-0, libffi-dev, shared-mime-info
- PaddleOCR: libgomp1, libglib2.0-0, libsm6, libxext6, libxrender1

**Workdir:** /app

**Python dependencies:** requirements.txt (pip install --no-cache-dir)

**Environment:** PYTHONPATH=/app (allows seed scripts to import db, app, rag modules)

**Expose:** 8000

**Default command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000`

**Overridden by docker-compose.yml (lines 88-97):**
```
command: >
  sh -c "
    echo 'Running database migrations...' &&
    alembic upgrade head &&
    echo 'Seeding legal knowledge base...' &&
    python db/legal_kb/seed_legal_kb.py &&
    echo 'Seeding reference corpus...' &&
    python db/reference_corpus/seed_reference_corpus.py &&
    echo 'Starting FastAPI server...' &&
    uvicorn app.main:app --host 0.0.0.0 --port 8000
  "
```

**Startup sequence:**
1. Alembic migrations (alembic upgrade head)
2. Legal KB seed (python db/legal_kb/seed_legal_kb.py)
3. Reference corpus seed (python db/reference_corpus/seed_reference_corpus.py)
4. Uvicorn start (app.main:app on 0.0.0.0:8000)

---

### 4. Backend Main Application

**File:** `backend/app/main.py` (lines 1-118)

**Framework:** FastAPI (title: "ScanTract API", version: "1.0.0")

**Docs:** /docs (Swagger), /redoc (ReDoc)

**Lifespan handler (lines 30-73):**
- Startup: Validates JWT_SECRET, marks interrupted contracts (classifying, detecting_risks, generating_explanations stages) as failed
- Shutdown: Logs shutdown message

**CORS middleware (lines 90-97):**
- allow_origins: ["http://localhost:5173", "http://localhost:3000"]
- allow_credentials: True
- allow_methods: ["*"]
- allow_headers: ["*"]

**Routers included (lines 99-103):**
1. auth_router (no prefix, tags not shown)
2. reports_router (no prefix, tags not shown)
3. explanations_router (no prefix, tags not shown)
4. contracts_router (prefix: /api/contracts, tags: ["contracts"])
5. pipeline_router (no prefix, tags not shown)

**Root endpoints:**
- GET / → {"message": "ScanTract API", "version": "1.0.0", "status": "running"}
- GET /health → {"status": "healthy"}

---

### 5. API Routes

**All routes extracted from backend/app/api/routes/*.py**

**Auth routes (auth.py):**
- POST /register → RegisterResponse (201, no auth)
- POST /login → LoginResponse (no auth)
- GET /me → UserResponse (auth: get_current_user)
- POST /forgot-password → ForgotPasswordResponse (no auth)
- POST /reset-password → success response (no auth)
- DELETE /me/data → deletion count (auth: get_current_user)

**Contract routes (contracts.py, prefix: /api/contracts):**
- POST /api/contracts/upload → UploadResponse (auth: get_current_user)
- GET /api/contracts/list → List[ContractListItem] (auth: get_current_user)
- GET /api/contracts/stats → StatsResponse (auth: get_current_user)
- DELETE /api/contracts/{contract_id} → success (auth: get_current_user)
- POST /api/contracts/{contract_id}/retry → 202 response (auth: get_current_user)

**Pipeline routes (pipeline.py):**
- POST /{contract_id}/classify → PipelineStatusResponse (auth not verified)
- POST /{contract_id}/detect-risks → PipelineStatusResponse (auth not verified)
- POST /{contract_id}/generate-explanations → PipelineStatusResponse (auth not verified)

**Explanation routes (explanations.py):**
- GET /{contract_id}/explanations → explanations list (auth not verified)
- POST /{contract_id}/explanations/regenerate → success (auth not verified)

**Report routes (reports.py):**
- GET /{contract_id}/report → Report JSON (auth not verified)
- GET /{contract_id}/report/pdf → PDF file (auth not verified)

**Auth requirement summary:**
- Auth required (get_current_user dependency): /api/contracts/* (all 5 routes), GET /me, DELETE /me/data
- No auth required: /register, /login, /forgot-password, /reset-password, pipeline/explanation/report routes (NOT VERIFIED for all)
- Retry route exists: POST /api/contracts/{contract_id}/retry (contracts.py line 331)
- Delete user data route exists: DELETE /me/data (auth.py line 375)

---

### 6. Document Processing Pipeline

**File:** `backend/app/document_processing/processor.py` (lines 21-138)

**Entry point:** `process_contract(contract_id: int, file_path: str, db: AsyncSession)`

**Called from:** `backend/app/api/routes/contracts.py` line 166:
```python
background_tasks.add_task(process_contract, contract.id, file_path, db)
```

**Pipeline execution:** Background task (FastAPI BackgroundTasks), NOT awaited in upload request

**Processor stages (lines 55-133):**
1. Set processing_status = 'processing' (line 99)
2. Extract text (PDF via PyMuPDF or DOCX via python-docx)
3. Normalize text (clean_and_normalize)
4. Segment clauses (segment_clauses)
5. Insert Clause rows
6. Update contract: full_text, page_count, pipeline_stage = 'segmented', processing_status = 'processing'
7. Call run_full_pipeline(contract_id, db) (line 128)

**File:** `backend/app/document_processing/orchestrator.py` (lines 1-290)

**Function:** `run_full_pipeline(contract_id: int, db: AsyncSession)` (lines 20-86)

**Orchestrator stages (in order):**
1. **Stage 4: Classification** (classifying → classified)
   - Function: `_run_classification_stage` (lines 89-139)
   - Calls: `classify_all_clauses(contract_id, contract_type, db)`
   - Updates: contract.pipeline_stage = 'classifying' (line 106), then 'classified' (line 133)
   - On error: pipeline_stage = 'failed', failed_stage = 'classifying' (lines 135-139)

2. **Stage 7: Risk Detection** (detecting_risks → risks_detected)
   - Function: `_run_risk_detection_stage` (lines 142-180)
   - Calls: `detect_risks(contract_id, db)`
   - Updates: contract.pipeline_stage = 'detecting_risks' (line 159), then 'risks_detected' (line 176)
   - On error: pipeline_stage = 'failed', failed_stage = 'detecting_risks' (lines 178-180)

3. **Stage 8: Explanation Generation** (generating_explanations → explanations_generated)
   - Function: `_run_explanation_stage` (lines 183-252)
   - Calls: `generate_all_explanations(contract_id, db)`
   - Validates: all findings have valid explanations
   - Updates: contract.pipeline_stage = 'generating_explanations' (line 200), then 'explanations_generated' (line 239)
   - On error: pipeline_stage = 'failed', failed_stage = 'generating_explanations' (lines 242-252)

4. **Completion** (orchestrator.py lines 59-66)
   - Sets: pipeline_stage = 'completed', processing_status = 'completed'
   - Clears: failed_stage = None, error_message = None

**Top-level exception handler (orchestrator.py lines 68-86):**
- Sets: pipeline_stage = 'failed', processing_status = 'failed' (line 75)
- Sets: error_message = friendly_error(e) if not already set

**Evidence that pipeline runs as background task:**
- processor.py line 166: `background_tasks.add_task(process_contract, ...)`
- No `await` before background_tasks.add_task
- processor.py creates new AsyncSessionLocal() for background context (line 57)
- Upload endpoint returns UploadResponse immediately (contracts.py lines 160-167)

CHECKPOINT: part 1 written

---

## Part 2: External Services, Database, Auth, and Frontend

### 7. External API Calls

**LLM completions (classification, risk detection, explanation generation):**

**Provider abstraction:** `backend/app/llm/llm_client.py`
- Env var: LLM_PROVIDER (choices: "openai", "claude", "gemini")
- Routes to: `backend/app/llm/providers/openai.py`, `claude.py`, or `gemini.py`

**OpenAI provider (`backend/app/llm/providers/openai.py` lines 36-102):**
- Used for: OpenRouter or OpenAI API calls
- Env vars: OPENAI_API_KEY, OPENAI_MODEL, LLM_BASE_URL (optional, for OpenRouter)
- Library: `openai` package (OpenAI SDK)
- Purpose: Classification, risk detection, explanation generation (LLM completions)
- Base URL: LLM_BASE_URL if set (e.g. https://openrouter.ai/api/v1), else OpenAI default

**Claude provider (`backend/app/llm/providers/claude.py`):**
- Used for: Anthropic Claude API calls
- Env vars: CLAUDE_API_KEY, CLAUDE_MODEL
- Purpose: LLM completions (alternative to OpenAI/OpenRouter)

**Gemini provider (`backend/app/llm/providers/gemini.py`):**
- Used for: Google Gemini API calls
- Env vars: GEMINI_API_KEY, GEMINI_MODEL
- Purpose: LLM completions (alternative to OpenAI/OpenRouter/Claude)

**Gemini embeddings (REQUIRED regardless of LLM_PROVIDER):**

**File:** `backend/rag/embeddings.py` (lines 22-77)
- Function: `get_gemini_client()` → genai.Client singleton
- Function: `embed_text(text: str)` → list[float]
- Env vars: GEMINI_API_KEY (required), EMBEDDING_MODEL (default: models/gemini-embedding-001)
- Library: `google-genai` SDK (genai.Client)
- API call: `client.models.embed_content(model="gemini-embedding-001", contents=text)` (line 74)
- Purpose: Generate embeddings for RAG similarity search in legal_rules and reference_clauses tables
- Used by: `backend/db/legal_kb/search.py`, `backend/db/reference_corpus/search.py`

**Summary:**
- **OpenRouter/OpenAI/Claude/Gemini:** LLM completions (classification, risk detection, explanations) via llm_client.py
- **Gemini embeddings:** Required for all RAG searches (legal KB and reference corpus) via rag/embeddings.py

---

### 8. Database

**Connection:** PostgreSQL 15+ with pgvector extension (Docker image: ankane/pgvector:latest)

**Database query results:**

```
docker exec scantract-db psql -U postgres -d scantract -f /tmp/list_tables.sql

                 List of relations
 Schema |         Name          | Type  |  Owner   
--------+-----------------------+-------+----------
 public | alembic_version       | table | postgres
 public | clauses               | table | postgres
 public | contracts             | table | postgres
 public | legal_rules           | table | postgres
 public | password_reset_tokens | table | postgres
 public | reference_clauses     | table | postgres
 public | risk_findings         | table | postgres
 public | users                 | table | postgres
(8 rows)
```

**pgvector tables and dimensions:**

```
    table_name     | column_name |  data_type   
-------------------+-------------+--------------
 legal_rules       | embedding   | USER-DEFINED
 reference_clauses | embedding   | USER-DEFINED
(2 rows)

 atttypmod 
-----------
      3072
(1 row)
```

**Vector dimension:** 3072 (from pg_attribute.atttypmod for legal_rules.embedding)

**Alembic head revision:**

```
SELECT version_num FROM alembic_version;
 version_num 
-------------
 010
(1 row)
```

**Migration files (backend/alembic/versions/):**
- 001_create_contracts_and_clauses.py
- 002_add_classification_fields.py
- 003_create_legal_rules_kb.py
- 004_create_reference_clauses.py
- 005_create_risk_findings.py
- 006_add_explanation_caching.py
- 007_add_document_processing_fields.py
- 008_add_pipeline_stage_tracking.py
- 009_add_user_auth.py
- 3b2943032b28_drop_ivfflat_index_change_to_3072_.py
- c9f165806a4d_alter_embedding_dimensions_to_768.py

**Current head:** 010 (possibly file 009 or later migration, filename not explicitly shown in list)

---

### 9. Authentication

**JWT tokens:**

**File:** `backend/app/auth/jwt.py` (lines 1-90)

**Library:** PyJWT (`import jwt`)

**Algorithm:** HS256

**Env vars:**
- JWT_SECRET (required, min 32 chars in production)
- ENV (defaults to "production", "test" bypasses secret validation)

**Expiry:** 24 hours (JWT_EXPIRY_HOURS = 24, line 16)

**Token creation (lines 42-59):**
- Function: `create_access_token(user_id: int, email: str) -> str`
- Payload: {"sub": str(user_id), "email": email, "exp": utcnow + 24h, "iat": utcnow}
- Encoding: jwt.encode(payload, JWT_SECRET, algorithm="HS256")

**Token validation (lines 62-77):**
- Function: `decode_access_token(token: str) -> Optional[Dict]`
- Returns payload if valid, None if invalid/expired

**Password hashing:**

**File:** `backend/app/auth/password.py` (lines 1-74)

**Library:** hashlib.scrypt (Python stdlib, no external dependency)

**Algorithm:** scrypt (N=16384, r=8, p=1, dklen=32)

**Salt:** 16 random bytes (secrets.token_bytes(16))

**Storage format:** "salt:hash" (both hex-encoded)

**Functions:**
- `hash_password(password: str) -> str` (lines 12-37)
- `verify_password(password: str, stored_hash: str) -> bool` (lines 40-74, uses hmac.compare_digest for constant-time comparison)

**Password reset flow:**

**Files involved:**
- `backend/app/api/routes/auth.py`:
  - POST /forgot-password (lines 233-296): Generates reset token, stores in password_reset_tokens table
  - POST /reset-password (lines 299-373): Validates token, updates user password
- `backend/app/db/models.py`: PasswordResetToken model (token, user_id, expires_at, used)

**Token generation:** secrets.token_urlsafe(32) (line 261 of auth.py)

**Token expiry:** 1 hour (timedelta(hours=1), line 264)

**One-time use:** Token marked as used=True after successful reset (line 358)

---

### 10. Report Generation

**Report assembly:**

**File:** `backend/app/reports/assembler.py` (lines 1-60+)

**Function:** `assemble_contract_report(contract_id: int, db: AsyncSession) -> ContractReport`

**Steps:**
1. Fetch Contract by ID
2. Verify pipeline_stage == 'completed' (raises ValueError if not)
3. Fetch all Clause rows for contract
4. Fetch all RiskFinding rows for contract
5. Assemble ClauseWithRisk, RiskyClauseReport, MissingClauseReport, RiskSummary
6. Return ContractReport with all data

**Models:** `backend/app/reports/models.py` (ContractReport, RiskyClauseReport, MissingClauseReport, RiskSummary, LegalReference)

**PDF generation:**

**File:** `backend/app/reports/pdf_generator.py` (lines 1-20)

**Library:** weasyprint (lines 16-17):
```python
from weasyprint import HTML, CSS
```

**Availability check (lines 15-20):**
```python
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except (OSError, ImportError) as e:
    logger.warning(f"weasyprint not available: {e}")
    WEASYPRINT_AVAILABLE = False
```

**Purpose:** Convert HTML report to PDF

**System dependencies (backend/Dockerfile lines 7-12):**
- libpango-1.0-0
- libpangocairo-1.0-0
- libgdk-pixbuf-2.0-0
- libffi-dev
- shared-mime-info

**Note:** PDF generation is untested on Linux Docker (per Dockerfile comment line 4)

---

### 11. Frontend

**Framework and versions:**

**File:** `frontend/package.json` (lines 1-45)

**Dependencies:**
- react: 19.2.8
- react-dom: 19.2.8
- react-router-dom: 7.18.2
- vite: 8.3.3 (devDependency)
- tailwindcss: 3.4.17 (devDependency)
- framer-motion: 14.0.0
- typescript: 6.0.2 (devDependency)
- vitest: 4.1.11 (devDependency)

**Other UI libraries:**
- lucide-react: 1.52.0 (icons)
- sonner: 2.0.8 (toast notifications)
- clsx: 2.1.1 (className utility)

**Router configuration:**

**File:** `frontend/src/App.tsx` (lines 1-80)

**Routes:**
- / → RootRoute (redirects to /dashboard if authenticated, else LandingPage)
- /login → LoginPage (PublicOnlyRoute)
- /signup → SignupPage (PublicOnlyRoute)
- /forgot-password → ForgotPasswordPage (PublicOnlyRoute)
- /reset-password → ResetPasswordPage (PublicOnlyRoute)
- /privacy → PrivacyPage (public)
- /terms → TermsPage (public)
- /dashboard → DashboardPage (ProtectedRoute)
- /upload → UploadPage (ProtectedRoute)
- /contracts → ContractsPage (ProtectedRoute)
- /contracts/:contractId → ReportView (ProtectedRoute)
- /report/:contractId → Redirect to /contracts/:contractId
- /settings → SettingsPage (ProtectedRoute)
- * → NotFoundPage

**API layer:**

**File:** `frontend/src/lib/api.ts`

**Functions include:**
- register, login, logout, getMe, forgotPassword, resetPassword, deleteMyData (auth)
- uploadContract, getContracts, getContractStats, deleteContract, retryContract (contracts)
- getReport, downloadReportPdf (reports)
- getPipelineStatus (pipeline)

**Auth context:**

**File:** `frontend/src/auth/AuthContext.tsx` (from import in App.tsx line 3)

**Provides:** AuthProvider, useAuth hook

**Protected routes:** `frontend/src/auth/ProtectedRoute.tsx` (ProtectedRoute, PublicOnlyRoute components)

**Polling hook (NOT VERIFIED):**

**Directory:** `frontend/src/hooks` (exists per list_directory output)

**Likely file:** useContractPolling.ts or similar (NOT VERIFIED)

---

## NOT FOUND

The following items could not be fully verified:

1. **Auth requirement for pipeline/explanation/report routes:** Could not verify whether get_current_user dependency is present in pipeline.py, explanations.py, and reports.py route handlers

2. **Frontend polling hook filename:** Directory `frontend/src/hooks` exists but specific polling hook file was not inspected

3. **Alembic migration 010 filename:** Version number 010 returned from alembic_version table but corresponding filename not matched in versions/ directory list

4. **PDF generator complete implementation:** Only read first 60 lines of assembler.py and first 20 lines of pdf_generator.py; full PDF generation logic not verified

5. **Exact LLM provider module usage per stage:** Verified abstraction layer exists (llm_client.py) but did not trace which provider functions are called from classify_clauses.py, detect_risk.py, generate_explanations.py

---

**End of Architecture Facts**
