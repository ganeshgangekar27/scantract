# Coding & Repo Conventions

- Commit messages: Conventional Commits (feat:, fix:, chore:, docs:, refactor:)
- One spec (.kiro/specs/) per architecture stage from the ScanTract diagram —
  do not merge multiple stages into one spec.
- Every new backend feature needs a matching pytest test file in
  backend/tests/.
- API responses follow a single consistent envelope:
  { "success": bool, "data": {...}, "error": str | null }
- No clause text or contract content should ever be logged in plaintext.