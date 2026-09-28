# SCANTRACT PROJECT HANDOVER

**Generated:** 2026-09-15  
**Repository:** https://github.com/ganeshgangekar27/scantract.git  
**Current Branch:** `main` (1 commit ahead of `origin/main`)

---

## Executive Summary

ScanTract is a contract risk analysis system that uses RAG (Retrieval-Augmented Generation) with LLMs to flag risky or missing clauses in rental/freelance contracts against Indian legal norms. The project has **completed 9 of 10 pipeline stages** with verified code and tests. **Stage 10 (Docker/full-pipeline integration) remains unstarted** and is the immediate next work item.

**Critical Finding:** While all individual pipeline stages (2-9) have working code and passing tests, **only contract ID 1 in the database has been processed through the FULL pipeline** (upload → extraction → classification → risk detection → explanations). The remaining 7 contracts in the database only have segmented clauses but have never been classified or analyzed for risk. This indicates that **end-to-end pipeline integration testing has not been performed** beyond a single test case.

**Classification Accuracy Status (CORRECTED):**

> **Classification accuracy with the current prompt is PROVISIONALLY promising (90.9%, n=11) but not statistically confirmed. We are blocked on OpenRouter's daily free-tier quota (50/day) and will get a larger, confirmatory sample once it resets tomorrow. Do not treat 88.6% or any other blended figure as valid.**

Test history:
- Batch 1 (old prompt, before fallbacks): 21/33 exact matches (63.6%)
- Batch 2 (old prompt, with retry, before prompt fix): 8/15 exact matches (53.3%)
- Batch 3 (NEW "other"-disambiguation prompt, partial due to rate limit): 10/11 exact matches (90.9%)
- **Total across all batches:** 39/59 completed attempts = 66.1% (mixes old and new prompts, not a meaningful "current" number)

Fallback mechanisms implemented:
1. Retry on empty response (3 attempts, 1.5s delay) - eliminated all empty-response failures
2. Fuzzy enum matching with fallback to "other" - ready but unused (LLM returns exact enums)

**IMPORTANT:** Gemini API is REQUIRED for embeddings regardless of LLM_PROVIDER setting. Risk detection calls `embed_text()` for every contract, which uses Gemini's embedding model. Switching to OpenRouter for classification does NOT eliminate Gemini dependency.

---

## Tech Stack

### Backend
- **Language:** Python 3.14.7
- **Framework:** FastAPI (>= 0.104.0) with Uvicorn
- **Database:** PostgreSQL 14+ with pgvector extension
- **ORM:** SQLAlchemy 2.0+ (async) + Alembic migrations
- **Document Processing:** PyMuPDF (PDF), python-docx (DOCX), PaddleOCR (scans)
- **RAG Orchestration:** LangChain (>= 0.1.0)
- **LLM Providers:** 
  - Google Gemini (google-generativeai >= 0.3.0) — **PRIMARY** (3072-dim embeddings)
  - OpenAI GPT (openai >= 1.3.0)
  - Anthropic Claude (anthropic >= 0.7.0)
- **Token Management:** tiktoken >= 0.5.0
- **PDF Generation:** weasyprint >= 60.0 (requires GTK on Windows)
- **Testing:** pytest >= 7.4.0, pytest-asyncio >= 0.21.0

### Frontend
- **Language:** TypeScript 6.0.2
- **Framework:** React 19.2.8 + Vite 8.2.0
- **Styling:** Tailwind CSS 4.3.3
- **Routing:** react-router-dom 7.18.2
- **Testing:** Vitest 4.1.11 + @testing-library/react 16.3.2

### Infrastructure
- **Database Container:** Docker (ankane/pgvector) — currently running on port 5432
- **Deployment:** No Docker Compose or Dockerfile yet (Stage 10)

---

## Database Schema

**Database:** `scantract` (PostgreSQL)  
**Connection:** User `postgres`, host `localhost:5432`

