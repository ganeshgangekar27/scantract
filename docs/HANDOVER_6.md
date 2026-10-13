# ScanTract Handover 6

**Date:** 13 October 2026  
**Status:** Dashboard status mix card fixed; LoginPage and PipelineTracker redesigned; uncommitted work exists

---

## 1. What ScanTract Is

**Carried from HANDOVER_5, not re-checked:**

ScanTract is an AI-powered contract risk analyzer that identifies risky clauses and missing terms in rental and freelance contracts using Indian legal norms, without giving legal advice. This is a final-year engineering project with a demo scheduled for 13 October 2026 (submission deadline extended). The system processes uploaded PDFs/DOCX files through a multi-stage pipeline: document extraction → normalization → clause segmentation → LLM classification → dual RAG retrieval (legal rules knowledge base + reference contract corpus) → risk detection → explanation generation → structured report.

---

## 2. How to Run

**Carried from HANDOVER_5, not re-checked:**

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

---

## 3. Architecture and Folders

**Carried from HANDOVER_5, not re-checked:**

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

**Carried from HANDOVER_5, not re-checked:**

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

**Carried from HANDOVER_5, not re-checked:**

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

**Routes verified (13 Oct 2026 11:45 IST):**
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

**Routes:** Same as HANDOVER_5 (no route changes)

**Components verified (13 Oct 2026 11:45 IST):**
```
cmd /c "dir /b frontend\src\components"
AppShell.tsx
ClauseHighlight.tsx
ContractText.tsx
ContractUpload.tsx
ExplanationPanel.tsx
HelpBot.test.tsx
HelpBot.tsx
landing
MissingClausesPanel.tsx
PipelineTracker.stages.test.tsx  ✓ NEW (17 tests for stepper stages)
PipelineTracker.test.tsx
PipelineTracker.tsx              ✓ UPDATED (stepper redesign, single DOM tree)
RiskSummaryHeader.tsx
SeverityBar.tsx
ui
__tests__
```

**Pages verified (13 Oct 2026 11:45 IST):**
```
cmd /c "dir /b frontend\src\pages"
auth
ContractsPage.test.tsx
ContractsPage.tsx
DashboardPage.test.tsx
DashboardPage.tsx                ✓ UPDATED (Status mix card percentages fix, commit 6229576)
LandingPage.test.tsx
LandingPage.tsx
LegalPage.test.tsx
LegalPage.tsx
NotFoundPage.tsx
ReportView.test.tsx
ReportView.tsx
SettingsPage.test.tsx
SettingsPage.tsx
UploadPage.test.tsx
UploadPage.tsx
```

**Key NEW features since HANDOVER_5:**

- **Dashboard Status mix card (commit 6229576 "fix(frontend): honest status mix card on dashboard"):**
  - Displays Completed / In progress / Failed with percentages summing to 100%
  - Uses largest-remainder rounding to ensure sum equals 100%
  - Excludes sample contracts from percentages
  - Percentages shown to 1 decimal place
  - **Warning:** If all contracts are Completed (100% in one slice), the ring may appear as a plain grey ring because a single 100% slice has the same start and end point in the arc code (unverified by owner)

- **LoginPage.tsx redesign (commit a6a23d0 + uncommitted changes):**
  - Two-column layout on desktop (gradient brand panel + form panel)
  - Motion animations with framer-motion
  - useReducedMotion accessibility support
  - 21 auth tests pass (LoginPage.test.tsx, SignupPage.test.tsx, etc.)
  - **Not yet built into container** - localhost:3000 still shows old login until frontend rebuild

- **PipelineTracker.tsx redesign (uncommitted):**
  - Stepper-based visual with progress line
  - Single DOM tree (replaced multiple independent components)
  - 17 new tests in PipelineTracker.stages.test.tsx
  - **Progress line orientation unverified** - must be vertical on mobile, horizontal on desktop
  - **Visual not seen** - only animates during live upload, which OpenRouter quota rules out
  - Component code never audited by owner or Claude

---

## 7. Database State

**Carried from HANDOVER_5, not re-checked:**

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

