# ScanTract Project Handover #2

**Date:** 11 October 2026  
**Handover Recipient:** New Development Team  
**Status:** 27 commits ahead of origin/main

---

## 1. PROJECT AND DEADLINE

**Demo Date:** 12 October 2026  
**Feature Freeze:** 11 October 2026, 12:00 PM  
**Critical Path:** Landing page with animations, help bot, professional polish

**Current Commit:** `61fc20f fix(frontend): clearer login error handling`  
**Ahead of origin:** 27 commits

---

## 2. ARCHITECTURE AND PORTS

### Services
- **Backend (FastAPI):** Port 8000, container `scantract-backend`
- **Frontend (Nginx):** Port 3000, container `scantract-frontend`
- **Database (PostgreSQL + pgvector):** Port 5432, container `scantract-db`
- **Vite Dev Server:** Port 5173 (NOT RUNNING - manual start required)

### Container Status (Verified)
```
scantract-backend   Up 10 minutes   0.0.0.0:8000->8000/tcp
scantract-db        Up 10 minutes   0.0.0.0:5432->5432/tcp (healthy)
scantract-frontend  Up 10 minutes   0.0.0.0:3000->80/tcp
```

### Architecture
```
Browser (5173/3000) → Nginx/Vite proxy → FastAPI (8000) → PostgreSQL (5432)
                              ↓
                        pgvector embeddings
                              ↓
                    Gemini API (embeddings)
                    OpenRouter API (LLM)
```

---

## 3. VERIFIED STATE

### Backend Tests
- **Total tests collected:** 289
- **Command:** `python -m pytest tests --ignore=tests/integration -q`
- **Status:** Collection successful
- **Note:** Actual test run NOT performed in this session

### Frontend Tests
- **Test files:** 25 passed
- **Tests:** 171 passed, 6 skipped (177 total)
- **Build:** Exit code 0 (successful)
- **Command:** `npm run test -- --run`

### Git State
- **Branch:** main
- **Ahead of origin/main:** 27 commits
- **Modified files:** 5 uncommitted changes
- **Stash:** 1 stashed change (WIP on commit 15b4a3d)

### Database State (Verified)
- **Users:** 27 total
- **Test users (test+/live_):** 23
- **Contracts:** 8 completed, 10 failed
- **Sample contracts:** 4 (ids: 1, 44, 46, 47)
- **Alembic version:** NOT VERIFIED (query not run)

### Recent Commits (Last 10)
```
61fc20f fix(frontend): clearer login error handling
f3c5ac0 feat(frontend): settings, delete my data, retry and delete contracts
edabea1 chore(backend): live check for management routes
9e8ef4b feat(backend): delete, retry, delete-my-data, upload cap, stats
ed731d6 feat(frontend): dashboard and my contracts with real data
605778d fix(frontend): navigation routes each tab to its own page
d68d1ad feat(frontend): results page hardened, why-flagged panel
116e75d feat(frontend): results page with risk ring, filters, findings
52f70c2 test(frontend): quarantine 6 broken upload/polling tests
38c91b4 test(frontend): upload page tests, polling tests restored
```


---

## 4. WORKING RULES (from .kiro/steering/working-rules.md)

### Evidence & Output (CRITICAL)
- **Every claim must cite the raw command output that proves it**
- If you did NOT run a check for that specific claim, write "NOT CHECKED"
- Do not infer, remember, or generalize
- Never generalize from one check
- Don't say "should work" — show what actually happened
- No secrets in output (file names and variable names only)
- **NEVER open, cat, or Read .env / .env.docker, and never print any key**
- Inspect secrets only via masked output (length, last 4 chars, booleans)

### Testing (NO LOOSENING)
- **Never loosen, skip, delete, or xfail a test to get a pass**
- Show the failure, then fix the real cause
- Paste the failure first, then fix
- No guessing where a command can settle it
- Tests must never upload contracts or hit live API without mocks
- **A fix only counts after a genuine rebuild/recreate (no docker cp live patches) and a rerun of the real check**

### Git & Deployment
- **Never run `git push` under any circumstances**
- Commit after each small task
- One commit per logical change

### LLM & External Calls
- **Make NO LLM completion calls (zero OpenRouter/Gemini quota spent)**
- No LLM calls during development/testing
- Don't call `/api/contracts/2/report` or `/api/contracts/3/report` until explicitly approved
- Contract processing only via orchestrator pipeline

### Data Types & Dependencies
- `contract_id` and `clause_id` are INTEGER (not UUID)
- `risk_findings.id` is UUID
- Gemini is a hard dependency for embeddings (cannot be optional)