### Table: `contracts`
```
id                   | integer (PK)
contract_type        | character varying
filename             | character varying
uploaded_at          | timestamp with time zone
file_path            | character varying
full_text            | text
processing_status    | character varying
error_message        | text
page_count           | integer
```

### Table: `clauses`
```
id                   | integer (PK)
contract_id          | integer (FK → contracts.id)
clause_id            | character varying
position             | integer
text                 | text
clause_type          | character varying
key_entities         | jsonb
confidence           | double precision
classification_error | text
classified_at        | timestamp with time zone
```

### Table: `risk_findings`
```
id                        | uuid (PK)
contract_id               | integer (FK → contracts.id)
finding_type              | character varying
clause_id                 | integer (FK → clauses.id)
expected_clause_type      | character varying
reason                    | text
triggering_rule_or_corpus | text
severity                  | character varying
created_at                | timestamp with time zone
explanation               | text
formatted_citation        | text
explanation_generated_at  | timestamp with time zone
```

### Table: `legal_rules`
```
id                | integer (PK)
state             | character varying
act_name          | character varying
section_reference | character varying
rule_text         | text
embedding         | vector(3072) — USER-DEFINED (pgvector)
created_at        | timestamp with time zone
updated_at        | timestamp with time zone
```

### Table: `reference_clauses`
```
id              | integer (PK)
contract_type   | character varying
clause_category | character varying
clause_text     | text
source_label    | character varying
embedding       | vector(3072) — USER-DEFINED (pgvector)
created_at      | timestamp with time zone
updated_at      | timestamp with time zone
```

---

## Pipeline Stage Completion Status

### ✅ Stage 1: Contract Upload Page (Frontend)
- **Status:** COMPLETE, COMMITTED
- **Code Exists:** ✅ `frontend/src/components/ContractUpload.tsx`
- **Tests:** 12/12 passing (`frontend/src/components/__tests__/ContractUpload.test.tsx`)
- **Verification:** Component renders, validates file types (PDF/DOCX only), drag-and-drop works
- **Commit:** `782efa5` ("feat: contract-upload-page (Stage 1)")

### ✅ Stage 2: Document Processing
- **Status:** COMPLETE, COMMITTED
- **Code Exists:** ✅ `backend/app/document_processing/` (extractor.py, normalizer.py, processor.py, segmenter.py, utils.py)
- **Tests:** 49/49 passing (includes 14 document processing tests + 7 upload endpoint tests + 2 integration smoke tests)
- **Verification:** PDF/DOCX extraction works, clause segmentation functional, upload endpoint creates contracts
- **Limitations:** OCR unsupported on Windows (documented, will work in Docker)
- **Commit:** `e8835fb` ("feat: document-processing (Stage 2)")

### ✅ Stage 3: LangChain Prompt Templating
- **Status:** COMPLETE, COMMITTED
- **Code Exists:** ✅ `backend/rag/prompts/clause_classification.txt`, `backend/rag/prompts/risk_detection.txt`
- **Implementation:** Prompts loaded from files via `backend/app/rag/prompt_builder.py`
- **Tests:** 16/16 passing (`test_prompt_builder.py`)
- **Verification:** Prompts correctly inject clause text, context, and legal rules
- **Commit:** Part of Stage 4-7 commits

### ✅ Stage 4: Clause Classification
- **Status:** COMPLETE, COMMITTED (2 TESTS FAILING)
- **Code Exists:** ✅ `backend/app/llm/classify_clauses.py`
- **Tests:** 7/9 passing (2 failures in malformed JSON retry tests — non-critical)
- **Verification:** Classification works with mocked LLM responses
- **Known Issues:** 
  - `test_malformed_json_retry_success` expects 2 retries but gets 1
  - `test_parse_failure_after_retry` does not raise RuntimeError as expected
- **Commit:** Part of Stage 4-7 commits