**Git status verified (13 Oct 2026 11:45 IST):**
```
git --no-pager log --oneline -8
6229576 (HEAD -> main) fix(frontend): honest status mix card on dashboard
a6a23d0 feat(frontend): contract retry/delete, delete-my-data, app shell updates
dce9471 docs: handover 5
03da0b9 docs: architecture facts
260668c feat(frontend): report summary-first redesign, collapsed cards, severity bar, legal pages
58e5455 docs: handover 4
d438cf9 fix(frontend): help bot whole-word matching and cited answers
a6165f6 feat(frontend): canned-answer help bot

git --no-pager status -sb
## main...origin/main [ahead 43]
 M .kiro/hooks/test-on-save-backend.json
 M HANDOVER.md
 M backend/scripts/auth_live_check.py
 D frontend/screenshots.spec.ts
 M frontend/src/components/PipelineTracker.tsx
 M frontend/src/pages/auth/LoginPage.tsx

git --no-pager status -s --untracked-files=no
 M .kiro/hooks/test-on-save-backend.json
 M HANDOVER.md
 M backend/scripts/auth_live_check.py
 D frontend/screenshots.spec.ts
 M frontend/src/components/PipelineTracker.tsx
 M frontend/src/pages/auth/LoginPage.tsx
```

**Branch:** main  
**Commits ahead of origin/main:** 43  
**Last commit:** 6229576 fix(frontend): honest status mix card on dashboard

**Uncommitted changes:**
- 6 modified/deleted files (hook config, HANDOVER.md, auth_live_check.py, screenshots.spec.ts deleted, PipelineTracker.tsx, LoginPage.tsx)
- ~150 untracked files (probe scripts, test outputs, including NEW: frontend/src/components/PipelineTracker.stages.test.tsx)

**Recent commits since HANDOVER_5:**
- 6229576: Dashboard Status mix card fix (percentages sum to 100%)
- a6a23d0: AppShell retry/delete/deleteMyData (from F5 commits, not in H5)
- dce9471: Handover 5 documentation

---

## 9. Environment Variable Names

**Carried from HANDOVER_5, not re-checked:**

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

## 10. UNCOMMITTED WORK AND DOCKER STATE

**Uncommitted files (13 Oct 2026 11:45 IST):**
```
git --no-pager status -s --untracked-files=no
 M .kiro/hooks/test-on-save-backend.json
 M HANDOVER.md
 M backend/scripts/auth_live_check.py
 D frontend/screenshots.spec.ts
 M frontend/src/components/PipelineTracker.tsx
 M frontend/src/pages/auth/LoginPage.tsx
```

- **Never to be staged without a decision:** HANDOVER.md (931 lines changed), .kiro/hooks/test-on-save-backend.json, backend/scripts/auth_live_check.py (known NameError on qa_email), deleted frontend/screenshots.spec.ts

- **Uncommitted and awaiting browser check + commit:** PipelineTracker.tsx, LoginPage.tsx

- **Untracked test file (new):** frontend/src/components/PipelineTracker.stages.test.tsx (17 tests, all passing)

**Docker container state (13 Oct 2026 11:45 IST):**
```
docker compose ps
NAME                 IMAGE                    COMMAND                   SERVICE    CREATED        STATUS                 PORTS
scantract-backend    scantract-backend        "sh -c '\n  echo 'Run…"   backend    39 hours ago   Up 3 hours             0.0.0.0:8000->8000/tcp
scantract-db         ankane/pgvector:latest   "docker-entrypoint.s…"    db         2 weeks ago    Up 3 hours (healthy)   0.0.0.0:5432->5432/tcp
scantract-frontend   scantract-frontend       "/docker-entrypoint.…"    frontend   2 hours ago    Up 2 hours             0.0.0.0:3000->80/tcp

docker inspect -f "{{.Name}} {{.Created}}"
/scantract-frontend 2026-10-13T04:04:07.428965487Z
/scantract-backend 2026-10-11T15:45:03.493518095Z
```

**Container build times:**
- **Frontend:** 2026-10-13 04:04:07 UTC (09:34:07 IST) - contains Status mix card fix, does NOT contain LoginPage or PipelineTracker redesigns
- **Backend:** 2026-10-11 15:45:03 UTC (21:15:03 IST) - unchanged since H4

