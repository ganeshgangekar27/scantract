# ScanTract Handover 9
**Date:** 7 November 2026  
**Status:** Hosting-ready, friendly error messages, honest forgot-password page

---

## 1. What ScanTract Is and How to Run It

ScanTract is an AI-powered contract risk analyzer that identifies risky clauses and missing terms in rental and freelance contracts using Indian legal norms, without giving legal advice. This is a final-year engineering project. The system processes uploaded PDFs/DOCX files through a multi-stage pipeline: document extraction, normalization, clause segmentation, LLM classification, dual RAG retrieval (legal rules knowledge base + reference contract corpus), risk detection, explanation generation, structured report.

**How to Run Locally:**

Command: `docker compose up` from workspace root

Services and Ports:
- Backend (FastAPI): http://localhost:8000 (API docs at /docs)
- Frontend (React+Vite dev): http://localhost:5173
- Frontend (Nginx prod): http://localhost:3000  
- PostgreSQL + pgvector: localhost:5432

Database names:
- Production/demo: `scantract` (main working database)
- Test: `scantract_test` (tests use this via backend/tests/db_config.py)
- Scratch: `scantract_scratch` (exists but tests use scantract_test)

---

## 2. Read-First Note

HANDOVER_8 sections 1-6 and 9 (architecture, routes, env names) are still valid.

HANDOVER_8 state sections 7, 8, 10, 14-20, 25, 26 are STALE and superseded by this file.

---

## 3. Verified State

### Git Status
VERIFIED `git --no-pager status -sb --untracked-files=no`:
```
## main...origin/main
 M HANDOVER.md
```

Only HANDOVER.md in root is modified. No other tracked files are uncommitted.

### Recent Commits
VERIFIED `git --no-pager log --oneline -15`:
```
ce264a1 (HEAD -> main) fix(backend): friendly, path-free error message for processing failures
702f4cd fix(backend): clear 409 on retry when uploaded file is gone
2c52f9f feat(frontend): honest forgot-password page when reset is disabled
915707e feat(frontend): vercel SPA fallback rewrite
297693b chore(backend): remove unused paddleocr dependencies
5c27f44 feat(backend): PORT-aware start command with migrations and seeds
2dbb101 feat(backend): no reset link in non-demo mode
0e49599 feat(backend): managed-Postgres URL handling for asyncpg and alembic
bbf8178 feat(backend): read CORS origins from CORS_ORIGINS env var
b4c8193 test(frontend): update landing page test for footer
084093d feat(frontend): restyle signup page to match login
f543a8a feat(frontend): remove sample-data caption from landing demo
261d021 feat(frontend): remove disclaimer and sample-data text from landing page
076b05f feat(frontend): footer copyright line, remove tagline
68ebf6e fix(frontend): password input padding and icon size, default light theme
```

### Hosting Files Tracked
VERIFIED `git ls-files`:
- frontend/vercel.json (tracked)
- frontend/src/vite-env.d.ts (tracked)
- backend/db_url_utils.py (tracked)
- backend/tests/test_processor_error_handling.py (tracked)
- backend/tests/test_reset_link_mode.py (tracked)
- backend/tests/test_cors_origins.py (tracked)
- backend/tests/test_db_url_utils.py (tracked)

### Sample Data Scripts
VERIFIED `Test-Path`:
- backend\scripts\h8_samples_data.sql: True
- backend\scripts\h8_samples_setval.sql: True

### Container Status
VERIFIED `docker compose ps`:
```
scantract-backend    Up 3 minutes    0.0.0.0:8000->8000/tcp
scantract-db         Up 3 minutes    0.0.0.0:5432->5432/tcp (healthy)
scantract-frontend   Up 3 minutes    0.0.0.0:3000->80/tcp
```

All three containers running.

### Frontend Bundle
VERIFIED `docker exec scantract-frontend sh -c "ls /usr/share/nginx/html/assets | grep -E '^index-.*\.js$'"`:
```
index-DajiUTk0.js
```

Production bundle present.

### Database Counts
VERIFIED `docker exec scantract-db psql -U postgres -d scantract -f /tmp/h9_facts.sql`:
```
 contracts | users | clauses | findings 
-----------+-------+---------+----------
        22 |     3 |     226 |      129
(1 row)
```

### Sample Contract IDs
VERIFIED same SQL query:
```
 id | is_sample | processing_status 
----+-----------+-------------------
  1 | t         | completed
 44 | t         | completed
 46 | t         | completed
 47 | t         | completed
(4 rows)
```

Four sample contracts: ids 1, 44, 46, 47. All processing_status is completed.

### Backend Environment Variable Names
VERIFIED `Get-Content docker-compose.yml -TotalCount 100`:

