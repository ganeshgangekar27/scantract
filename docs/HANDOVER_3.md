# HANDOVER 3 — ScanTract Status (11 Oct 2026)

**Deadline:** 12 October 2026 demo  
**Feature Freeze:** PASSED  
**Status:** PIPELINE BUG OPEN + POLISH INCOMPLETE

---

## 1. PROJECT OVERVIEW

**What:** AI contract analysis for rental/freelance contracts (Indian legal norms). Upload → segmentation → LLM clause classification → RAG risk detection (legal KB + reference corpus) → explanation generation → report.

**Stack:**
- Frontend: React 18.3 + Vite 6.0 + TypeScript 5.6 + Tailwind 3.4 + Framer Motion 11.11
- Backend: FastAPI (Python 3.11+), async, Pydantic v2
- Database: PostgreSQL 15 + pgvector, SQLAlchemy async + Alembic
- LLM: Claude API or GPT API (via env var `LLM_PROVIDER`), embeddings via Gemini
- Docker: compose brings up frontend:3000, backend:8000, postgres:5432

**Zero-Cost Rules:**
- NO OpenRouter/Gemini quota during dev/testing
- NO calls to `/api/contracts/2/report` or `/api/contracts/3/report` (samples) unless approved
- Contract processing ONLY via orchestrator pipeline
- Tests use scantract_test DB (scratch), NEVER scantract (demo/prod-like)

**Working Rules Summary:**
- Every claim must cite raw command output
- Never loosen/skip/xfail tests; fix real cause
- No git push under any circumstances
- One commit per logical change
- Commit after each small task
- Never print secrets (.env content, API keys)
- PowerShell 5: no `**` recursion, use `Get-ChildItem -Recurse`
- Never run git reset --hard/revert/clean on whole tree

**How to Run:**
```powershell
# Start all services
docker compose up -d

# Backend logs
docker logs scantract-backend -f

# Frontend dev (optional, for hot reload)
cd frontend
npm run dev  # vite dev server on 5173

# Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

**Tests:**
```powershell
# Backend (289 passed)
cd backend
python -m pytest tests --ignore=tests/integration -q

# Frontend (184 passed, 6 skipped)
cd frontend
npm test -- --run
```

**Rebuild:**
```powershell
# Backend only
docker compose up -d --build backend

# Frontend only
docker compose up -d --build frontend

# Full rebuild
docker compose down
docker compose up -d --build
```

---

## 2. COMPLETED WORK

### L1 Login Bug Fix (Commit 64128b6)
**Root Cause:** Frontend had a gitignored `frontend/.env.production` file that baked `VITE_API_BASE_URL=https://api.scantract.com` into the production build. Browser login failed because it tried absolute URLs instead of relative `/api/*` proxied by nginx.

