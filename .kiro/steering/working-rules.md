---
name: Working Rules
inclusion: auto
---

# Working Rules for ScanTract Development

## Evidence & Output
- Paste raw command output for every claim
- Never generalize from one check
- Don't say "should work" — show what actually happened
- No secrets in output (file names and variable names only)

## Testing
- Never skip or loosen a test to get green
- Paste the failure first, then fix
- No guessing where a command can settle it
- Tests must never upload contracts or hit live API without mocks

## Git & Deployment
- **Never run `git push` under any circumstances**
- Commit after each small task
- One commit per logical change

## LLM & External Calls
- No LLM calls during development/testing
- Don't call `/api/contracts/2/report` or `/api/contracts/3/report` until explicitly approved
- Contract processing only via orchestrator pipeline

## Data Types & Dependencies
- `contract_id` is INTEGER (not UUID)
- `clause_id` is INTEGER (not UUID)
- Gemini is a hard dependency for embeddings (cannot be optional)

## Work Style
- One small task at a time
- Complete each task before moving to next
- Verify with raw output, not assumptions
