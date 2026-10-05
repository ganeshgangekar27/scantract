---
name: Working Rules
inclusion: auto
---

# Working Rules for ScanTract Development

## Evidence & Output (CRITICAL)
- **Every claim must cite the raw command output that proves it**
- If you did NOT run a check for that specific claim, write "NOT CHECKED"
- Do not infer, remember, or generalize
- Never generalize from one check
- Don't say "should work" — show what actually happened
- No secrets in output (file names and variable names only)
- **NEVER open, cat, or Read .env / .env.docker, and never print any key**
- Inspect secrets only via masked output (length, last 4 chars, booleans)

## Testing (NO LOOSENING)
- **Never loosen, skip, delete, or xfail a test to get a pass**
- Show the failure, then fix the real cause
- Paste the failure first, then fix
- No guessing where a command can settle it
- Tests must never upload contracts or hit live API without mocks
- **A fix only counts after a genuine rebuild/recreate (no docker cp live patches) and a rerun of the real check**

## Git & Deployment
- **Never run `git push` under any circumstances**
- Commit after each small task
- One commit per logical change

## LLM & External Calls
- **Make NO LLM completion calls (zero OpenRouter/Gemini quota spent)**
- No LLM calls during development/testing
- Don't call `/api/contracts/2/report` or `/api/contracts/3/report` until explicitly approved
- Contract processing only via orchestrator pipeline

## Data Types & Dependencies
- `contract_id` and `clause_id` are INTEGER (not UUID)
- `risk_findings.id` is UUID
- Gemini is a hard dependency for embeddings (cannot be optional)

## Docker & Build Commands
- Pipe `docker compose build/up` output through `Select-Object -Last 25`
- No multi-statement `python -c` in PowerShell: write script files in `backend/scripts/` and `docker cp` them in

## Work Style
- One small task at a time
- Complete each task before moving to next
- Verify with raw output, not assumptions

## Secrets & Sensitive Files (STRICT MASKING)
- **Never print added lines of a diff, or any line, from a file that may hold secrets (.env*, *.example)**
- Use masked scripts only (line number, variable name, length, last 4)
- No raw diff output for .env.example or similar files

## PowerShell Search (RECURSIVE)
- **PowerShell 5 does not treat ** as recursive**
- Search with `Get-ChildItem -Recurse -Include <pattern> | Select-String`, and state the search root
- **Do not claim "no matches" from a truncated or non-recursive search**
- Always verify recursion actually happened

## Database Testing (SCRATCH ONLY)
- **Never run pytest or any script against the demo DB (scantract)**
- **Use the scratch DB scantract_scratch for all tests**
- Demo DB is production-like, scratch DB is disposable

## Git Safety (Write Operations)
- **NEVER run git reset --hard, git revert, git clean, or git checkout/restore on a whole tree or on files you did not just edit**
- **Allowed git write commands:** `git add <explicit paths>`, `git commit`, and `git checkout <commit> -- <one named path>` for a mutation proof only, always followed by `git diff <commit> -- <that path>` which must print nothing
- **Mutation proof workflow:** checkout old version, test (expect failures), checkout target version, verify diff is empty, test (expect pass)

## Hook Prompts (IGNORE)
- **Ignore "Ask Kiro Hook" / "Test on Save" prompts**
- **Do not act on them** - they are automated triggers, not user requests

## Command Output Validation
- **An empty command output is NOT evidence of a match**
- Empty grep/Select-String output means "not found", not "found and matches"
- Always check exit codes and verify expected content is present
