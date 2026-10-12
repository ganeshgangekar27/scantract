# ScanTract Handover 4
**Date:** 12 October 2026  
**Status:** Backend B7 fixes committed and rebuilt; frontend uncommitted changes exist

---

## 1. What ScanTract Is

ScanTract is an AI-powered contract risk analyzer that identifies risky clauses and missing terms in rental and freelance contracts using Indian legal norms, without giving legal advice. This is a final-year engineering project with a demo scheduled for 13 October 2026. The system processes uploaded PDFs/DOCX files through a multi-stage pipeline: document extraction → normalization → clause segmentation → LLM classification → dual RAG retrieval (legal rules knowledge base + reference contract corpus) → risk detection → explanation generation → structured report.

---

## 2. How to Run

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

Evidence: `git grep -n "scantract_test" -- backend` shows tests/db_config.py:19 defaults to scantract_test

Container status (12 Oct 2026 10:09 IST):
```
scantract-backend    Up About an hour        0.0.0.0:8000->8000/tcp
scantract-db         Up About an hour        0.0.0.0:5432->5432/tcp
scantract-frontend   Up 32 minutes           0.0.0.0:3000->80/tcp
```

Container images built:
```
scantract-frontend 2026-10-12 09:37:44 +0530 IST
scantract-backend  2026-10-11 21:14:50 +0530 IST
```

---

## 3. Architecture and Folders

**Backend structure** (`Get-ChildItem backend\app -Directory -Name`):
- `api/` - FastAPI route handlers (auth, contracts, explanations, pipeline, reports)
- `auth/` - JWT, password hashing, dependencies
- `db/` - SQLAlchemy models, database session
- `document_processing/` - extractor, normalizer, segmenter, orchestrator, processor
- `llm/` - LLM client abstraction (Claude/OpenAI/Gemini), classify_clauses, detect_risk, generate_explanations
- `rag/` - prompt_builder, merge_context, models
- `reports/` - assembler, pdf_generator, models
- `utils/` - error_handling

**Frontend structure** (`Get-ChildItem frontend\src -Directory -Name`):
- `auth/` - Protected routes, auth context
- `components/` - Reusable UI components
- `hooks/` - Custom React hooks
- `lib/` - API client, utilities
- `pages/` - Page components
- `test/` - Test utilities
- `types/` - TypeScript type definitions

**Frontend pages** (`Get-ChildItem frontend\src\pages -Name`):
- `auth/` - LoginPage, SignupPage, ForgotPasswordPage, ResetPasswordPage
- LandingPage.tsx, DashboardPage.tsx, UploadPage.tsx
- ContractsPage.tsx, ReportView.tsx, SettingsPage.tsx
- NotFoundPage.tsx

---

## 4. Pipeline Stages and Statuses

**processing_status values** (from processor.py and orchestrator.py):
- `uploaded` - initial state after file upload
- `processing` - set after segmentation (processor.py:99), maintained throughout pipeline
- `completed` - set by orchestrator when all stages succeed (orchestrator.py:63)
- `failed` - set by stage handlers or top-level except (orchestrator.py:75,132,176,229,244)

**pipeline_stage values** (from orchestrator.py findstr output):
- `segmented` - after clause segmentation (processor.py:100)
- `classifying` → `classified` - Stage 4: LLM clause classification
- `detecting_risks` → `risks_detected` - Stage 7: risk detection
- `generating_explanations` → `explanations_generated` - Stage 8: explanation generation
- `completed` - full pipeline success (orchestrator.py:62)
- `failed` - any stage failure (with failed_stage field indicating which)

Evidence: `findstr -n "pipeline_stage processing_status" backend\app\document_processing\{processor,orchestrator}.py`

---

## 5. API Routes

**Verified routes** (`git grep -n -E "@router\.(get|post|put|patch|delete)" -- backend/app`):

**Auth routes:**
- POST /api/auth/register (auth.py:95)
- POST /api/auth/login (auth.py:158)
- GET /api/auth/me (auth.py:211)
- POST /api/auth/forgot-password (auth.py:233)
- POST /api/auth/reset-password (auth.py:299)
- DELETE /api/auth/me/data (auth.py:374) ✓ **EXISTS**

**Contract routes:**
- POST /api/contracts/upload (contracts.py:89)
- GET /api/contracts/list (contracts.py:170)
- GET /api/contracts/stats (contracts.py:227)
- DELETE /api/contracts/{contract_id} (contracts.py:265)
- POST /api/contracts/{contract_id}/retry (contracts.py:331) ✓ **EXISTS**

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

Evidence: Retry route at backend/app/api/routes/contracts.py:331, DELETE me/data at backend/app/api/routes/auth.py:374

---

## 6. Frontend Routes