### Docker & Build Commands
- Pipe `docker compose build/up` output through `Select-Object -Last 25`
- No multi-statement `python -c` in PowerShell: write script files in `backend/scripts/` and `docker cp` them in

### Secrets & Sensitive Files (STRICT MASKING)
- **Never print added lines of a diff, or any line, from a file that may hold secrets (.env*, *.example)**
- Use masked scripts only (line number, variable name, length, last 4)
- No raw diff output for .env.example or similar files

### Database Testing (SCRATCH ONLY)
- **Never run pytest or any script against the demo DB (scantract)**
- **Use the scratch DB scantract_scratch for all tests**
- Demo DB is production-like, scratch DB is disposable

### Git Safety (Write Operations)
- **NEVER run git reset --hard, git revert, git clean, or git checkout/restore on a whole tree or on files you did not just edit**
- **Allowed git write commands:** `git add <explicit paths>`, `git commit`, and `git checkout <commit> -- <one named path>` for a mutation proof only
- **Mutation proof workflow:** checkout old version, test (expect failures), checkout target version, verify diff is empty, test (expect pass)

### PowerShell Search (RECURSIVE)
- **PowerShell 5 does not treat ** as recursive**
- Search with `Get-ChildItem -Recurse -Include <pattern> | Select-String`
- **Do not claim "no matches" from a truncated or non-recursive search**

---

## 5. API REFERENCE

### Backend Routes (Verified)

**Auth Routes (auth.py):**
- `POST /api/auth/register` - Create new user
- `POST /api/auth/login` - Authenticate user
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password with token

**Contract Routes (contracts.py):**
- `POST /api/contracts/upload` - Upload contract file
- `GET /api/contracts/list` - List all contracts (own + samples)
- `GET /api/contracts/{id}` - Get contract metadata
- `DELETE /api/contracts/{id}` - Delete contract (owner only, not samples, not processing)
- `POST /api/contracts/{id}/retry` - Retry failed contract (returns 202, only for failed contracts)
- `GET /api/contracts/stats` - Get contract counts by status (excludes samples)

**Report Routes (reports.py):**
- `GET /api/contracts/{id}/report` - Get full analysis report
- `GET /api/contracts/{id}/report/pdf` - Download PDF report

**Pipeline Routes (pipeline.py):**
- `POST /api/contracts/{id}/classify` - Manual classification trigger

**User Data Routes (auth.py):**
- `DELETE /api/auth/me/data` - Delete all user data (contracts + account)

### API Response Envelopes

**Standard Envelope:**
```json
{
  "success": true|false,
  "data": {...},
  "error": "error message" | null
}
```

**Upload Response:**
```json
{
  "contract_id": 123,
  "status": "uploaded",
  "message": "Contract uploaded successfully"
}
```

**Report Structure:**
```json
{
  "all_clauses": [...],
  "risky_clauses": [...],
  "missing_clauses": [...],
  "risk_summary": {
    "overall_risk_level": "high|medium|low|none",
    "total_clauses": 45,
    "risky_count": 3,
    "missing_count": 2
  }
}
```

### Important API Details
- **Upload Limit:** MAX_UPLOADS_PER_DAY (default 3 in last 24h)
- **No per-contract status endpoint:** Use `GET /api/contracts/list` to poll
- **finding_id:** Risk findings use UUID, not INTEGER
- **Sample contracts:** Cannot be deleted or modified
- **Ownership:** All mutations check owner, return 404 for non-owner

---

## 6. FRONTEND MAP

