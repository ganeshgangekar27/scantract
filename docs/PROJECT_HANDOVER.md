# ScanTract Project Handover

**Generated:** 2026-10-08  
**Target:** New assistant taking over the project  
**Source:** Verified commands run in session (no speculation)

---

## 1. REPOSITORY STATUS

### Git State
```
Current branch: main
Ahead of origin/main by: 9 commits
Remote: https://github.com/ganeshgangekar27/scantract.git
Branches: feature/stage2-document-processing, main
```

### Recent Commits (Last 15)
```
f9ec3d4 (HEAD -> main) feat(backend): sample contracts (is_sample) with read-only sharing
bf0ae9f chore(backend): live upload proof script
230afc0 feat(frontend): auth screens (login, signup, forgot, reset)
75d906a feat(frontend): design system, api/auth layer, routing, app shell
ddf5c98 fix(backend): live auth verified end to end
3947800 chore(backend): clean docker image, live auth proof scripts
8f33d0e fix(backend): ownership on classify, no 404->500 swallowing, auth + isolation tests
93c77e1 feat(backend): user auth, per-user isolation, password reset
3d42420 feat(backend): friendly, redacted failure messages
aa2fcc7 (origin/main) fix(backend): readable citation labels for reference examples
799af61 feat(backend): derive report citation label from the traced reference
d689f52 chore: script to complete a failed contract's explanation stage
21227fc chore: script to repair stored explanations
5757070 test: completion-integrity tests against real orchestrator with teardown
69211e8 fix(backend): completion integrity tests against real orchestrator
```

### Uncommitted Changes
- Modified: .kiro/hooks/test-on-save-backend.json, HANDOVER.md, backend/scripts/auth_live_check.py
- Untracked scripts in backend/scripts/ (dev/debug artifacts, not production code)

---

## 2. PROJECT LAYOUT

### Backend Structure (`backend/app/`)
```
api/routes/        auth.py, contracts.py, explanations.py, pipeline.py, reports.py
auth/              dependencies.py, jwt.py, password.py
db/                database.py, models.py
document_processing/ extractor.py, normalizer.py, orchestrator.py, processor.py, segmenter.py, utils.py
llm/               classify_clauses.py, detect_risk.py, generate_explanations.py, llm_client.py, models.py
llm/providers/     claude.py, gemini.py, openai.py
rag/               merge_context.py, models.py, prompt_builder.py
reports/           assembler.py, models.py, pdf_generator.py
utils/             error_handling.py
main.py            FastAPI app entry point
```

### Database Migrations (`backend/alembic/versions/`)
```
001_create_contracts_and_clauses.py
002_add_classification_fields.py
003_create_legal_rules_kb.py
004_create_reference_clauses.py
005_create_risk_findings.py
006_add_explanation_caching.py
007_add_document_processing_fields.py
008_add_pipeline_stage_tracking.py
009_add_user_auth.py
010_add_sample_contracts_flag.py
3b2943032b28_drop_ivfflat_index_change_to_3072_.py
c9f165806a4d_alter_embedding_dimensions_to_768.py
```

### Tests (`backend/tests/`)
```
Total: 280 tests collected
Files: test_*.py across auth, api, pipeline, orchestration
Result: 272 passed, 1 failed, 6 errors, 209 warnings
```

### Frontend Structure (`frontend/src/`)
```
auth/              AuthContext.tsx, ProtectedRoute.tsx
components/        AppShell, ContractUpload, ExplanationPanel, MissingClausesPanel, RiskSummaryHeader
components/ui/     Badge, Button, Card, EmptyState, ErrorState, Input, Logo, Modal, etc.
hooks/             useContractList, useLocalStorage, useReportData
lib/               api.ts, constants.ts, utils.ts
pages/             DashboardPage, UploadPage, ContractsPage, ReportView, SettingsPage
pages/auth/        LoginPage, SignupPage, ForgotPasswordPage, ResetPasswordPage
test/              setup.ts
App.tsx, main.tsx, style.css
```

### Docker Services
```
Service: db
  Image: ankane/pgvector:latest
  Ports: 5432:5432
  Healthcheck: pg_isready -U postgres (10s interval, 5s timeout, 5 retries)

Service: backend
  Image: Built from ./backend/Dockerfile (python:3.11-slim)
  Ports: 8000:8000
  Depends: db (healthy)

Service: frontend  
  Image: Built from ./frontend/Dockerfile (node:20-alpine + nginx:alpine)
  Ports: 3000:80
```