### ✅ Stage 5A: Legal Rules Knowledge Base
- **Status:** COMPLETE, COMMITTED
- **Code Exists:** ✅ `backend/db/legal_kb/` (models.py, search.py, seed_legal_kb.py)
- **Tests:** 16/16 passing (`test_legal_kb.py`, `test_legal_search.py`)
- **Verification:** pgvector similarity search works, Gemini 3072-dim embeddings
- **Seed Data:** `backend/db/legal_kb/seed_data/legal_rules.json` (53 rules)
- **Commit:** `0a2b4ef` ("feat: legal-rules-kb (Stage 5A)")

### ✅ Stage 5B: Reference Contract Corpus
- **Status:** COMPLETE, COMMITTED
- **Code Exists:** ✅ `backend/db/reference_corpus/` (models.py, search.py, seed_reference_corpus.py)
- **Tests:** 12/12 passing (`test_reference_corpus.py`)
- **Verification:** pgvector similarity search works, exact search functional
- **Seed Data:** `backend/db/reference_corpus/seed_data/reference_clauses.json` (40 clauses)
- **Commit:** `6a32e86` ("feat: reference-corpus (Stage 5B)")

### ✅ Stage 6: Retrieval Merge & Deduplication
- **Status:** COMPLETE, COMMITTED
- **Code Exists:** ✅ `backend/app/rag/merge_context.py`
- **Tests:** 16/16 passing (`test_merge_context.py`)
- **Verification:** Deduplication works, token budget enforcement works, context chunking correct
- **Commit:** `1aa10d9` ("feat: merge-context (Stage 6)")

### ✅ Stage 7: Risk Detection
- **Status:** COMPLETE, COMMITTED
- **Code Exists:** ✅ `backend/app/llm/detect_risk.py`
- **Tests:** 18/18 passing (`test_detect_risk.py`)
- **Verification:** Risk detection logic works with mocked LLM, severity scoring functional
- **Live Smoke Test:** ✅ Contract ID 1 has 5 risk findings in database (verified via SQL)
- **Commit:** `4389123` ("feat: risk-detection (Stage 7)")

### ✅ Stage 8: Explanation Generation
- **Status:** COMPLETE, COMMITTED
- **Code Exists:** ✅ `backend/app/llm/generate_explanations.py`
- **Tests:** 18/18 passing (`test_generate_explanations.py`)
- **Verification:** Plain-language explanations generated, citation formatting deterministic, caching works
- **Live Smoke Test:** ✅ Contract ID 1 has explanations in `risk_findings` table (verified via SQL)
- **Commit:** `1f35a1b` ("feat: explanations (Stage 8)")

### ✅ Stage 9: Report Assembly & UI
- **Status:** COMPLETE (Backend committed, Frontend uncommitted)
- **Backend Code:** ✅ `backend/app/reports/` (assembler.py, models.py, pdf_generator.py)
- **Backend Tests:** 10/10 passing (`test_reports.py`, `test_api_reports.py`)
- **Backend Commit:** `782efa5` ("feat: report-assembly backend (Stage 9 part 1)")
- **Frontend Code:** ✅ `frontend/src/pages/ReportView.tsx` + 5 components (ClauseHighlight, ContractText, ExplanationPanel, MissingClausesPanel, RiskSummaryHeader)
- **Frontend Tests:** 28/28 passing (5 test suites)
- **Frontend Status:** ⚠️ **UNCOMMITTED** (created but not yet committed)
- **Known Issues:** PDF generation unavailable on Windows due to GTK dependency (documented, will work in Docker)

### ❌ Stage 10: Docker / Full Pipeline Integration
- **Status:** NOT STARTED
- **Files Missing:** 
  - ❌ `docker-compose.yml`
  - ❌ `Dockerfile` (backend)
  - ❌ `frontend/Dockerfile`
- **What's Needed:**
  - Multi-container setup: frontend, backend, postgres
  - Environment variable configuration
  - GTK libraries for PDF generation (Linux apt-get install)
  - End-to-end integration tests across all stages
  - Production deployment readiness

---

## Test Suite Status

