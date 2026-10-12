# ScanTract Handover 5

**Date:** 12 October 2026  
**Status:** Frontend F1/F3/F5 redesign completed; backend B7 deployed; uncommitted frontend work exists

---

## 1. What ScanTract Is

**Carried from HANDOVER_4, not re-checked:**

ScanTract is an AI-powered contract risk analyzer that identifies risky clauses and missing terms in rental and freelance contracts using Indian legal norms, without giving legal advice. This is a final-year engineering project with a demo scheduled for 13 October 2026 (submission deadline extended). The system processes uploaded PDFs/DOCX files through a multi-stage pipeline: document extraction → normalization → clause segmentation → LLM classification → dual RAG retrieval (legal rules knowledge base + reference contract corpus) → risk detection → explanation generation → structured report.

---

## 2. How to Run

**Carried from HANDOVER_4, not re-checked:**

**Command:** `docker compose up` from workspace root

**Services & Ports:**
- Backend (FastAPI): http://localhost:8000 (API docs at /docs)
- Frontend (React+Vite dev): http://localhost:5173
- Frontend (Nginx prod): http://localhost:3000  
- PostgreSQL + pgvector: localhost:5432

**Database names:**
- Production/demo: `scantract` (main working database)
- Test: `scantract_test` (tests use this via backend/tests/db_config.py)
- Scratch: `scantract_scratch` (exists but tests use scantract_test)

**Container status (verified 12 Oct 2026 21:08 IST):**
```
docker compose ps
NAME                 IMAGE                    SERVICE    CREATED        STATUS                 PORTS
scantract-backend    scantract-backend        backend    24 hours ago   Up 3 hours             0.0.0.0:8000->8000/tcp
scantract-db         ankane/pgvector:latest   db         2 weeks ago    Up 3 hours (healthy)   0.0.0.0:5432->5432/tcp
scantract-frontend   scantract-frontend       frontend   6 hours ago    Up 3 hours             0.0.0.0:3000->80/tcp
```

**Container images built (verified 12 Oct 2026 21:08 IST):**
```
docker inspect -f "{{.Name}} {{.Created}} {{.Image}}"
/scantract-frontend 2026-10-12T09:30:43.448201395Z sha256:02d7052fd8605...
/scantract-backend  2026-10-11T15:45:03.493518095Z sha256:f4cdb592c89a2...
```
- Frontend built: 2026-10-12 09:30:43 (15:00:43 IST)
- Backend built: 2026-10-11 15:45:03 (21:15:03 IST)

---

## 3. Architecture and Folders

**Carried from HANDOVER_4, not re-checked:**

**Backend structure:**
- `api/` - FastAPI route handlers (auth, contracts, explanations, pipeline, reports)
- `auth/` - JWT, password hashing, dependencies
- `db/` - SQLAlchemy models, database session
- `document_processing/` - extractor, normalizer, segmenter, orchestrator, processor
- `llm/` - LLM client abstraction (Claude/OpenAI/Gemini), classify_clauses, detect_risk, generate_explanations
- `rag/` - prompt_builder, merge_context, models
- `reports/` - assembler, pdf_generator, models
- `utils/` - error_handling

**Frontend structure:**
- `auth/` - Protected routes, auth context
- `components/` - Reusable UI components
- `hooks/` - Custom React hooks
- `lib/` - API client, utilities
- `pages/` - Page components
- `test/` - Test utilities
- `types/` - TypeScript type definitions

---

## 4. Pipeline Stages and Statuses

**Carried from HANDOVER_4, not re-checked:**

**processing_status values** (from processor.py and orchestrator.py):
- `uploaded` - initial state after file upload
- `processing` - set after segmentation (processor.py:99), maintained throughout pipeline
- `completed` - set by orchestrator when all stages succeed (orchestrator.py:63)
- `failed` - set by stage handlers or top-level except (orchestrator.py:75,132,176,229,244)

**pipeline_stage values** (from orchestrator.py):
- `segmented` - after clause segmentation (processor.py:100)
- `classifying` → `classified` - Stage 4: LLM clause classification
- `detecting_risks` → `risks_detected` - Stage 7: risk detection
- `generating_explanations` → `explanations_generated` - Stage 8: explanation generation
- `completed` - full pipeline success (orchestrator.py:62)
- `failed` - any stage failure (with failed_stage field indicating which)

---

## 5. API Routes