---

## 3. API ROUTES

### Backend Routes (FastAPI)
```
/api/auth
  POST   /register                  (no auth) -> RegisterResponse
  POST   /login                     (no auth) -> LoginResponse
  GET    /me                        (auth required) -> UserResponse
  POST   /forgot-password           (no auth) -> ForgotPasswordResponse
  POST   /reset-password            (no auth) -> success/error

/api/contracts
  POST   /upload                    (auth required) -> UploadResponse
  GET    /list                      (auth required) -> List[ContractListItem]
  GET    /{contract_id}/explanations (auth required, owner or sample) -> explanations
  POST   /{contract_id}/explanations/regenerate (auth required, owner only)
  POST   /{contract_id}/classify    (auth required, owner only) -> PipelineStatusResponse
  POST   /{contract_id}/detect-risks (auth required, owner only) -> PipelineStatusResponse
  POST   /{contract_id}/generate-explanations (auth required, owner only) -> PipelineStatusResponse
  GET    /{contract_id}/report      (auth required, owner or sample) -> report JSON
  GET    /{contract_id}/report/pdf  (auth required, owner or sample) -> PDF download
```

**Auth Pattern:** All routes except auth endpoints use `Depends(get_current_user)`
- Files using auth: auth.py, contracts.py, explanations.py, pipeline.py, reports.py

### Frontend Routes (React Router)
```
PUBLIC (redirect to /dashboard if logged in):
  /login              -> LoginPage
  /signup             -> SignupPage
  /forgot-password    -> ForgotPasswordPage
  /reset-password     -> ResetPasswordPage

PROTECTED (redirect to /login if not logged in):
  /dashboard          -> DashboardPage
  /upload             -> UploadPage
  /contracts          -> ContractsPage
  /contracts/:id      -> ReportView
  /settings           -> SettingsPage
  
  / redirects to /dashboard or /login based on auth state
```


---

## 4. DATABASE STATE

### Current Alembic Version
```
009 (add_user_auth)
```

**Note:** Migration 010 (add_sample_contracts_flag) exists but NOT yet applied to production DB (scantract). It has been applied to scantract_test only.

### Table Schemas

**users** (6 columns)
```
id            integer (PK)
email         character varying (unique)
full_name     character varying
password_hash character varying
created_at    timestamp with time zone
is_active     boolean
```

**password_reset_tokens** (6 columns)
```
id         integer (PK)
user_id    integer (FK to users, CASCADE)
token_hash character varying
expires_at timestamp with time zone
used_at    timestamp with time zone
created_at timestamp with time zone
```

**contracts** (12 columns)
```
id                integer (PK)
contract_type     character varying
filename          character varying
uploaded_at       timestamp with time zone
file_path         character varying
full_text         text
processing_status character varying
error_message     text
page_count        integer
pipeline_stage    character varying (indexed)
failed_stage      character varying
user_id           integer (FK to users, CASCADE, nullable)
```

**clauses** (10 columns)
```
id                   integer (PK)
contract_id          integer (FK to contracts)
clause_id            character varying
position             integer
text                 text
clause_type          character varying
key_entities         jsonb
confidence           double precision
classification_error text
classified_at        timestamp with time zone
```

**risk_findings** (8 columns - schema not fully retrieved in this session)
```
id          integer (PK)
contract_id integer (FK to contracts)
clause_id   (FK to clauses)
finding_type, severity, explanation, formatted_citation, legal_rule_id, etc.
```

**legal_rules** (pgvector KB - exact schema not retrieved)
**reference_clauses** (pgvector corpus - exact schema not retrieved)

### Row Counts (Production DB: scantract)
```
users:                  5
password_reset_tokens:  0
contracts:             18
clauses:              177
risk_findings:        132
legal_rules:           20
reference_clauses:     28
```

### Contract Status
```
ID  | pipeline_stage | is_legacy (user_id IS NULL)
----|----------------|---------------------------
1   | completed      | true
3   | failed         | true
44  | completed      | true
46  | completed      | true
47  | completed      | true
53  | completed      | true
54  | failed         | false (has user_id)
55  | completed      | false
56  | completed      | false
57  | completed      | false
(18 total, 10 failed, 8 completed)
```

**Legacy contracts:** IDs 1, 44, 46, 47 are completed and could be flagged `is_sample=true` after migration 010.