Under backend environment block:
- DATABASE_URL
- LLM_PROVIDER
- LLM_BASE_URL
- OPENAI_API_KEY
- CLAUDE_API_KEY
- GEMINI_API_KEY
- OPENAI_MODEL
- CLAUDE_MODEL
- GEMINI_MODEL
- EMBEDDING_MODEL
- EMBEDDING_DIMENSIONS
- UPLOAD_TEMP_DIR
- MAX_UPLOAD_SIZE_MB
- MAX_UPLOADS_PER_DAY
- MAX_CONTEXT_TOKENS
- DEDUPLICATION_THRESHOLD
- MIN_CHUNKS_PER_SOURCE
- LLM_CONCURRENCY_LIMIT
- LLM_MAX_RETRIES
- LLM_TIMEOUT_SECONDS
- LOG_LEVEL
- JWT_SECRET
- RESET_LINK_MODE
- CORS_ORIGINS

### Backend Test Results
VERIFIED `python -m pytest tests --ignore=tests/integration -q` from backend/:
```
336 passed, 261 warnings in 41.72s
```

Full backend test suite: 336 passed, 0 failed.

### Frontend Test Results
VERIFIED `npx vitest run` from frontend/:
```
Test Files  31 passed (31)
Tests  271 passed | 6 skipped (277)
```

Full frontend test suite: 31 files, 271 passed, 6 skipped, 0 failed.

---

## 4. What Changed Since H8

### Commits Since H8 (VERIFIED)
From git log output:
- ce264a1: friendly, path-free error message for processing failures
- 702f4cd: clear 409 on retry when uploaded file is gone
- 2c52f9f: honest forgot-password page when reset is disabled
- 915707e: vercel SPA fallback rewrite
- 297693b: remove unused paddleocr dependencies
- 5c27f44: PORT-aware start command with migrations and seeds
- 2dbb101: no reset link in non-demo mode
- 0e49599: managed-Postgres URL handling for asyncpg and alembic
- bbf8178: read CORS origins from CORS_ORIGINS env var
- b4c8193: update landing page test for footer
- 084093d: restyle signup page to match login
- f543a8a: remove sample-data caption from landing demo
- 261d021: remove disclaimer and sample-data text from landing page

### Features and Fixes (OWNER-STATED)

Frontend:
- Signup page restyled to match login page
- Landing page disclaimer and sample-data caption removed
- frontend/vercel.json added with SPA fallback rewrite rule
- Forgot Password page shows honest "Password reset unavailable" message when VITE_RESET_DISABLED=true (build-time env var, unset locally)
- frontend/src/vite-env.d.ts declares VITE_API_BASE_URL and VITE_RESET_DISABLED

Backend:
- CORS_ORIGINS env var: comma-separated list of allowed origins (wildcard * is ignored)
- DATABASE_URL conversion for asyncpg and alembic with Neon-style params (backend/db_url_utils.py, is_pooler_url function detects -pooler- substring)
- RESET_LINK_MODE: when set to value other than "demo", /auth/forgot-password returns no reset link (response_model_exclude_none=True)
- Dockerfile CMD: runs alembic upgrade head, both seed scripts (legal_kb, reference_corpus), then uvicorn on ${PORT:-8000}. docker-compose command overrides it locally.
- Unused paddleocr and paddlepaddle removed from requirements.txt (Docker image reduced from 2.54GB to 1.18GB)
- Migrations proven on empty scratch database (head revision 010, pgvector extension created by first migration)
- Retry route returns HTTP 409 with clear message "The original file is no longer available. Please upload the contract again." when the uploaded file is gone
- processor.py stores friendly_error(e) instead of raw exception text
- friendly_error function redacts file paths (Unix /path/to/file and Windows C:\path\to\file patterns replaced with [path redacted])

Tests:
- backend/tests/test_cors_origins.py (CORS validation)
- backend/tests/test_db_url_utils.py (DATABASE_URL conversion)
- backend/tests/test_reset_link_mode.py (no reset link in non-demo mode)
- backend/tests/test_processor_error_handling.py (missing file produces friendly error without server paths)
- frontend: ForgotPasswordPage.test.tsx covers VITE_RESET_DISABLED=true case

---

## 5. Hosting Decision and Plan

### Chosen Hosting (OWNER-STATED)

- Backend: Render (Docker, root backend/)
- Database: Neon (Postgres with pgvector)
- Frontend: Vercel (root frontend/)

Visitors CAN upload new contracts.

### Hosting Facts Checked on Vendor Pages in Nov 2026 (OWNER-STATED)

Render free web service:
- 512 MB RAM
- 0.1 CPU
- Spins down after 15 min idle, about 1 min to wake
- Ephemeral filesystem
- 750 free instance hours per workspace
- Starter plan $7 removes sleep