**Carried from HANDOVER_4, not re-checked:**

**Auth routes:**
- POST /api/auth/register (auth.py:95)
- POST /api/auth/login (auth.py:158)
- GET /api/auth/me (auth.py:211)
- POST /api/auth/forgot-password (auth.py:233)
- POST /api/auth/reset-password (auth.py:299)
- DELETE /api/auth/me/data (auth.py:374) ✓ EXISTS

**Contract routes:**
- POST /api/contracts/upload (contracts.py:89)
- GET /api/contracts/list (contracts.py:170)
- GET /api/contracts/stats (contracts.py:227)
- DELETE /api/contracts/{contract_id} (contracts.py:265)
- POST /api/contracts/{contract_id}/retry (contracts.py:331) ✓ EXISTS

**Explanation routes:**
- GET /api/contracts/{contract_id}/explanations (explanations.py:21)
- POST /api/contracts/{contract_id}/explanations/regenerate (explanations.py:85)

**Pipeline routes:**
- POST /api/contracts/{contract_id}/classify (pipeline.py:36)
- POST /api/contracts/{contract_id}/detect-risks (pipeline.py:122)
- POST /api/contracts/{contract_id}/generate-explanations (pipeline.py:211)

**Report routes:**
- GET /api/contracts/{contract_id}/report (reports.py:21)
- GET /api/contracts/{contract_id}/report/pdf (reports.py:98)

---

## 6. Frontend Routes and Components

**Routes verified (12 Oct 2026 21:08 IST):**
```
findstr /N "Route path" frontend\src\App.tsx
49:  <Route path="/" element={<RootRoute />} />
52:  <Route path="/login" element={<PublicOnlyRoute><LoginPage /></PublicOnlyRoute>} />
53:  <Route path="/signup" element={<PublicOnlyRoute><SignupPage /></PublicOnlyRoute>} />
54:  <Route path="/forgot-password" element={<PublicOnlyRoute><ForgotPasswordPage /></PublicOnlyRoute>} />
55:  <Route path="/reset-password" element={<PublicOnlyRoute><ResetPasswordPage /></PublicOnlyRoute>} />
56:  <Route path="/privacy" element={<PrivacyPage />} />
57:  <Route path="/terms" element={<TermsPage />} />
60:  <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
61:  <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
62:  <Route path="/contracts" element={<ProtectedRoute><ContractsPage /></ProtectedRoute>} />
63:  <Route path="/contracts/:contractId" element={<ProtectedRoute><ReportView /></ProtectedRoute>} />
64:  <Route path="/report/:contractId" element={<Navigate to="/contracts/:contractId" replace />} />
65:  <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
68:  <Route path="*" element={<NotFoundPage />} />
```

**Routes summary:**
- `/` - Root (redirects to /dashboard if authenticated, else LandingPage)
- `/login`, `/signup`, `/forgot-password`, `/reset-password` - Public-only auth pages
- `/privacy`, `/terms` - Public legal pages (LegalPage.tsx) ✓ NEW
- `/dashboard` - Protected: user dashboard
- `/upload` - Protected: contract upload with pipeline tracker
- `/contracts` - Protected: my contracts list (with retry/delete buttons) ✓ UPDATED
- `/contracts/:contractId` - Protected: contract report view (summary-first, collapsed cards) ✓ UPDATED
- `/settings` - Protected: user settings
- `*` - 404 not found

**Components verified (12 Oct 2026 21:08 IST):**
```
cmd /c "dir /b frontend\src\components"
AppShell.tsx              ✓ UPDATED (retry/delete contract actions)
ClauseHighlight.tsx
ContractText.tsx
ContractUpload.tsx
ExplanationPanel.tsx
HelpBot.test.tsx
HelpBot.tsx
landing
MissingClausesPanel.tsx
PipelineTracker.test.tsx
PipelineTracker.tsx
RiskSummaryHeader.tsx
SeverityBar.tsx           ✓ NEW (colored severity bars for Top 5 risks)
ui
__tests__
```

**Pages verified (12 Oct 2026 21:08 IST):**
```
cmd /c "dir /b frontend\src\pages"
auth
ContractsPage.test.tsx
ContractsPage.tsx         ✓ UPDATED (retry/delete buttons)
DashboardPage.test.tsx
DashboardPage.tsx
LandingPage.test.tsx
LandingPage.tsx
LegalPage.test.tsx        ✓ NEW
LegalPage.tsx             ✓ NEW (Privacy Policy and Terms of Service)
NotFoundPage.tsx
ReportView.test.tsx
ReportView.tsx            ✓ UPDATED (summary-first, Top 5 risks, collapsed cards, "Show all N")
SettingsPage.test.tsx
SettingsPage.tsx
UploadPage.test.tsx
UploadPage.tsx
```