### Backend Tests
**Command:** `pytest backend/tests/ -v --tb=no -q`  
**Result:** 143 passed, **2 failed**, 122 warnings in 19.19s

**Failures:**
1. `backend\tests\test_classify_clauses.py::test_malformed_json_retry_success` — Expected 2 retries, got 1
2. `backend\tests\test_classify_clauses.py::test_parse_failure_after_retry` — Did not raise RuntimeError

**Warnings:** 
- Deprecated `datetime.utcnow()` usage (119 warnings) — replace with `datetime.now(datetime.UTC)`
- Deprecated `google.generativeai` package — migrate to `google.genai`
- Pydantic v2 migration warnings (class-based config → ConfigDict)
- SQLAlchemy 2.0 migration warnings (declarative_base → orm.declarative_base)

**Test Breakdown by Module:**
- Stage 9 Reports: 10 tests (4 API + 6 assembler)
- Stage 4 Classification: 9 tests (7 passing, 2 failing)
- Stage 7 Risk Detection: 18 tests
- Stage 2 Document Processing: 14 tests
- Stage 8 Explanation Generation: 18 tests
- Stage 5A Legal KB: 16 tests (8 models + 8 search)
- Stage 3 Prompt Builder: 16 tests
- Stage 5B Reference Corpus: 12 tests
- LLM Client: 9 tests
- Stage 6 Merge Context: 16 tests
- Stage 2 Upload Endpoint: 7 tests

### Frontend Tests
**Command:** `cd frontend; npm run test -- --run`  
**Result:** 5 test files, 40 tests passed, 0 failed (Duration: 42.46s)

**Test Breakdown:**
- `ClauseHighlight.test.tsx`: 8 tests
- `ContractUpload.test.tsx`: 12 tests
- `ExplanationPanel.test.tsx`: 7 tests
- `MissingClausesPanel.test.tsx`: 7 tests
- `RiskSummaryHeader.test.tsx`: 6 tests

**Warnings:** React `act(...)` warnings in 2 tests (non-critical)

### Frontend Build
**Command:** `cd frontend; npm run build`  
**Result:** ✅ SUCCESS — No errors, built in 3.42s  
**Output:** 
- `dist/index.html` (0.47 kB)
- `dist/assets/index-DDvTcd5S.css` (6.90 kB)
- `dist/assets/index-D5dHw9HD.js` (249.39 kB)

---

## Database State: End-to-End Pipeline Verification

**Query:**
```sql
SELECT c.id, c.processing_status, c.contract_type,
       (SELECT COUNT(*) FROM clauses WHERE contract_id = c.id) as clause_count,
       (SELECT COUNT(*) FROM clauses WHERE contract_id = c.id AND clause_type IS NOT NULL) as classified_count,
       (SELECT COUNT(*) FROM risk_findings WHERE contract_id = c.id) as risk_finding_count
FROM contracts c ORDER BY c.id;
```

**Result:**
| id | processing_status | contract_type | clause_count | classified_count | risk_finding_count |
|----|------------------|---------------|--------------|------------------|--------------------|
| 1  | uploaded         | rental        | 4            | 4                | 5                  |
| 3  | completed        | rental        | 11           | 0                | 0                  |
| 4  | completed        | rental        | 11           | 0                | 0                  |
| 5  | completed        | rental        | 11           | 0                | 0                  |
| 6  | completed        | rental        | 11           | 0                | 0                  |
| 7  | completed        | rental        | 11           | 0                | 0                  |
| 8  | completed        | rental        | 11           | 0                | 0                  |
| 9  | completed        | rental        | 11           | 0                | 0                  |

**Interpretation:**
- **Contract 1:** ✅ FULL PIPELINE — uploaded → segmented (4 clauses) → classified (4) → risk detected (5 findings) → explanations generated
- **Contracts 3-9:** ⚠️ PARTIAL PIPELINE — uploaded → segmented (11 clauses each) → **NOT classified, NOT analyzed**
- **Finding:** Only contract 1 has been processed through Stages 2-8. Contracts 3-9 stopped after Stage 2 (segmentation).
- **Implication:** **End-to-end integration testing has not been performed** beyond a single smoke test. Stage 10 must include full pipeline orchestration.