### Data Integrity Baseline
```
Contract 1 risk_findings MD5: 6adf9b01e1a4557703c818e5d5cf3b75 (known-good)
```

---

## 5. TESTS

### Backend Tests
```
Command: python -m pytest tests --ignore=tests/integration -q
Result: 272 passed, 1 failed, 6 errors, 209 warnings (26.63s)
Total collected: 280 tests
```

**CRITICAL:** NEVER run bare `pytest` or `tests/integration` - they perform real uploads and spend LLM API quota.

### Frontend Tests
```
Status: NOT VERIFIED (npm commands not run in this session)
```

### Frontend Build
```
Status: NOT VERIFIED (npm commands not run in this session)
```

---

## 6. ENVIRONMENT & SECRETS

### Required Environment Variables
```
DATABASE_URL              (required) - PostgreSQL connection string
OPENAI_API_KEY           (required if LLM_PROVIDER=openai)
CLAUDE_API_KEY           (required if LLM_PROVIDER=claude)
GEMINI_API_KEY           (required) - used for embeddings regardless of LLM_PROVIDER
LLM_PROVIDER             (required) - one of: openai, claude, gemini
JWT_SECRET               (required) - at least 32 characters
```

### Optional Configuration
```
CLAUDE_MODEL, GEMINI_MODEL, OPENAI_MODEL
EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
UPLOAD_TEMP_DIR, MAX_UPLOAD_SIZE_MB
MAX_CONTEXT_TOKENS, DEDUPLICATION_THRESHOLD, MIN_CHUNKS_PER_SOURCE
LLM_CONCURRENCY_LIMIT, LLM_MAX_RETRIES, LLM_TIMEOUT_SECONDS
LOG_LEVEL
RESET_LINK_MODE          (demo or email)
```

### API Key Change Procedure
1. Check no contracts are processing: `SELECT COUNT(*) FROM contracts WHERE pipeline_stage NOT IN ('completed', 'failed');` must be 0
2. Edit `backend/.env` by hand (never commit secrets!)
3. Run: `docker compose up -d --force-recreate backend`
4. Container restart marks running contracts as failed

### Current Quota Status
```
Free tier: used=87, limit=50, remaining=0
Status: QUOTA EXCEEDED (no more free calls until daily reset)
```

**Verification:** `docker exec scantract-backend python /app/scripts/check_key.py 2>&1 | Select-String free_model_daily_requests`

### JWT Configuration
```
Algorithm: HS256
Expiry: 24 hours
Secret source: JWT_SECRET environment variable
```


---

## 7. HOW TO RUN

### Start Services
```bash
docker compose up -d
```

### View Logs
```bash
docker logs scantract-backend
docker logs scantract-frontend  
docker logs scantract-db
```

### Run Backend Tests
```bash
cd backend
python -m pytest tests --ignore=tests/integration
```

**NEVER** run `tests/integration` or bare `pytest` - they perform real uploads and spend LLM quota.

### Frontend Development
```bash
cd frontend
npm run dev         # NOT VERIFIED in this session
npm run test        # NOT VERIFIED
npm run build       # NOT VERIFIED
```

### Helper Scripts (Committed in `backend/scripts/`)
```
auth_diag.py                  - Diagnose auth issues
auth_live_check.py            - Live auth endpoint verification (POST-only, no LLM)
check_content_loss_v2.py      - Verify no content loss during processing
check_key.py                  - Check API key quota and validity
cleanup_test_contracts.py     - Delete test contracts from DB
complete_contract.py          - Manually complete a failed contract's stage
db_hashes.sh                  - Generate baseline hashes for DB integrity
encoding_check.py             - Verify file encoding (UTF-8 required)
env_check.py                  - Print env var lengths (not values)
live_upload_check.py          - End-to-end upload proof (spends ~19 LLM calls)
prove_invariant_red.py        - Test data integrity invariants
regenerate_missing_explanations.py - Regenerate missing explanations for a contract
repair_explanations.py        - Repair malformed explanations
run_parser_on_real.py         - Test clause parser on real contracts
scan_secrets.py               - Scan for accidentally committed secrets
```

### Windows Quirks
1. **Docker Desktop must be running** - check with `docker info`
2. **PDF generation works only in Docker** - weasyprint needs GTK libraries (not available on Windows host)
3. **No multi-line python -c** - PowerShell breaks on newlines, use script files instead
4. **No > redirects to create files** - causes UTF-16 corruption, use `Out-File -Encoding UTF8` or write script files
5. **Use .sql files for DB queries** - `docker cp file.sql container:/tmp/ ; docker exec container psql -f /tmp/file.sql`

