# ScanTract: product spec and remaining work

Status tags: [DONE] built and committed, [TODO] not built, [CHECK] unknown, verify before relying on it. Deadline: 12 Oct 2026. Feature freeze: 11 Oct 12:00.

## 1. Remaining work: BACKEND

- [DONE] Pipeline (upload, extract, normalize, segment, classify, retrieve, risk detection, explanations), report from DB (409 unless completed), PDF export (Docker only), friendly/redacted errors, auth (register, login, JWT, me, forgot/reset in demo mode), per-user isolation on all contract routes, 273 passing tests, Docker image cleaned.

- [TODO] 11C: ONE live upload proof through Docker (spends about 19 free LLM calls).

- [TODO] 11D-LITE: contracts.is_sample (migration 010), samples readable by everyone (read routes only), mutations stay owner-only, /list returns own contracts then samples with is_sample.

- [TODO] 11E: rebuild backend, migrate real DB to 010, mark contracts 1, 44, 46, 47 as samples, global daily cap on live analyses (about 2/day because of the free quota) with a friendly message.

- [TODO] 11F: retry endpoint for failed contracts, delete contract, delete my data (account + contracts + findings), dashboard stats endpoint (counts, severity totals, recent), optional risk_score field.

- [TODO] 11G (optional): help chatbot endpoint (Gemini) with canned-answer fallback; "Not legal advice" label.

- [CHECK] "Suggested safer wording" per finding: unknown whether the backend produces it; verify in the report JSON before building UI for it.

- [CHECK] Confidence value per finding: verify it exists in the report JSON.

- [TODO] DEPLOY: Cloudflare quick tunnel from the laptop (public https URL), production notes, README, fresh-clone `docker compose up` test, runbook.

- [TODO] Extras if time remains: notifications source data (derive from contract status), usage meter data.

## 2. Remaining work: FRONTEND

- [TODO] A1-FIX: fix failing build (suspected tailwind.config.js syntax error around line 79), tsc `global` errors in tests, commit design system, API/auth layer, routing, app shell (58 vitest passing, 40 old + 18 new).

- [TODO] A2: Login, Signup, Forgot password, Reset password screens + Playwright screenshots (mocked API).

- [TODO] B: Landing page (section 4).

- [TODO] C: Upload page, live Processing tracker, Results/Report page (section 5). The most important screen.

- [TODO] D: Dashboard and My contracts (section 6).

- [TODO] E: Settings, help chatbot, notifications panel, static legal pages, light/dark polish, accessibility sweep, frontend Docker rebuild.

- Existing old components (reuse and restyle, covered by the 40 old tests): ClauseHighlight, ContractText, ContractUpload, ExplanationPanel, MissingClausesPanel, RiskSummaryHeader, useContractReport, usePDFDownload, ReportView.

## 3. Global UI rules