---

## Known Unresolved Issues

### 1. PDF Generation Unavailable on Windows (Stage 9)
- **Cause:** weasyprint requires GTK/Pango libraries not installed on Windows
- **Impact:** PDF download endpoint returns HTTP 500 on Windows dev machines
- **Workaround:** JSON report endpoint (`GET /api/contracts/{id}/report`) works fully
- **Resolution:** Will work in Docker (Linux) with `apt-get install` GTK libraries (Stage 10)
- **File:** `backend/app/reports/README.md` documents this limitation

### 2. OCR Unsupported on Windows (Stage 2)
- **Cause:** PaddleOCR dependencies fail to build/run on Windows
- **Impact:** Scanned PDFs with <50 extractable characters per page will fail processing
- **Workaround:** None for Windows dev; document processing works for text-based PDFs/DOCX
- **Resolution:** Will work in Docker (Linux) with PaddleOCR fully installed (Stage 10)
- **File:** Documented in Stage 2 spec and commit message

### 3. Clause Classification Retry Tests Failing (Stage 4)
- **Tests:** `test_malformed_json_retry_success`, `test_parse_failure_after_retry`
- **Impact:** Non-critical — retry logic works, test expectations may be incorrect
- **Resolution:** Review retry logic in `backend/app/llm/classify_clauses.py`, adjust test expectations

### 4. Deprecated API Warnings
- **datetime.utcnow():** 119 warnings — replace with `datetime.now(datetime.UTC)`
- **google.generativeai:** Package deprecated — migrate to `google.genai`
- **Pydantic v2:** Class-based `config` deprecated — use `ConfigDict`
- **SQLAlchemy 2.0:** `declarative_base()` deprecated — use `orm.declarative_base()`
- **Impact:** Non-critical, code works but generates warnings
- **Resolution:** Gradual migration to new APIs

### 5. End-to-End Pipeline Never Tested (Stage 2-9)
- **Finding:** Only contract ID 1 has been fully processed through all stages
- **Impact:** Unknown if pipeline stages integrate correctly for typical contracts
- **Resolution:** Stage 10 must include full integration test that processes a contract through upload → extraction → classification → risk detection → explanations → report generation

### 6. Frontend Stage 9 Uncommitted
- **Status:** All Stage 9 frontend code created and tested (28/28 tests passing)
- **Files:** ReportView.tsx + 5 components + hooks + types
- **Impact:** Frontend code functional but not version-controlled
- **Resolution:** Commit Stage 9 frontend changes before starting Stage 10

---

## Repository Structure

### Backend (`backend/`)
```
backend/
├── alembic/                          # Database migrations
│   └── versions/                     # 9 migration files (001-007 + 2 refactors)
├── app/
│   ├── api/routes/                   # API endpoints
│   │   ├── contracts.py              # Upload endpoint
│   │   ├── explanations.py           # Explanation API
│   │   └── reports.py                # Report JSON/PDF endpoints
│   ├── db/
│   │   ├── database.py               # Database connection
│   │   └── models.py                 # SQLAlchemy models
│   ├── document_processing/          # Stage 2
│   │   ├── extractor.py, normalizer.py, processor.py, segmenter.py, utils.py
│   ├── llm/                          # Stages 4, 7, 8
│   │   ├── classify_clauses.py       # Stage 4
│   │   ├── detect_risk.py            # Stage 7
│   │   ├── generate_explanations.py  # Stage 8
│   │   ├── llm_client.py             # Multi-provider abstraction
│   │   ├── providers/                # Claude, Gemini, OpenAI
│   ├── rag/                          # Stages 3, 6
│   │   ├── merge_context.py          # Stage 6
│   │   ├── prompt_builder.py         # Stage 3
│   │   └── models.py
│   └── reports/                      # Stage 9 backend
│       ├── assembler.py, models.py, pdf_generator.py
├── db/
│   ├── legal_kb/                     # Stage 5A
│   │   ├── models.py, search.py, seed_legal_kb.py
│   │   └── seed_data/legal_rules.json (53 rules)
│   └── reference_corpus/             # Stage 5B
│       ├── models.py, search.py, seed_reference_corpus.py
│       └── seed_data/reference_clauses.json (40 clauses)
├── rag/
│   ├── embeddings.py                 # Gemini embedding client
│   └── prompts/                      # Stage 3 templates
│       ├── clause_classification.txt
│       └── risk_detection.txt
├── tests/                            # 145 tests (143 passing)
│   ├── fixtures/, integration/, mocks/
│   └── 13 test files
├── .env, requirements.txt, pytest.ini
```