---

## 8. AUTH & API CONTRACT

### Auth Endpoints

**POST /api/auth/register**
```
Request:  { email: EmailStr, password: str (min 8), full_name: str }
Response: { access_token: str, token_type: "bearer", user: {...} }
Errors:   409 "An account with this email already exists"
```

**POST /api/auth/login**
```
Request:  { email: EmailStr, password: str }
Response: { access_token: str, token_type: "bearer" }
Errors:   401 "No account found with this email"
          401 "Incorrect password"
```

**GET /api/auth/me**
```
Headers:  Authorization: Bearer <token>
Response: { id: int, email: str, full_name: str, created_at: datetime, is_active: bool }
Errors:   401 if no token or invalid token
```

**POST /api/auth/forgot-password**
```
Request:  { email: EmailStr }
Response: { message: str, demo_reset_link?: str }
Errors:   (Returns 200 even for non-existent emails to prevent enumeration)
```

**POST /api/auth/reset-password**
```
Request:  { token: str, new_password: str (min 8) }
Response: { message: str }
Errors:   400 "Invalid or expired reset token"
          400 "Reset token has already been used"
          404 "User not found"
```

### Contract Endpoints

**GET /api/contracts/list**
```
Headers:  Authorization: Bearer <token>
Response: [ { contract_id: int, filename: str, uploaded_at: datetime, 
              processing_status: str, pipeline_stage: str, failed_stage?: str,
              error_message?: str, is_sample: bool }, ... ]
Notes:    Returns user's own contracts + all sample contracts (is_sample=true)
```

**GET /api/contracts/{id}/report**
```
Headers:  Authorization: Bearer <token>
Response: { 
  success: true,
  data: {
    contract_id: int,
    filename: str,
    all_clauses: [ { id, text, type, ... }, ... ],
    risky_clauses: [ { clause_id, severity, explanation, citation, ... }, ... ],
    missing_clauses: [ { severity, explanation, citation, ... }, ... ],
    risk_summary: { overall_risk_level, high_severity_count, medium_severity_count, 
                    low_severity_count, risky_clauses_count, missing_clauses_count, 
                    total_clauses },
    legal_references: [...]
  },
  error: null
}
Errors:   404 if contract not found or not owned (unless is_sample)
          409 if processing incomplete
```

**POST /api/contracts/upload**
```
Headers:  Authorization: Bearer <token>
Body:     multipart/form-data with field "file" (PDF or DOCX, max 15MB)
Response: { contract_id: int, filename: str, size: int, upload_timestamp: datetime, status: "uploaded" }
Errors:   400 if invalid file type or size exceeds limit
```

### JWT Details
```
Algorithm: HS256
Expiry:    24 hours
Secret:    JWT_SECRET env var (min 32 chars)
```

---

## 9. KNOWN ISSUES & UNVERIFIED

### Test Failures (Backend)
```
Result: 1 failed, 272 passed, 6 errors
Details: NOT EXAMINED in this session (would require reading pytest output)
```

### Unverified Items
1. **Frontend tests/build** - npm commands not run (would spend time)
2. **Migration 010 on production** - created and tested on scantract_test, NOT applied to production scantract DB
3. **Sample contract flagging** - contracts 1, 44, 46, 47 are candidates for `is_sample=true` after migration 010
4. **Full test failure details** - 1 failed + 6 errors not diagnosed
5. **Database table schemas** - risk_findings, legal_rules, reference_clauses schemas partially missing (pgvector columns)
6. **Helper script purposes** - some scripts listed but internal logic not verified

### Warnings
1. **LLM quota exhausted** - remaining=0, used=87/50 (exceeded daily free tier limit)
2. **9 commits ahead of origin** - need git push to sync
3. **Stale HANDOVER.md** - in repo root, superseded by this file

### Production Readiness Checklist
- [ ] Apply migration 010 to production DB
- [ ] Flag demo contracts (1, 44, 46, 47) as `is_sample=true`
- [ ] Push 9 commits to origin
- [ ] Investigate 1 failed + 6 error tests
- [ ] Verify frontend build passes
- [ ] Replace expired/invalid API key (quota exceeded)
- [ ] Delete or commit untracked scripts in backend/scripts/

---

**END OF HANDOVER**