- Look: professional, interactive, attractive. Indigo-to-violet gradient primary (#6366f1 to #8b5cf6), cyan accent (#22d3ee), dark #0b1020 / light #f7f8fc, rounded cards, soft shadows, Inter font (local @fontsource, no CDN).

- Severity colours everywhere: High red, Medium amber, Low/Safe green (single source: src/lib/severity.ts).

- Motion with purpose (framer-motion), all animation disabled under prefers-reduced-motion.

- Every page needs loading skeletons, empty states, error states with retry, toasts (sonner), keyboard focus rings, responsive layout (phone 390px and desktop), light/dark toggle.

- Honest wording: "Information, not legal advice"; never claim 100% accuracy; timestamp on every report; source reference on every finding.

## 4. Landing page (batch B)

Top nav (logo, Why ScanTract, How it works, Features, Try it, FAQ, theme toggle, Log in, Create account, mobile hamburger).

Hero: badge "Built for Indian rental and freelance contracts", headline "Know what you're signing before you sign it.", one-line description, buttons "Analyze a contract" and "Try a live example", trust ticks (PDF and DOCX, Private to your account, Delete anytime), animated contract window that scans a sample rental agreement (clauses light up red/amber/green, risk score counts up to 62/100, tilts with the mouse), three floating cards (High risk, Legal source found, Missing clause), dark background with grid, glowing orbs, shimmering gradient headline.

Then: scrolling clause-type strip (termination, security deposit, rent escalation, lock-in period, notice period, payment terms, IP ownership, liability, confidentiality, late fees, scope of work, dispute resolution; pauses on hover); "Signing blind is expensive" comparison cards (Without vs With ScanTract); "What happens after you upload" six animated steps (Extract, Normalize, Segment, Classify, Retrieve, Explain) with a progress line that fills on scroll; features grid with spotlight hover (risky clause detection, missing clauses, plain language, legal sources, safer wording, private by design); "Try it yourself" interactive demo with Rental/Freelance tabs and three clickable sample clauses showing severity badge, legal reference, confidence bar and suggested wording (static sample data, no API); "Built on a modern stack" badges (FastAPI, React, PostgreSQL + pgvector, Docker; add Gemini only if true); FAQ accordion (legal advice? supported contracts? who can see my documents? how accurate?); final CTA "Read your next contract with confidence"; footer with disclaimer and working links. Sticky frosted navbar, scroll-reveal, before/after slider (optional).

## 5. App pages after login

- Upload: dropzone with PDF/DOCX validation (15 MB max), contract type selector (Rental main, Freelance marked beta), friendly error if the daily AI limit is reached.

- Processing: live pipeline stepper polling the stage (uploaded, classifying, detecting_risks, generating_explanations, completed/failed) with a friendly failure state, the failure reason and a Retry button.

- Results page (the star): risk score ring + summary (risk score computed in the frontend from risk_summary counts), pipeline status strip, highlighted contract text, finding cards (severity, plain-language explanation, legal reference/citation, confidence if available), click-to-link between highlight and finding card with a flash, severity filter chips, missing clauses section, "Why was this flagged?" drawer, copy suggested wording button (only if the backend provides wording), feedback thumbs per finding (optional), Download PDF button, print-friendly view, timestamp, disclaimer.

- My contracts: history with search, filter by status/severity, risk bars, open, retry failed, delete; sample contracts shown with a "Sample" badge.

- Settings and profile: change name/password, privacy note, working "Delete my data" button with confirmation modal.

- Notifications: simple in-app panel derived from contract status changes (no email).

- Static pages: About, Contact, Privacy policy, Terms, Disclaimer (can be one page with tabs).

## 6. Dashboard

Welcome banner with Upload button; stat cards (analyzed, high-risk, medium-risk, safe); risk breakdown donut chart; analyses-over-time chart (optional); recent contracts with risk bars; most common issues (optional); usage meter for daily AI analyses (optional); search bar, theme toggle, avatar menu.

## 7. Help chatbot

Floating chat button on every page; quick-reply chips that change by page; answers about uploading, severity levels, risk score, missing clauses, privacy and reports; "Not legal advice" label. First version uses canned answers in the frontend (no quota); Gemini via a FastAPI endpoint only if time remains.

## 8. Reusable components (in src/components/ui)

Sidebar, top bar, severity badges, clause card, risk ring, filter chips, search bar, dropzone, pipeline stepper, form inputs with inline errors, toasts, modals, drawers, skeletons, empty and error states, theme toggle.


## 9. Trust and quality checklist

Disclaimer on landing, upload and results; privacy note and working Delete my data; source reference on every finding; honest accuracy wording; timestamp on every report; responsive; keyboard focus; contrast; reduced motion.

## 10. Report and demo extras

- Architecture diagram (React, FastAPI, pipeline, PostgreSQL/pgvector, Gemini embeddings, Docker), use case, data flow and ER diagrams.

- Demo flow: sign up, upload, live pipeline, highlighted analysis, flagged reasoning, report/PDF. Backup: sample contracts + a recorded video, because the free LLM quota allows only about 2 live analyses per day.

- Testing summary: backend 273 tests (as of commit ddf5c98), frontend vitest, route-isolation mutation proofs, live auth 16/16 checks; bugs fixed (clause numbering, token limit, JSON-wrapped explanations, incomplete explanations marked completed, report calling the LLM, tests polluting the demo DB, empty citations, key leaks, 404 turned into 500, classify missing ownership check).

- Future work (not built): OCR for scanned PDFs, Google login/2FA, real email sending, Hindi, compare two versions, admin dashboard, contract templates library, expiry reminders, expiring share links, chat with your contract, negotiation email generator, key dates and amounts extractor, auto-delete setting and data export.