Neon free tier:
- 0.5 GB per project
- 100 CU-hours
- Scale to zero after 5 min idle

Use Neon's DIRECT (non-pooler) connection string.

Local DB is about 10 MB.

### Environment Variables to Set (OWNER-STATED)

Render backend env vars (names only, values copied by owner from their own .env):
- DATABASE_URL
- JWT_SECRET (new, must generate)
- GEMINI_API_KEY
- OPENAI_API_KEY
- LLM_PROVIDER
- LLM_BASE_URL
- OPENAI_MODEL
- RESET_LINK_MODE=off
- CORS_ORIGINS (the Vercel URL)
- EMBEDDING_DIMENSIONS=3072
- All other names listed in docker-compose.yml backend environment block

Vercel frontend env vars:
- VITE_API_BASE_URL (the Render URL)
- VITE_RESET_DISABLED=true

No value is ever pasted into chat or Kiro. Owner copies values by hand into host dashboards.

### Sample Data Plan (OWNER-STATED)

Only contract id 47 (rental demo, 9 clauses, 13 risk findings) goes to Neon.

Steps:
1. Run backend\scripts\h8_samples_data.sql (resets both sequences to 1)
2. Run backend\scripts\h8_samples_setval.sql (moves sequences to 47 and 99 so next ids are 48 and 100)

Must run IN THAT ORDER.

The legal_rules (20) and reference_clauses (28) are not copied. The Render start command seeds them on first boot (Gemini embedding calls).

### Risks (OWNER-STATED)

- Slow first boot on 0.1 CPU
- Render and Neon cold starts (15 min and 5 min idle thresholds)
- Free OpenRouter key allows about 2 live uploads per day for ALL visitors combined (global daily cap proposed, owner has not decided)
- Scanned PDFs have no OCR

---

## 6. Remaining Work

Steps in order (OWNER-STATED):

1. Owner commits HOST-9C files (processor.py, error_handling.py, test_processor_error_handling.py) by explicit path if not already committed.

2. Owner creates Neon project and imports the two sample files (owner runs psql with their own connection string).

3. Owner creates Render web service and sets env vars.

4. Owner creates Vercel project and sets its two env vars, then adds the Vercel URL to CORS_ORIGINS on Render.

5. Smoke test on live URLs:
   - /health
   - Sign up
   - Log in
   - Open the sample report
   - PDF download
   - One upload
   - Check in browser F12 Network that /api calls go to the Render URL

6. Fix the missing space in contracts.py retry detail text "havefailed" after checking that no test asserts it.

7. Decide the global daily upload cap.

8. Update this handover, README hosting notes and live URL, commit docs by explicit path.

Optional:
- Fresh-clone test
- Demo video
- Restore api.test.ts from commit 61fc20f
- Tracker polish
- pdf_generator unit test

After deadline:
- LICENSE
- Research paper

---

## 7. Working Rules and Kiro Habits

### Claude and Kiro Workflow (OWNER-STATED)

Claude writes Kiro prompts only (tagged [BACKEND] or [FRONTEND]), one at a time, at most one question per reply. The owner pastes raw Kiro output. Claude separates PROVEN from claimed.

Every Kiro prompt structure:
- Starts with reading working-rules.md
- "Ignore any earlier summary"
- PREFLIGHT docker info
- Ends with FINAL block

### Kiro Habits Seen (OWNER-STATED)

Issues observed:
- Says "nothing went wrong" when something did
- Retyped "RAW OUTPUT" blocks differ from the real tool output
- Marks code review as PROVEN
- Invents numbers
- Replays old summaries after a context reset
- Goes beyond the prompt (check diffs)
- Empty output is not proof (always use a control)

### Tooling Facts (OWNER-STATED)

PowerShell:
- Select-Object is blocked
- Get-Content has no -Skip parameter
- Use -TotalCount or -Tail, or use the file reader tool
- Paste one PowerShell command block at a time

SQL:
- Only via .sql file, docker cp, psql -f

Testing:
- Backend pytest needs Docker Desktop running (otherwise INTERNALERROR)
- Frontend tests can time out when the machine is busy, rerun alone when quiet

Git:
- Kiro never commits or pushes
- Owner commits after `python backend\scripts\scan_secrets.py` shows 0 secrets
- Staging: explicit paths only

---

## 8. Never Stage These Files

OWNER-STATED list, never stage:
- HANDOVER.md in the repo root
- Every untracked file in backend/scripts (probe scripts, .sql, .txt, .sh, .pdf)
- frontend/e2e screenshot specs
- frontend/*.txt
- frontend/scripts/
- Backups in C:\Users\USER\scantract_backups
- .env files

---

## End of Handover 9