**Key frontend features (from commit 260668c):**
- **ReportView redesign:**
  - Summary-first layout (risk score, severity counts displayed prominently)
  - Top 5 highest-severity risks shown by default
  - Collapsed finding cards (click to expand for full details)
  - "Show all N findings" button to expand all cards
  - SeverityBar component for visual severity indication
  - Filter chips with counts matching visible cards
  
- **LegalPage (Privacy & Terms):**
  - /privacy route serves Privacy Policy
  - /terms route serves Terms of Service
  - Footer links on landing page
  
- **ContractsPage enhancements:**
  - Retry button for failed contracts
  - Delete button for completed/failed contracts
  - Integrated with AppShell actions

- **AppShell updates:**
  - Retry contract action (calls POST /api/contracts/{id}/retry)
  - Delete contract action (calls DELETE /api/contracts/{id})
  - Delete my data action (calls DELETE /api/auth/me/data)

---

## 7. Database State

**Carried from HANDOVER_4, not re-checked:**

**Contract status distribution (from H4, 12 Oct 2026):**
- completed/completed: 11 contracts
- failed/failed: 10 contracts

**User count:** 27 users

**Database tables:**
- alembic_version (migrations)
- clauses (extracted contract clauses)
- contracts (uploaded contracts with status tracking)
- legal_rules (Indian legal norms knowledge base with pgvector embeddings)
- password_reset_tokens (password reset flow)
- reference_clauses (reference contract corpus with pgvector embeddings)
- risk_findings (detected risks and missing clauses)
- users (authentication and authorization)

---

## 8. Git State

**Git status verified (12 Oct 2026 21:08 IST):**
```
git status -sb
## main...origin/main [ahead 40]
 M .kiro/hooks/test-on-save-backend.json
 M HANDOVER.md
 M backend/scripts/auth_live_check.py
 D frontend/screenshots.spec.ts
 M frontend/src/components/AppShell.tsx
 M frontend/src/lib/api.ts
 M frontend/src/pages/ContractsPage.tsx
 M frontend/src/pages/auth/ForgotPasswordPage.test.tsx
 M frontend/src/pages/auth/ResetPasswordPage.test.tsx
```