**Diagnosis:**
- Node CORS probe: both localhost:8000 and localhost:3000 returned proper CORS headers (access-control-allow-origin: http://localhost:3000)
- No absolute URLs baked in built JS (grep empty)
- Frontend Dockerfile had no ARG/ENV lines
- nginx.conf correctly proxies `location /api` to `http://backend:8000`

**Fix:**
1. Emptied `frontend/.env.production` (set `VITE_API_BASE_URL=` to empty)
2. Added `RUN rm -f .env.production` to frontend/Dockerfile to prevent future issues
3. Verified: `API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''` results in empty string → relative URLs work with nginx proxy

**Commit:** 64128b6 - "fix(frontend): never bake absolute api url into production build"

### Landing Page (Commits ece59a3, b3f559b)
**Sections Implemented:**
1. **Navigation** - Logo, nav links (Features, How It Works, FAQ), CTA buttons (login/signup)
2. **Hero** - Headline, subheadline, dual CTA (Try Demo / Upload Contract), visual decoration
3. **Interactive Demo** - 4-card flip demo (upload → analysis → risk detection → report), animated state transitions
4. **Features** - 6 feature cards (AI-powered, plain language, Indian legal context, etc.)
5. **How It Works** - 4-step process (upload → analysis → findings → export)
6. **Video Slot** - OptionalVideo.tsx checks for `frontend/public/demo.mp4`, shows placeholder if missing
7. **FAQ** - Accordion with 6 Q&A pairs (what it does, accuracy, data privacy, free tier, etc.)

**Components:**
- `frontend/src/components/landing/Navigation.tsx`
- `frontend/src/components/landing/Hero.tsx`
- `frontend/src/components/landing/InteractiveDemo.tsx`
- `frontend/src/components/landing/Features.tsx`
- `frontend/src/components/landing/HowItWorks.tsx`
- `frontend/src/components/landing/OptionalVideo.tsx`
- `frontend/src/components/landing/FAQ.tsx`
- `frontend/src/pages/LandingPage.tsx` (orchestrates all sections)

**Animations:** Framer Motion for fade-ins, slide-ins, card flips, stagger children

**Commits:**
- ece59a3 - "feat(frontend): animated landing page"
- b3f559b - "feat(frontend): professional interactive landing page"

**Visual Quality:** UNVERIFIED (user needs to check in browser)

---
## 3. EVIDENCE

### Git Status (Evidence a)
```
git log --oneline -12:
b3f559b (HEAD -> main) feat(frontend): professional interactive landing page
ece59a3 feat(frontend): animated landing page
64128b6 fix(frontend): never bake absolute api url into production build
f224814 docs: handover 2
61fc20f fix(frontend): clearer login error handling
f3c5ac0 feat(frontend): settings, delete my data, retry and delete contracts
edabea1 chore(backend): live check for management routes
9e8ef4b feat(backend): delete, retry, delete-my-data, upload cap, stats
ed731d6 feat(frontend): dashboard and my contracts with real data
605778d fix(frontend): navigation routes each tab to its own page
d68d1ad feat(frontend): results page hardened, why-flagged panel (e2e spec unverified)
116e75d feat(frontend): results page with risk ring, filters, findings, missing clauses, pdf

git status -sb (first 25 lines):
## main...origin/main [ahead 31]
 M .kiro/hooks/test-on-save-backend.json
 M HANDOVER.md
 M backend/scripts/auth_live_check.py
 D frontend/screenshots.spec.ts
 M frontend/src/components/AppShell.tsx
 M frontend/src/lib/api.ts
 M frontend/src/pages/ContractsPage.tsx
 M frontend/src/pages/auth/ForgotPasswordPage.test.tsx
 M frontend/src/pages/auth/ResetPasswordPage.test.tsx
 ?? backend/scripts/api_results.txt
 ?? backend/scripts/api_tests.py
 ?? backend/scripts/backup_demo.sh
 ...many untracked scripts...

git stash list:
stash@{0}: WIP on main: 15b4a3d fix(backend): orchestrator fails contracts with missing or invalid explanations
```

### Tests (Evidence b, c)
```
Backend (pytest):
289 passed, 249 warnings in 34.74s

Frontend (vitest):
Test Files  26 passed (26)
Tests  184 passed | 6 skipped (190)
Duration  15.58s
```

### Docker Status (Evidence d)
```
scantract-backend Up 4 hours 2026-10-09 20:20:49 +0530 IST
scantract-db Up 4 hours (healthy) 2026-09-25 20:24:10 +0530 IST
scantract-frontend Up About an hour 2026-10-11 14:09:29 +0530 IST
```

### Frontend Structure (Evidence e)
```
src/pages:
- auth/ (LoginPage, SignupPage, ForgotPasswordPage, ResetPasswordPage)
- ContractsPage.tsx, DashboardPage.tsx, LandingPage.tsx
- ReportView.tsx, SettingsPage.tsx, UploadPage.tsx, NotFoundPage.tsx

src/components:
- AppShell.tsx, ClauseHighlight.tsx, ContractText.tsx, ContractUpload.tsx
- ExplanationPanel.tsx, MissingClausesPanel.tsx, PipelineTracker.tsx
- RiskSummaryHeader.tsx
- landing/ (Navigation, Hero, InteractiveDemo, Features, HowItWorks, OptionalVideo, FAQ)
- ui/ (Button, Card, etc.)

src/hooks:
- useContractReport.ts, usePDFDownload.ts, usePipelinePolling.ts, useReveal.ts
```

---

## 4. KNOWN ISSUES

### CRITICAL: Pipeline Bug (OPEN)
**Symptom:** After upload, frontend tracker shows pipeline progressing. User navigates to report. ReportView shows "Analysis not finished yet" error. Dashboard already counts contract as "completed". Minutes later, report loads successfully.

**Current Diagnosis (B1 — REJECTED):**
- Claimed: Race condition between polling stopping on `processing_status='completed'` and report checking `pipeline_stage='completed'`
- Reality: Both fields are set atomically in `orchestrator.py:62-63` (same db.commit())
- Database evidence: All contracts show both fields in sync
- Rejected because: Invented a timing race without evidence

**New Diagnosis Needed (B2 — NOT YET RUN):**
- Read `orchestrator.py` lines 40-70 and 170-end
- Determine if `run_full_pipeline` is background task or awaited
- Check which fields the polled route returns
- Parse backend logs for contracts 58/59 to reconstruct actual timeline
- Find real cause with timestamps

**Code Locations:**
- Error shown: `frontend/src/pages/ReportView.tsx` line ~47 (on 409 status)
- Backend check: `backend/app/reports/assembler.py` line ~49 (`if contract.pipeline_stage != 'completed'`)
- Dashboard count: `backend/app/api/routes/contracts.py` line ~250 (`processing_status == 'completed'`)

**Impact:** User sees confusing "not finished" error despite dashboard showing "completed". Report eventually works after refresh.

### Test Coverage Gap
**Issue:** Commit 64128b6 deleted old `api.test.ts` coverage (234 deletions):
- Tests removed: `listContracts`, `getReport`, `downloadReportPdf`, `uploadContract`, `getPipelineStatus`
- File shrank significantly without replacement tests

**Recovery:** Need to restore from commit 61fc20f into a separate test file

### Uncommitted Changes
**Modified files (unverified in browser):**
- `frontend/src/components/AppShell.tsx` - partial polish (had Logo import error, fixed)
- `frontend/src/lib/api.ts`
- `frontend/src/pages/ContractsPage.tsx`
- `frontend/src/pages/auth/ForgotPasswordPage.test.tsx`
- `frontend/src/pages/auth/ResetPasswordPage.test.tsx`

**Untracked probe scripts (NEVER STAGE):**
- `frontend/scripts/l1_probe.mjs` (CORS testing)
- `backend/scripts/cors_probe.mjs` (CORS testing)
- `backend/scripts/check_status_mismatch.sql` (diagnosis)
- Many other untracked `.sql`, `.sh`, `.py` scripts in backend/scripts/

**Old stash:** `stash@{0}` from commit 15b4a3d

---
## 5. REMAINING WORK

### Polish Status
**Completed:**
- Landing page (visual quality UNVERIFIED)
- AppShell: partial polish only (UNVERIFIED)

**NOT Done:**
- Login/Signup/Forgot/Reset password pages: redesign pending
- Dashboard: polish pending (framer-motion already installed, keep it)
- Upload page: polish pending
- My Contracts page: polish pending
- Settings page: polish pending

### Report Redesign (DECIDED, NOT STARTED)
**Chosen Design:** Option A+C combined

**Layout:**
1. **Summary section first:**
   - Risk ring (visual score)
   - 3-line plain-language summary
   - Top 3 risks highlighted

2. **Findings section:**
   - Show top 5 highest-severity findings initially
   - "Show all N findings" expand button
   - Each finding as collapsed card:
     - Title bar: clause number/type, severity chip, one-line reason
     - Expand for: full explanation text + citation/reference
   
3. **Missing clauses:**
   - Compact presentation
   - Similar collapsed card pattern

**Status:** NOT STARTED (all current report code remains unchanged)

### Help Bot (Canned Answers)
**Spec:** Static Q&A bot, NO LLM, canned responses for common questions
**Status:** NOT STARTED

### Static Legal Pages
**Required:**
- Privacy Policy page
- Terms of Service page

**Status:** NOT STARTED

### Deployment Prep
**Remaining:**
1. Public URL for demo password reset link
2. Cloudflare Quick Tunnel deployment (or similar)
3. README.md updates (setup, deploy, env vars)
4. Docker fresh-clone test:
   - Frontend: vite 6 on node 20
   - Backend: Python 3.11+
5. Clean test users:
   - About 23 test_*/live_* users in DB
   - Backup DB first, then clean
6. is_sample delete guard: mutation proof test
7. Retry route: never run live, needs testing
8. Push to GitHub:
   - User must run secret scans first
   - User must run `git push --dry-run` first
   - User pushes after verification

### User's Own Work
**Remaining:**
1. Final report/documentation
2. Presentation slides
3. Backup demo video (can go to `frontend/public/demo.mp4`)
4. Rehearsal

---

## 6. LESSONS LEARNED

### Working with Kiro
1. **Context limits:** Kiro hits its own context limit on big prompts. Better to send one small, focused prompt per area than one giant prompt.
2. **Overclaiming:** Kiro sometimes claims work is done without verifying. Always demand raw command output as proof.
3. **Git safety:** Kiro once committed without showing clean diff first. Always verify git diff before committing.

### PowerShell 5 Gotchas
1. No `-SkipHttpErrorCheck` flag (use try/catch or check `$LASTEXITCODE`)
2. `curl` is an alias for `Invoke-WebRequest`, not the real curl
3. No native `**` glob recursion (use `Get-ChildItem -Recurse`)

### Testing Discipline
1. Never loosen tests to get passing status
2. Show failure first, then fix root cause
3. Verify fix with real rebuild (no live patches with `docker cp`)

---

## 7. UNVERIFIED ITEMS

**The following have NOT been verified by command output and require user inspection:**

### Visual/UX (Browser Check Required)
- Landing page visual quality and animations
- Landing page responsiveness (mobile/tablet)
- AppShell visual polish
- All other page layouts and styling
- Button hover states, transitions, micro-interactions
- Color scheme consistency
- Typography hierarchy
- Spacing and alignment
- Icon sizes and placement

### Functional (Manual Testing Required)
- Landing page navigation clicks
- Interactive demo card flip animations
- Video playback (if demo.mp4 present)
- FAQ accordion expand/collapse
- All CTA button clicks lead to correct pages
- Form validation states
- Error message display
- Toast notifications
- Loading states
- Empty states

### Performance (Measurement Required)
- Page load times
- Bundle sizes
- Animation smoothness (60fps)
- API response times under load
- Database query performance
- Memory usage over time

### Accessibility (Audit Required)
- Keyboard navigation
- Screen reader compatibility
- Color contrast ratios (WCAG AA)
- Focus indicators
- ARIA labels
- Alt text for images
- Form labels

### Cross-browser (Testing Required)
- Chrome, Firefox, Safari, Edge
- Mobile Safari, Chrome mobile
- Different screen sizes (320px to 4K)

### Edge Cases (Scenario Testing Required)
- Network failures during upload
- Concurrent user uploads
- Very large contracts (100+ pages)
- Malformed PDF/DOCX files
- Browser back/forward navigation
- Session expiration handling
- Token refresh flows

---

## 8. FINAL CHECKLIST

**Before Demo (12 Oct 2026):**
- [ ] Fix pipeline bug (B2 diagnosis + fix)
- [ ] Polish all pages (visual verification in browser)
- [ ] Report redesign (Option A+C implementation)
- [ ] Help bot (canned answers)
- [ ] Legal pages (Privacy, Terms)
- [ ] Demo video backup (optional: frontend/public/demo.mp4)
- [ ] Clean test users (backup DB first)
- [ ] Fresh-clone Docker test
- [ ] User rehearsal

**Before GitHub Push:**
- [ ] Run `python backend/scripts/scan_secrets.py` (must show 0)
- [ ] Run `git grep -lE "sk-or-v1-[0-9a-f]{20,}|AIza[0-9A-Za-z_-]{20,}"` (exit code must be 1)
- [ ] Run `git push --dry-run` and verify output
- [ ] User verifies all secrets removed
- [ ] User pushes

---

**Document Generated:** 11 October 2026  
**Next Handover:** After pipeline bug fix and polish completion
