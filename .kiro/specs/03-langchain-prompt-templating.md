# Spec: LangChain Prompt Templating Layer

## Overview
Build the prompt templating layer for ScanTract using LangChain — Stage 3 of the core pipeline that constructs structured prompts for clause classification and risk detection. Templates are stored as separate files (not inline strings) and loaded at runtime, following the steering rule that prompt templates belong in `backend/rag/prompts/`.

## Scope
- LangChain PromptTemplate for clause classification
- LangChain PromptTemplate for risk & missing clause detection
- Prompt template files stored as `.txt` or `.jinja` in `backend/rag/prompts/`
- Builder functions: `build_classification_prompt()` and `build_risk_prompt()`
- Runtime template loading and validation
- Legal compliance instructions embedded in templates
- Unit tests for prompt assembly and placeholder validation

## Requirements

### Functional Requirements

**FR-1: Clause Classification Template**
- Template file: `backend/rag/prompts/clause_classification.txt`
- Input variables:
  - `clause_text`: The clause content to classify
  - `clause_index`: Position in contract (e.g., "1.1", "para_5")
  - `contract_type`: "rental" or "freelance"
  - `retrieved_context`: Placeholder for RAG-retrieved context (stages 5A/5B)
- Output: Structured prompt ready for LLM
- Must include instructions: no legal advice, no imperatives, cite sources

**FR-2: Risk & Missing Clause Detection Template**
- Template file: `backend/rag/prompts/risk_detection.txt`
- Input variables:
  - `clauses_list`: Full list of classified clauses with metadata
  - `legal_context`: Merged context from legal rules KB (stage 5A)
  - `corpus_context`: Merged context from reference contracts (stage 5B)
  - `contract_type`: "rental" or "freelance"
- Output: Structured prompt ready for LLM
- Must include instructions: no legal advice, always cite triggering rules


**FR-3: Template Storage**
- All templates stored as separate files in `backend/rag/prompts/`
- No inline Python strings for prompt content (per steering rules)
- Support both `.txt` (simple) and `.jinja` (advanced) formats
- Templates loaded at module initialization or first use (lazy loading)

**FR-4: Prompt Builder Functions**
- `build_classification_prompt()`: Assembles clause classification prompt
- `build_risk_prompt()`: Assembles risk detection prompt
- Both functions return LangChain-compatible message arrays or prompt strings
- Validate all required variables are provided
- Raise clear errors if placeholders remain unfilled

**FR-5: Legal Compliance Instructions**
- Both templates must explicitly instruct the LLM:
  - "Never provide legal advice"
  - "Never use imperative language like 'you should' or 'you must'"
  - "Always cite which legal rule or reference clause triggered a flag"
  - "Use language like 'this clause differs from X because Y'"
  - "Provide severity scores based on objective criteria"

**FR-6: Template Variables Validation**
- Before sending to LLM, validate no placeholders remain (e.g., `{variable}`)
- Check all required variables are non-empty
- Log warning if optional variables missing (but don't fail)

### Non-Functional Requirements

**NFR-1: Type Safety**
- All functions use type hints (Python 3.11+)
- Pydantic models for prompt inputs
- Return types clearly specified (str or list of message dicts)

**NFR-2: Maintainability**
- Template changes don't require code changes
- Clear separation: templates (content) vs builders (logic)
- Templates readable by non-engineers

**NFR-3: Performance**
- Templates loaded once and cached in memory
- Template assembly completes in <100ms
- No file I/O during prompt building (pre-loaded)

**NFR-4: Error Handling**
- Missing template files raise clear errors at startup
- Invalid template syntax caught during loading
- Missing variables caught before LLM call