**Uncommitted changes:**
- 9 modified/deleted files (hook config, HANDOVER.md, 1 backend script, 5 frontend files)
- ~157 untracked files (probe scripts, test outputs in backend/scripts/, frontend/e2e/, frontend/*.txt)

**Note:** Untracked file count via `find /c "?"` failed with "File not found - ?" error. Count estimated from git status -s output.

**Recent commits verified (12 Oct 2026 21:08 IST):**
```
git log --oneline -15
03da0b9 (HEAD -> main) docs: architecture facts
260668c feat(frontend): report summary-first redesign, collapsed cards, severity bar, legal pages
58e5455 docs: handover 4
d438cf9 fix(frontend): help bot whole-word matching and cited answers
a6165f6 feat(frontend): canned-answer help bot
2f8e3e6 test(backend): real tests for processing_status lifecycle
f951488 fix(backend): processing_status stays processing until pipeline finishes
312101d fix(backend): risk detection guard accepts processing status
f270197 docs: handover 3
b3f559b feat(frontend): professional interactive landing page
ece59a3 feat(frontend): animated landing page
64128b6 fix(frontend): never bake absolute api url into production build
f224814 docs: handover 2
61fc20f fix(frontend): clearer login error handling
f3c5ac0 feat(frontend): settings, delete my data, retry and delete contracts
```

**Branch:** main  
**Commits ahead of origin/main:** 40  
**Last commit:** 03da0b9 docs: architecture facts

---

## 9. Test Status

**Backend tests verified (12 Oct 2026 21:08 IST):**
```
python -m pytest tests --ignore=tests/integration -q 2>&1 | findstr /C:"passed" /C:"failed"
296 passed, 249 warnings in 35.01s
```
✓ All 296 backend tests passing

**Frontend tests verified (12 Oct 2026 21:08 IST):**
```
npx vitest run 2>&1 | findstr /C:"FAIL" /C:"Tests" /C:"Test Files"
Test Files  30 passed (30)
Tests  259 passed | 6 skipped (265)
```
✓ 30 test files passed (was 28 in H4), 259 tests passed, 6 skipped

**TypeScript check verified (12 Oct 2026 21:08 IST):**
```
npx tsc --noEmit
EXIT_CODE: 0
```
✓ No TypeScript errors

**Summary:**
- Backend: 296 passed (unchanged from H4)
- Frontend: 259 passed (was 220 in H4), 6 skipped (unchanged)
- Frontend test files: 30 (was 28 in H4) - added LegalPage.test.tsx
- TypeScript: Clean compilation

---

## 10. Environment Variable Names

**Carried from HANDOVER_4, not re-checked:**

From backend/.env.example (variable names only, no values):
- DATABASE_URL
- OPENAI_API_KEY
- LLM_PROVIDER
- CLAUDE_API_KEY
- CLAUDE_MODEL
- GEMINI_API_KEY
- GEMINI_MODEL
- UPLOAD_TEMP_DIR
- MAX_UPLOAD_SIZE_MB
- MAX_UPLOADS_PER_DAY
- EMBEDDING_MODEL
- EMBEDDING_DIMENSIONS
- MAX_CONTEXT_TOKENS
- DEDUPLICATION_THRESHOLD
- MIN_CHUNKS_PER_SOURCE
- LLM_CONCURRENCY_LIMIT
- LLM_MAX_RETRIES
- LLM_TIMEOUT_SECONDS
- LOG_LEVEL
- JWT_SECRET
- RESET_LINK_MODE

---

## 11. ROLE AND WORKING RULES (OWNER-STATED, NOT VERIFIED)

- Claude writes Kiro-ready PROMPTS, not code. Every prompt starts with a tag [BACKEND] or [FRONTEND] plus a name (the owner runs a BACKEND and a FRONTEND Kiro window in parallel). One prompt at a time, at most one question per reply, fast, honest, concise.

- Every prompt starts with "Read .kiro/steering/working-rules.md and show its last 10 lines" and PREFLIGHT docker info | findstr /C:Version /C:Context, and ends with "FINAL: raw output first, then Claim | Command | PROVEN or NOT CHECKED, then anything that did not go as planned."

- Never accept summaries as proof; demand raw output. Empty output is not proof. Never loosen assertions to fit wrong behaviour. Mutation proofs: hash before, break, test FAILS, restore, hashes equal. A fix counts only after a real docker rebuild plus a grep or hash proving the new code is in the container. Never rebuild the backend while a contract is processing.

- PowerShell: no multi-line python -c, never create files with > or Out-File, SQL only via a .sql file + docker cp + psql -f (user postgres, DB scantract; retry docker cp once if it fails right after a write). Backend tests only: python -m pytest tests --ignore=tests/integration from backend/, never two pytest runs at once. Frontend: vitest only (Playwright hangs); never use --reporter=verbose on ReportView tests (dumps the DOM), always pipe vitest to findstr.

- No git reset --hard/revert/clean/stash/checkout; never git add .; stage explicit paths; never stage probe scripts or output .txt files. Kiro never pushes; the owner pushes after secret scans (python backend\scripts\scan_secrets.py = 0; git grep -lE "sk-or-v1-[0-9a-f]{20,}|AIza[0-9A-Za-z_-]{20,}" exit code 1) and git push --dry-run first.

- Keys live in d:\scantract\.env: Kiro must NEVER open or print it; never ask the owner to paste a key or an ngrok token. Zero cost: free OpenRouter key (about 2 live uploads per day), Gemini key for embeddings.

- Frontend prompts only under frontend/, backend only under backend/. Kiro's shell has a permissions allow list (Select-Object may be blocked; use findstr). The test-on-save hook is disabled.

- Stack: FastAPI + React/Vite/TypeScript/Tailwind v3 + Postgres 15/pgvector; Docker Compose (db, backend 8000, frontend/nginx 3000 proxying /api; vite dev 5173). Code is baked into images (only uploads/ is bind-mounted).

---

## 12. LESSONS (OWNER-STATED, NOT VERIFIED)

- Kiro writes "no deviations" even when it deviated, and its final summaries get rebuilt after context summarisation and can contain fabricated hashes (seen once: the F1-A-PATCH baseline block). Check every specific claim; copy hashes from tool output only.

- Kiro loosens tests to make them pass (getByText to getAllByText, > to >=, weaker matchers). Always audit git diff -U2 of edited tests.

- A PowerShell/cmd mix-up breaks "dir /S /B"; Kiro then substitutes other commands and calls it no deviation.

- A model "high volume of traffic" error means nothing ran; switch model and re-run the same prompt.

- nginx serves index.html for every path, so curl 200 on /privacy proves nothing; only the bundle grep or the browser does.

- docker exec grep on the minified bundle can time out; use grep -l on the file or strings | grep -m1, and expect long output.

---

## 13. UNPROVEN OR RISKY (OWNER-STATED, NOT VERIFIED)

- B7 real-upload lifecycle proof (uploaded, processing, completed) never run on a real upload; OpenRouter quota is used up.

- The report PDF is about 7 pages for a 2-page contract: each finding repeats reason, explanation and full clause text. The owner is worried the report is longer than the contract.

- "rent_increase_limitation" is flagged missing for the sample rental contract although clause 8 covers rent revision without the 8 percent cap: arguable, be ready to explain.

- backend/scripts/auth_live_check.py (uncommitted) uses a variable qa_email that is never defined: it would crash with NameError. Do not run or stage it until fixed.

- Uncommitted and unchecked in the browser: AppShell.tsx, api.ts (deleteContract, retryContract, deleteMyData), ContractsPage.tsx and the two auth tests.

- The 6 skipped vitest tests: reason unknown. 6 earlier backend failures (FK violations and deadlocks) never reproduced. Tests run against scantract_test, not scantract_scratch. Mutation proof for processor.py setting completed after segmentation was never done. Help-bot citations use line numbers (will rot).

- About 120 untracked probe scripts and output .txt files (including frontend/test_output.txt): never stage; secret-scan before any push. pre_b7g.sql backup is in %TEMP%\scantract_backups and must be copied somewhere permanent.

- "Privacy Policy" and "Terms of Service" heading strings were never shown in the bundle by grep; the owner confirmed in the browser that /privacy and /terms and the footer links work.

---

## 14. REMAINING WORK (OWNER-STATED, NOT VERIFIED)

**In order:**

 1. Run F5-VERIFY-COMMIT if not yet done (re-verify after the tsc fix; commit only the 11 F1/F3/F5 files by explicit path).

 2. Rebuild the frontend once and prove the new code is in the container; owner browser check: severity bar, collapsed cards, expand, "Show all N", chip counts equal card counts, retry and delete buttons on My Contracts (use only a junk or failed contract).

 3. Then commit AppShell.tsx, api.ts, ContractsPage.tsx and the two auth tests by explicit path.

 4. Optional, backend: shorten the PDF report (one-page summary first: score, severity counts, Top 5 one-liners; then per finding: clause number, the last sentence of the explanation, citation; drop duplicated reason and full clause text). Needs tests, mutation proof and a backend rebuild when no contract is processing. Optional, frontend: fold Reason into the explanation in the Why flagged panel.

 5. D3: back up the DB, then clean test users (SQL via .sql file). Copy pre_b7g.sql out of %TEMP%.

 6. D2: README (usage, architecture, setup), fresh secret scans, git push --dry-run, owner pushes.

 7. Deployment (the owner will do it on the day after this handover): decide between laptop + ngrok free dev domain with a restart-stability check, or real hosting; owner runs ngrok himself.

 8. Demo rehearsal with an already-completed contract (no live upload), and a screen recording as backup.

 9. P1 if time: fix auth_live_check.py (define qa_email), restore api.test.ts coverage (about 234 lines deleted in commit 64128b6, recover from 61fc20f), tracker stage visuals, polish demo-path pages.

 10. After the deadline: fresh-clone Docker test, real hosting, research paper, copyright/LICENSE.

 Cut first if short on time: notifications panel, feedback thumbs, extra charts.

---

## 15. DEMO AND DEPLOYMENT PLAN (OWNER-STATED, NOT VERIFIED)

Submission date was extended; the owner wants to finish remaining build work today and deploy the next day. Demo uses an already-completed contract (avoid LLM quota, pipeline failure and the 3-4 minute wait), via laptop + ngrok free dev domain, with localhost and a screen recording as backups. Never-cut features: auth, upload, tracker, results page, landing page, canned-answer help bot (no LLM).

---

**End of Handover 5**