**Routes from App.tsx** (`findstr -n "Route path" frontend\src\App.tsx`):
- `/` - Root (redirects to /dashboard if logged in, else /login)
- `/login`, `/signup`, `/forgot-password`, `/reset-password` - Public-only auth pages
- `/dashboard` - Protected: user dashboard
- `/upload` - Protected: contract upload with pipeline tracker
- `/contracts` - Protected: my contracts list
- `/contracts/:contractId` - Protected: contract report view
- `/report/:contractId` - Redirect to /contracts/:contractId
- `/settings` - Protected: user settings
- `*` - 404 not found page

---

## 7. Database State

**Contract status distribution** (12 Oct 2026, `docker exec scantract-db psql -U postgres -d scantract -f /tmp/h4.sql`):
```
 processing_status | pipeline_stage | count 
-------------------+----------------+-------
 completed         | completed      |    11
 failed            | failed         |    10
```

**User count:** 27 users

**Database tables** (\dt output):
- alembic_version (migrations)
- clauses (extracted contract clauses)
- contracts (uploaded contracts with status tracking)
- legal_rules (Indian legal norms knowledge base with pgvector embeddings)
- password_reset_tokens (password reset flow)
- reference_clauses (reference contract corpus with pgvector embeddings)
- risk_findings (detected risks and missing clauses)
- users (authentication and authorization)

---

## 8. Git State and Recent Commits

**Branch status** (12 Oct 2026):
- Current branch: main
- Commits ahead of origin/main: 37 (`git rev-list --count origin/main..HEAD`)
- Uncommitted changes (`git status -s --untracked-files=no`):
  - Modified: .kiro/hooks/test-on-save-backend.json, HANDOVER.md, backend/scripts/auth_live_check.py
  - Deleted: frontend/screenshots.spec.ts
  - Modified frontend files: AppShell.tsx, api.ts, ContractsPage.tsx, auth test files

**Recent commits** (`git log --oneline -30`):
```
d438cf9 (HEAD) fix(frontend): help bot whole-word matching and cited answers
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
edabea1 chore(backend): live check for management routes
9e8ef4b feat(backend): delete, retry, delete-my-data, upload cap, stats
ed731d6 feat(frontend): dashboard and my contracts with real data
605778d fix(frontend): navigation routes each tab to its own page
d68d1ad feat(frontend): results page hardened, why-flagged panel
116e75d feat(frontend): results page with risk ring, filters, findings, missing clauses, pdf
52f70c2 test(frontend): quarantine 6 broken upload/polling tests, suite green
38c91b4 test(frontend): upload page tests, polling tests restored
bc94136 feat(frontend): upload page, live pipeline tracker, polling hook
37fc69e feat(frontend): report/list/upload api layer, types
bc50660 fix(frontend): auth tests green, real-backend auth e2e passing
ab66b6b chore(backend): sample live proof
86cbb23 fix(backend): sample contract tests real and green
a0bf7a7 test(frontend): real-backend auth e2e + screenshots
99f50b0 docs: product spec and remaining work
70f65df docs: verified project handover
f9ec3d4 feat(backend): sample contracts (is_sample) with read-only sharing
bf0ae9f chore(backend): live upload proof script
```

---

## 9. Test Status

**Backend tests** (12 Oct 2026, from d:\scantract\backend):
```
python -m pytest tests --ignore=tests/integration -q --tb=short -p no:cacheprovider
296 passed, 249 warnings in 30.19s
```

**Frontend tests** (12 Oct 2026, from d:\scantract\frontend):
```
npx vitest run
Test Files  28 passed (28)
Tests  220 passed | 6 skipped (226)
```

**TypeScript check:**
```
npx tsc --noEmit
Exit code: 0
```

---

## 10. Environment Variable Names

From backend/.env.example (variable names only, no values shown):
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

## 10b. WORKING RULES (OWNER-STATED, NOT VERIFIED)

See .kiro/steering/working-rules.md for the complete set. Key lessons learned:

**Extra lessons from development:**
- Kiro overclaims: check each claim with raw command output
- Empty output is not proof (e.g., empty grep means "not found", not "found and matches")
- A passing test is not proof until its mutation fails
- If a prompt says STOP, Kiro must stop immediately
- docker cp can fail right after a file write due to filesystem timing - retry once
- The test-on-save hook was disabled by the owner to prevent interference
- Kiro never pushes (all git push commands are forbidden)
- Never stage probe scripts in backend/scripts/ or output .txt files

**Critical rules:**
- Tests must run against scantract_scratch but currently use scantract_test
- Every claim must cite raw command output that proves it
- Never loosen, skip, delete, or xfail a test to get a pass
- A fix only counts after a genuine rebuild (no docker cp live patches)
- Make NO LLM completion calls (zero OpenRouter/Gemini quota spent during development)
- Never print or log contract text, keys, tokens, emails, or passwords

---

## 11. UNPROVEN OR RISKY (OWNER-STATED, NOT VERIFIED)