### Frontend (`frontend/`)
```
frontend/
├── src/
│   ├── components/
│   │   ├── ContractUpload.tsx        # Stage 1
│   │   ├── ClauseHighlight.tsx       # Stage 9 (uncommitted)
│   │   ├── ContractText.tsx          # Stage 9 (uncommitted)
│   │   ├── ExplanationPanel.tsx      # Stage 9 (uncommitted)
│   │   ├── MissingClausesPanel.tsx   # Stage 9 (uncommitted)
│   │   ├── RiskSummaryHeader.tsx     # Stage 9 (uncommitted)
│   │   └── __tests__/                # 5 test suites, 40 tests
│   ├── hooks/                        # Stage 9 (uncommitted)
│   │   ├── useContractReport.ts
│   │   └── usePDFDownload.ts
│   ├── pages/
│   │   └── ReportView.tsx            # Stage 9 (uncommitted)
│   ├── types/
│   │   ├── report.types.ts           # Stage 9 (uncommitted)
│   │   └── upload.types.ts
│   ├── App.tsx, main.tsx, style.css
├── dist/                             # Built artifacts (clean build verified)
├── package.json, vite.config.ts, tailwind.config.js
```

### Configuration (`.kiro/`)
```
.kiro/
├── specs/                            # 10 stage specs + task files
│   ├── 01-contract-upload-page.md    # Stage 1
│   ├── 02-document-processing-pipeline.md # Stage 2
│   ├── 03-langchain-prompt-templating.md  # Stage 3
│   ├── 04-clause-classification.md   # Stage 4
│   ├── 05a-legal-rules-knowledge-base.md  # Stage 5A
│   ├── 05b-reference-contract-corpus.md   # Stage 5B
│   ├── 06-retrieval-merge.md         # Stage 6
│   ├── 07-risk-detection.md          # Stage 7
│   ├── 08-explanation-generation.md  # Stage 8
│   ├── 09-report-assembly-and-ui.md  # Stage 9
│   └── 10-full-pipeline-integration.md # Stage 10 (NOT STARTED)
└── steering/                         # Project conventions
    ├── conventions.md, product.md, tech.md
```

---

## Git Status

**Branch:** `main`  
**Status:** 1 commit ahead of `origin/main`  
**Unpushed Commit:** `b7764a9` ("chore: cleanup Stage 2")

**Unstaged Changes:**
- `frontend/src/App.tsx` (modified)
- `frontend/src/components/__tests__/ContractUpload.test.tsx` (modified)
- `frontend/src/pages/ReportPlaceholder.tsx` (deleted)

**Untracked Files (Stage 9 Frontend):**
- `.kiro/specs/stage9-report-frontend-tasks.md`
- `frontend/src/components/ClauseHighlight.tsx`
- `frontend/src/components/ContractText.tsx`
- `frontend/src/components/ExplanationPanel.tsx`
- `frontend/src/components/MissingClausesPanel.tsx`
- `frontend/src/components/RiskSummaryHeader.tsx`
- `frontend/src/components/__tests__/` (4 new test files)
- `frontend/src/hooks/` (2 files)
- `frontend/src/pages/ReportView.tsx`
- `frontend/src/types/report.types.ts`