**Code in containers:**
- Frontend localhost:3000 (nginx) contains: commits up to 6229576 (Dashboard fix), does NOT contain uncommitted LoginPage/PipelineTracker redesigns
- Frontend localhost:5173 (vite dev) needs "npm run dev" run by owner to see uncommitted changes
- Backend localhost:8000 contains: B7 fix (processor.py:99 sets 'processing')

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

### ADDED IN H6 (OWNER-STATED, NOT VERIFIED)

- LoginPage.tsx redesign (gradient brand panel on desktop, motion, useReducedMotion): 21 auth tests pass and tsc 0, but never seen in a browser and not built into the container (localhost:3000 still shows the old login until a rebuild; localhost:5173 needs "npm run dev" run by the owner in a separate window).

- PipelineTracker.tsx redesign (stepper, single DOM tree) plus new PipelineTracker.stages.test.tsx: 17 tests pass and tsc 0, but the component code was never audited by the owner or Claude, and the progress-line orientation is unverified (it must be vertical on mobile and horizontal on desktop; Kiro's summary claimed the reverse). The tracker only animates during a live upload, which the OpenRouter quota rules out, so the visual cannot be seen without a mocked state.

- Dashboard Status mix card (commit 6229576): after the fix, if every contract is Completed the ring may show as a plain grey ring, because a single 100 percent slice has the same start and end point in the arc code. The owner has not confirmed what it looks like. Mutation proofs B (Math.round instead of largest-remainder) and C (samples included) were never completed; only mutation A was shown, and the hash and test results in that run were inconsistent, so treat the rounding test as unproven.

- DashboardPage.test.tsx beforeEach auth mock: the original signup and checkAuth lines may still be changed to register, forgotPassword and resetPassword (the revert was claimed but its diff output showed the change still present). All tests pass, so it is low priority.

- Uncommitted and never to be staged without a decision: HANDOVER.md (931 lines changed), .kiro/hooks/test-on-save-backend.json, backend/scripts/auth_live_check.py (known NameError on qa_email), the deleted frontend/screenshots.spec.ts, and about 150 untracked probe scripts and .txt files.

---

## 14. REMAINING WORK (OWNER-STATED, NOT VERIFIED)

**In order:**

 1. F13: ONE frontend rebuild, then a bundle grep proving the new code is in the container (strings from the LoginPage and PipelineTracker redesign), then owner browser check of /login, the dashboard Status mix card (including an all-Completed case), My Contracts and the report page. If the owner approves, commit LoginPage.tsx, PipelineTracker.tsx and PipelineTracker.stages.test.tsx by explicit path. If the owner rejects the login or tracker visuals, restore from %TEMP%\scantract_backups (LoginPage.tsx.bak and PipelineTracker.tsx.bak, check hashes) rather than keep debugging.

 2. Fix the dashboard ring if the all-Completed case is grey (small bug fix, needs a test).

 3. D3: back up the DB, copy pre_b7g.sql out of %TEMP%\scantract_backups to a permanent folder, then clean test users with a .sql file (keep the completed demo contract).

 4. D2: README (usage, architecture, setup), fresh secret scans, git push --dry-run, owner pushes.

 5. Deployment (next day): laptop + ngrok free dev domain with a restart-stability check; the owner runs ngrok; localhost and a screen recording as backups.

 6. Demo rehearsal with the already-completed contract (no live upload) and a screen recording.

 7. Optional if time: fix auth_live_check.py (define qa_email), restore api.test.ts coverage (about 234 lines deleted in commit 64128b6, recover from 61fc20f), shorten the PDF report, tracker polish.

 8. After the deadline: fresh-clone Docker test, real hosting, research paper, copyright/LICENSE.

 Cut first if short on time: notifications panel, feedback thumbs, extra charts.

---

## 15. DEMO AND DEPLOYMENT PLAN (OWNER-STATED, NOT VERIFIED)

Submission date was extended; the owner wants to finish remaining build work today and deploy the next day. Demo uses an already-completed contract (avoid LLM quota, pipeline failure and the 3-4 minute wait), via laptop + ngrok free dev domain, with localhost and a screen recording as backups. Never-cut features: auth, upload, tracker, results page, landing page, canned-answer help bot (no LLM).

---

**End of Handover 6**