### (a) B7 Fix Not Proven on Real Upload
The B7 fix (processing_status stays 'processing' until the pipeline finishes) is committed and deployed in the rebuilt backend container (scantract-backend 2026-10-11 21:14:50) but NOT proven with a real upload. Proof requires one upload while polling the database every 10 seconds to observe the lifecycle: uploaded → processing → completed (or failed). The free OpenRouter key allows about 2 uploads per day and was used on 12 October.

### (b) Earlier Test Failures Never Reproduced
6 backend tests (test_auth.py x3, test_contract_management.py x1, test_route_isolation.py x2) failed with FK violations and deadlocks during an earlier run. The cause was never reproduced. The suite later passed 296 tests with the test-on-save hook disabled. Hypothesis: concurrent pytest runs on the shared scantract_test DB caused the failures.

### (c) Uncommitted Frontend Work
Files modified but not committed (git status -s):
- frontend/src/components/AppShell.tsx
- frontend/src/lib/api.ts (deleteContract, retryContract, deleteMyData functions)
- frontend/src/pages/ContractsPage.tsx
- frontend/src/pages/auth/ForgotPasswordPage.test.tsx
- frontend/src/pages/auth/ResetPasswordPage.test.tsx

The frontend container rebuilt on 2026-10-12 09:37:44 contains these changes.

### (d) Help-Bot Citations Use Line Numbers
The canned-answer help bot uses line numbers to cite legal rules and reference clauses. These will rot as the knowledge base evolves.

### (e) 6 Vitest Tests Skipped
Frontend tests show "220 passed | 6 skipped" - reason for skips unknown.

### (f) Tests Run Against scantract_test
Tests run against scantract_test (not scantract_scratch) which holds real-looking data. Working rules say tests should use scantract_scratch, but db_config.py defaults to scantract_test.

### (g) Untracked Probe Scripts and Output Files
About 120 untracked files in backend/scripts/, frontend/*.txt, frontend/e2e/, and frontend/scripts/ (probe scripts and test output). Never stage them. Secret-scan before any push.

### (h) Backup Location
The pre_b7g.sql backup (660 KB, created before backend rebuild) is in %TEMP%\scantract_backups and must be copied somewhere permanent before the temp directory is cleaned.

### (i) Mutation Proof Incomplete
The mutation proof for processor.py setting 'completed' after segmentation (the original bug that B7 fixed) was never done. TC-1 test doesn't directly test processor.py line 99 - only orchestrator behavior.

---

## 12. REMAINING WORK (OWNER-STATED, NOT VERIFIED)

### P0 (Never Cut - Must Have for Demo)
1. **B7 real-upload proof:** One upload while polling DB to verify lifecycle works correctly
2. **Browser check:** Verify new AppShell and ContractsPage UI work correctly
3. **Route verification:** Confirm retry and me/data routes exist and work (Section 5 shows they exist in code)
4. **Commit frontend work:** After manual browser check, commit the 5 modified frontend files
5. **Results page redesign A+C:** Summary first, top 5 risks, collapsed finding cards, "Show all N" button
6. **Legal pages:** Terms, privacy policy, about page
7. **Public URL:** ngrok free dev domain with restart-stability check (verify URL survives container restart)
8. **Process demo contract:** Run one contract through pipeline in advance for demo fallback
9. **README:** Usage instructions, architecture diagram, setup guide
10. **Secret scans:** Run scan_secrets.py and manual grep for leaked keys before push
11. **Push dry-run:** `git push --dry-run` then owner pushes (Kiro never pushes)
12. **Screen-recording backup:** Record demo as backup in case live demo fails

### P1 (Important but Can Be Simplified)
1. **Tracker stage visuals:** Improve pipeline stage indicator UI
2. **Polish pages:** Login, signup, forgot password, reset password, Dashboard, Upload, My Contracts, Settings
3. **Clean test users:** Delete test users after backup
4. **Check api.test.ts coverage:** Restore ~234 lines deleted in commit 64128b6 (recover from 61fc20f)

### P2 (Post-Deadline)
1. **Fresh-clone Docker test:** Clone repo fresh, run `docker compose up`, verify it works (drop if time-short)
2. **Real hosting:** Render backend, Supabase Postgres with pgvector, Vercel or static hosting for frontend
3. **Research paper:** Write up methodology, results, evaluation
4. **Copyright:** Add LICENSE file, check institute IPR policy, verify legal KB and sample contract licenses

### Cut First if Short on Time
- Notifications panel
- Feedback thumbs-up/down on findings
- Extra dashboard charts

---

## 13. DEMO PLAN (OWNER-STATED, NOT VERIFIED)

**Date:** 13 October 2026  
**Method:** Demo via laptop + ngrok free dev domain  
**Backups:** localhost fallback, pre-recorded screen capture  
**Strategy:** Use an already-completed contract rather than live upload to avoid:
- Depending on LLM API quota
- Risk of pipeline failure during live demo
- 3-4 minute wait time for pipeline completion

---

**End of Handover 4**