### Pages (frontend/src/pages)
- **auth/**: LoginPage, SignupPage, ForgotPasswordPage, ResetPasswordPage
- **DashboardPage:** Overview with stats and recent contracts
- **UploadPage:** File upload with drag-drop and polling tracker
- **ContractsPage:** List view with My Contracts and Samples tabs
- **ReportView:** Full analysis results with risk ring, filters, findings
- **SettingsPage:** Account, appearance, privacy, delete my data
- **NotFoundPage:** 404 error page

### Components (frontend/src/components)
- **ui/**: Button, Input, Card, Modal, Badge, Skeleton, EmptyState, ErrorState, ThemeToggle, Logo, PasswordStrength, PageTransition
- **AppShell:** Layout wrapper with sidebar and header
- **RiskRing:** Circular risk visualization
- **WhyFlaggedPanel:** Explanation drawer for findings

### Library (frontend/src/lib)
- **api.ts:** API client with auth and error handling
- **types.ts:** TypeScript interfaces for API contracts
- **risk.ts:** Risk calculation utilities
- **severity.ts:** Severity level helpers

### Routing (frontend/src/App.tsx)
```
/ → LoginPage (redirect to /dashboard if authenticated)
/login → LoginPage
/signup → SignupPage
/forgot-password → ForgotPasswordPage
/reset-password → ResetPasswordPage
/dashboard → DashboardPage (protected)
/upload → UploadPage (protected)
/contracts → ContractsPage (protected)
/contracts/:id → ReportView (protected)
/settings → SettingsPage (protected)
* → NotFoundPage
```

### Design Tokens
- **Colors:** Primary gradient (blue), text (3 levels), surface, border
- **Theme:** Light/dark mode via localStorage
- **Typography:** System font stack with fallbacks
- **Animations:** Framer Motion for page transitions, modals, cards


---

## 7. KNOWN GAPS AND ISSUES

### Quarantined Tests (Commit 52f70c2)
- **6 tests quarantined** in commit "test(frontend): quarantine 6 broken upload/polling tests, suite green"
- Files affected: `usePipelinePolling.test.ts`, `UploadPage.test.tsx`
- Reason: Upload/polling integration tests broken
- Status: Suite is green with these tests disabled

### Mutation Proof Gaps
- **is_sample delete guard:** NOT mutation-proven
- No proof that samples are protected from deletion at code level

### Unverified Features
- **Retry button:** Never run live through UI (backend endpoint exists, frontend has button)
- **Upload cap (MAX_UPLOADS_PER_DAY):** Never tested with real user hitting limit
- **Real-backend report e2e:** Results page never viewed in real browser with live data
- **PDF generation:** Tested only in Docker, not on Windows host

### Login Bug Status (L1)
- **Issue:** "An unexpected error occurred" on network failure
- **Fix commit:** 61fc20f "fix(frontend): clearer login error handling"
- **Status:** FIXED - now shows "Cannot reach the server. Please check your connection."
- **Test added:** Network error message test passes

### Playwright Issues
- **Playwright via Kiro hangs** on Windows
- **Workaround:** Use manual browser checks for e2e verification
- Integration tests disabled (tests/integration folder ignored)

### Configuration Issues
- **Demo reset link:** Hardcodes `localhost:3000` in `backend/app/api/routes/auth.py`
- **Problem:** Won't work in production/cloud deployment
- **Fix needed:** Use configurable PUBLIC_URL env var

### Database Pollution
- **Test users:** 23 users with `test+` or `live_` prefixes in production DB
- **Action needed:** Delete after backup
- **Command:** NOT RUN - needs manual cleanup

### Untracked Scripts
- **Many scripts in backend/scripts/** are untracked
- **Do not stage these** without review
- Examples: auth_live_check.py, check_key.py, etc.

### OpenRouter Quota
- **Daily limit:** ~50 requests/day (free tier)
- **Practical limit:** ~2 live uploads/day
- **Reliability:** Quota tracking unreliable, monitor failures

---

## 8. REMAINING WORK (Priority Order)

### CRITICAL (Feature Freeze 11 Oct 12:00)

1. **L1 Login Error Fix** ✓ COMPLETE (commit 61fc20f)

2. **P1 Professional Polish**
   - Motion animations (page transitions, cards)
   - Empty states for all pages
   - Header/sidebar refinements
   - Loading skeletons

3. **Landing Page WITH Animations** ⚠️ CRITICAL
   - Hero section with gradient
   - Animated scanning contract window
   - Pipeline steps visualization
   - Features showcase
   - Demo section
   - FAQ accordion

4. **Help Bot** ⚠️ CRITICAL
   - Canned answers only (no LLM)
   - Common questions (How to upload, What do risk levels mean, etc.)
   - Floating chat button
   - Drawer interface

5. **Static Legal Pages**
   - Privacy Policy
   - Terms of Service
   - Legal Disclaimer (no legal advice warning)

### DEPLOYMENT

6. **Frontend Docker Rebuild Proof**
   - Vite 8 on node:20-alpine
   - Nginx /api proxy configuration
   - Build test in container

7. **Demo Reset Link Fix**
   - Replace `localhost:3000` with PUBLIC_URL env var
   - Test with production URL

8. **Cloudflare Quick Tunnel Deploy**
   - Set up tunnel
   - Configure domain
   - Test end-to-end

### DOCUMENTATION

9. **README**
   - Setup instructions
   - Environment variables
   - Development workflow
   - Deployment guide

10. **Fresh-Clone Docker Compose Test**
    - Clone repo on clean machine
    - Run `docker compose up`
    - Verify all services start

### CLEANUP

11. **Delete Test Users**
    - Backup database first
    - Delete users with `test+` or `live_` prefixes (23 users)
    - Verify integrity

12. **Scan Secrets**
    - Run `python backend/scripts/scan_secrets.py`
    - Run `git grep -lE "sk-or-v1-[0-9a-f]{20,}|AIza[0-9A-Za-z_-]{20,}"`
    - Fix any leaks

13. **Push to GitHub**
    - `git push --dry-run` first
    - Then `git push origin main`

### USER DELIVERABLES

14. **User's Own Work**
    - Project report
    - Presentation slides
    - Recorded backup demo video
    - Rehearsal with team

---

## 9. CONSTRAINTS AND POLICIES

### API Quotas
- **OpenRouter:** ~50 requests/day free tier
- **Gemini:** Embeddings quota (NOT VERIFIED)
- **Practical upload limit:** 2 contracts/day to preserve quota for demo

### Security Policies
- **NEVER print API keys** in logs or output
- **NEVER commit .env files** to git
- **Secrets inspection:** Only via masked scripts (length, last 4 chars)
- **Key rotation:** Edit .env manually, then `docker compose up -d --force-recreate backend`
- **Key rotation timing:** Only when NO contract is processing

### Database Policies
- **Production DB:** scantract (never run tests against this)
- **Test DB:** scantract_scratch (disposable, for pytest only)
- **Backups:** Always backup before migrations or major changes

### Testing Policies
- **Backend tests:** `python -m pytest tests --ignore=tests/integration`
- **NEVER run:** `tests/integration` folder (uploads real files, spends LLM quota)
- **NEVER run:** bare `pytest` (includes integration tests)
- **Frontend tests:** `npm test -- --run` (all tests are safe)

### Windows Quirks
1. **Docker Desktop must be running** before any docker commands
2. **PDF generation works only in Docker** (not on Windows host)
3. **No multi-line `python -c`** in PowerShell (syntax breaks)
4. **No `>` redirects** to create files (UTF-16 corruption)
5. **Use .sql files:** `docker cp` + `psql -f` instead of heredocs

### Cut Priority (If Time Runs Out)
**NEVER CUT:**
- Auth (login, signup, password reset)
- Upload page
- Contract tracker/polling
- Results page with findings
- Landing page with animations
- Help bot

**CUT FIRST (in this order):**
1. Notifications panel
2. Feedback thumbs (like/dislike on findings)
3. Extra charts and visualizations
4. Advanced filters
5. Export options beyond PDF

---

## UNVERIFIED ITEMS

The following items could NOT be verified in this session:

### Backend Tests
- **Actual test run:** Tests were collected (289 tests) but NOT executed
- **Reason:** Only ran `--collect-only`, not actual pytest run
- **Command needed:** `python -m pytest tests --ignore=tests/integration`

### Alembic Version
- **Current version:** NOT VERIFIED
- **Expected:** 010_add_sample_contracts_flag
- **Reason:** SQL query not run
- **Command needed:** `SELECT version_num FROM alembic_version;`

### Database Hashes
- **Baseline hashes:** NOT VERIFIED
- **contract_id=1 md5:** NOT VERIFIED
- **Known-good:** 6adf9b01e1a4557703c818e5d5cf3b75
- **Reason:** db_hashes.sh not executed

### Environment Variables
- **backend/.env.example contents:** NOT READ (policy violation to print)
- **docker-compose.yml env sections:** NOT EXTRACTED
- **Reason:** Secrets policy forbids reading .env files

### Key Status Check
- **OpenRouter/Gemini quota:** NOT VERIFIED
- **Command not run:** `docker exec scantract-backend python /app/scripts/check_key.py`
- **Reason:** Time constraint

### Frontend Skipped Tests
- **6 skipped tests detected:** Cause NOT DETERMINED
- **Reason:** No skip markers found in code (it.skip, describe.skip, test.skip)
- **Hypothesis:** Tests may be conditionally skipped at runtime

### Real User Workflows
- **Upload through UI:** NOT TESTED in this session
- **Report viewing in browser:** NOT TESTED
- **Delete/Retry buttons:** NOT TESTED
- **Settings delete-my-data:** NOT TESTED
- **Reason:** All manual UI testing

### Vite Dev Server
- **Port 5173:** NOT LISTENING (vite not started)
- **Frontend development:** Must start manually with `npm run dev`

---

**Generated:** 11 October 2026  
**Verified By:** Assistant via command-line evidence only  
**Next Update:** Before production deployment