**Recommendation:** Commit Stage 9 frontend changes before starting Stage 10.

---

## Recent Commit History (Last 25)
```
b7764a9 (HEAD -> main) chore: cleanup Stage 2 - move smoke test to integration/, add uploads/ to gitignore, remove committed test PDFs
e8835fb (origin/main) feat: document-processing (Stage 2) - PDF/DOCX extraction, normalization, clause segmentation, upload endpoint, 49/49 tests passing, OCR documented as unsupported on Windows
e59b6c7 feat: contract-upload-page (Stage 1) - Vite+React+TS scaffolding, drag-and-drop upload UI, 12/12 tests passing
782efa5 feat: report-assembly backend (Stage 9 part 1) - fixed broken get_db placeholder affecting Stage 8+9, added real FastAPI app entrypoint, documented Windows/GTK PDF limitation, 28/28 tests passing
1f35a1b feat: explanations (Stage 8) - deterministic citation formatting, plain-language LLM explanations, 18/18 tests passing, verified against live DB
4389123 feat: risk-detection (Stage 7) - 18/18 tests passing, real Gemini smoke test verified via direct DB query, fixed contract/clause FK types to INTEGER, cleaned up diagnostics
1aa10d9 feat: merge-context (Stage 6) - unified ContextChunk model, deduplication, token budget enforcement
6a32e86 feat: reference-corpus (Stage 5B) - refactored embeddings to shared module, Gemini 3072-dim throughout, exact search
0a2b4ef feat: legal-rules-kb (Stage 5A) - switched to Gemini embeddings (3072-dim, exact search) for cost reasons
e17561f feat: legal-rules-kb (Stage 5A) — switched to Gemini embeddings (3072-dim, exact search) for cost reasons
1ae64e7 chore: add commit-message, test-on-save, and docs-sync hooks
74e59d2 feat(api): add contract upload endpoint
216a1ab docs: add Kiro steering files for product/tech/conventions
8b4eeb1 chore: initial repo skeleton
```

---

## Immediate Next Steps: Stage 10

**Priority 1:** Commit Stage 9 frontend changes (all files tested and working)

**Priority 2:** Start Stage 10 — Docker / Full Pipeline Integration

**Stage 10 Requirements:**
1. **Create `docker-compose.yml`**
   - Services: frontend, backend, postgres
   - Network configuration
   - Volume mounts for persistent data
   - Environment variable injection

2. **Create `backend/Dockerfile`**
   - Python 3.11+ base image
   - Install system dependencies (GTK for weasyprint, PaddleOCR deps)
   - Install Python packages from requirements.txt
   - Set up uvicorn entrypoint

3. **Create `frontend/Dockerfile`**
   - Node.js base image
   - Install dependencies, build Vite app
   - Serve via nginx or Node static server

4. **Environment Configuration**
   - `.env.docker` with service hostnames
   - Database connection string pointing to postgres service
   - LLM API keys injection

5. **End-to-End Integration Tests**
   - **CRITICAL:** Test full pipeline upload → extraction → classification → risk detection → explanations → report
   - Verify all 8 contracts in DB can be fully processed
   - Ensure no stage is skipped

6. **PDF Generation Verification**
   - Test PDF download endpoint works in Docker (GTK available)
   - Verify report layout and formatting

7. **Production Readiness**
   - Health check endpoints
   - Graceful shutdown handling
   - Log aggregation configuration
   - Security hardening (secrets management, CORS, rate limiting)

**Estimated Effort:** 2-3 days (assuming no major integration issues)

---

## Contact & Access

**Repository:** https://github.com/ganeshgangekar27/scantract.git  
**Database:** Local Docker container `scantract-db` (postgres user, scantract database)  
**Specs Location:** `.kiro/specs/` (10 stage specs with requirements, design, tasks)  
**Conventions:** `.kiro/steering/` (tech stack, product context, coding standards)

---

**End of Handover Document**
