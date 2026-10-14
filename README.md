# ScanTract

AI-powered contract risk analysis for rental and freelance contracts using Indian legal norms. This system identifies risky clauses and missing terms, providing plain-language explanations and legal references without giving legal advice.

## What It Does

ScanTract analyzes uploaded contracts through a multi-stage pipeline:
- Document extraction (PDF/DOCX)
- Clause segmentation
- LLM-powered classification
- Dual RAG retrieval (legal rules knowledge base + reference contract corpus)
- Risk detection with severity scoring
- Plain-language explanations with legal citations

The system flags unusual clauses by comparing them against Indian legal norms and reference contracts, but never provides legal advice.

## Features

- **User Authentication**: Register, login, password reset
- **Contract Upload**: PDF and DOCX support
- **Real-time Pipeline Tracking**: Visual progress through processing stages
- **Risk Analysis**: Identifies high/medium/low severity clauses
- **Missing Clause Detection**: Flags important missing terms
- **Explanations**: Plain-language explanations with legal references
- **PDF Reports**: Downloadable summary-first compact reports
- **Dashboard**: Contract statistics and status tracking
- **Sample Contracts**: Pre-loaded demo contracts for exploration

## Tech Stack

**Backend:**
- FastAPI (Python 3.11+)
- PostgreSQL + pgvector extension
- SQLAlchemy (async) + Alembic for migrations
- LangChain for RAG orchestration
- PyMuPDF, python-docx, PaddleOCR for document processing
- WeasyPrint for PDF generation
- JWT authentication with bcrypt

**Frontend:**
- React 19.2.8
- Vite 8.3.3
- TypeScript 6.0.2
- Tailwind CSS 3.4.17
- React Router DOM 7.18.2
- Framer Motion 14.0.0 for animations
- Lucide React for icons

**LLM Integration:**
- Supports Claude (Anthropic), GPT (OpenAI), and Gemini (Google)
- Switchable via `LLM_PROVIDER` environment variable
- Gemini embeddings (hard dependency for vector search)

## Quick Start with Docker

1. **Copy environment file:**
   ```bash
   cp backend/.env.example .env
   ```
   Edit `.env` and fill in required values (see Environment Variables section)

2. **Start services:**
   ```bash
   docker compose up -d --build
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - API Documentation: http://localhost:8000/docs
   - Database: localhost:5432

## Environment Variables

Required variables (from `backend/.env.example`):

**Database:**
- `DATABASE_URL` - PostgreSQL connection string

**LLM Configuration:**
- `LLM_PROVIDER` - Choose: "claude", "openai", or "gemini"
- `CLAUDE_API_KEY`, `CLAUDE_MODEL`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`, `GEMINI_MODEL`

**Embeddings:**
- `EMBEDDING_MODEL` - Gemini embedding model
- `EMBEDDING_DIMENSIONS` - Vector dimensions (3072)

**Upload Limits:**
- `MAX_UPLOAD_SIZE_MB` - Maximum file size
- `MAX_UPLOADS_PER_DAY` - Daily upload limit per user

**Authentication:**
- `JWT_SECRET` - Secret key for JWT tokens
- `RESET_LINK_MODE` - Password reset link mode

**Processing:**
- `LLM_CONCURRENCY_LIMIT` - Concurrent LLM requests
- `LLM_MAX_RETRIES` - Retry attempts
- `LLM_TIMEOUT_SECONDS` - Request timeout
- `MAX_CONTEXT_TOKENS` - Max tokens for context
- `DEDUPLICATION_THRESHOLD` - Similarity threshold
- `MIN_CHUNKS_PER_SOURCE` - Minimum chunks per source

**Other:**
- `UPLOAD_TEMP_DIR` - Temporary upload directory
- `LOG_LEVEL` - Logging level

## Project Structure

**Backend (`backend/app/`):**
- `api/` - FastAPI route handlers
  - `routes/auth.py` - Authentication endpoints
  - `routes/contracts.py` - Contract management
  - `routes/explanations.py` - Explanation generation
  - `routes/pipeline.py` - Pipeline control
  - `routes/reports.py` - Report generation
- `auth/` - JWT and password handling
- `db/` - SQLAlchemy models and database session
- `document_processing/` - Document extraction and processing
- `llm/` - LLM client abstraction and processing
- `rag/` - RAG prompt building and context merging
- `reports/` - Report assembly and PDF generation
- `utils/` - Error handling utilities

**Frontend (`frontend/src/`):**
- `auth/` - Protected routes and auth context
- `components/` - Reusable UI components
  - `ui/` - Base UI components
  - `landing/` - Landing page sections
- `hooks/` - Custom React hooks
- `lib/` - API client and utilities
- `pages/` - Page components
  - `auth/` - Login, signup, password reset
- `test/` - Test utilities
- `types/` - TypeScript type definitions

## API Overview

**Authentication (`/api/auth`):**
- `POST /register` - Create new account
- `POST /login` - Authenticate user
- `GET /me` - Get current user
- `POST /forgot-password` - Request password reset
- `POST /reset-password` - Reset password with token
- `DELETE /me/data` - Delete user account and data

**Contracts (`/api/contracts`):**
- `POST /upload` - Upload contract file
- `GET /list` - List user's contracts
- `GET /stats` - Get contract statistics
- `DELETE /{contract_id}` - Delete contract
- `POST /{contract_id}/retry` - Retry failed processing

**Explanations (`/api/contracts/{contract_id}`):**
- `GET /explanations` - Get clause explanations
- `POST /explanations/regenerate` - Regenerate explanations

**Pipeline Control (`/api/contracts/{contract_id}`):**
- `POST /classify` - Run clause classification
- `POST /detect-risks` - Run risk detection
- `POST /generate-explanations` - Generate explanations

**Reports (`/api/contracts/{contract_id}`):**
- `GET /report` - Get JSON report
- `GET /report/pdf` - Download PDF report

## Running Tests

**Backend tests:**
```bash
cd backend
python -m pytest tests --ignore=tests/integration
```
Tests run against the `scantract_scratch` database (never the main database).

**Frontend tests:**
```bash
cd frontend
npx vitest run
```

## Important Notes

**Disclaimer:** This system uses a sample knowledge base for demonstration purposes. It is not a substitute for professional legal advice. Always consult a qualified lawyer for contract review.

**LLM Quotas:** Free-tier API keys have daily upload limits. The `MAX_UPLOADS_PER_DAY` setting prevents quota exhaustion.

**Processing Time:** Contract analysis can take 3-4 minutes depending on document length and LLM response times.

**Sample Contracts:** The system includes pre-loaded sample contracts for exploring features without uploading your own documents.
