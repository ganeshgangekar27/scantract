# ScanTract — Product Context

ScanTract analyzes uploaded rental/freelance contracts and flags risky or
missing clauses using Indian legal norms, without giving legal advice.

Core pipeline (must be respected in every spec):
1. Contract upload (React/Vite/TS frontend)
2. Document processing: PyMuPDF (PDF), python-docx (DOCX), PaddleOCR (scans)
3. Prompt templating via LangChain, injecting clause + pgvector context
4. LLM clause classification (Claude/GPT API)
5. Dual RAG lookup: (5A) Indian legal rules KB, (5B) reference contract corpus
   — both via pgvector similarity search
6. Merge/dedupe both retrieval sources into one context set
7. LLM risk & missing-clause detection with severity scoring
8. Plain-language explanation + legal citation generation
9. Structured API response → React output UI (highlighted clauses, risk
   levels, missing clauses, explanations, references)

Non-negotiable: every flagged clause must be traceable to (a) the source
clause text, (b) the triggering rule or corpus match, (c) a severity score.
The system must never say "you should" or give legal advice — only
"this clause is unusual because X, compared to Y".