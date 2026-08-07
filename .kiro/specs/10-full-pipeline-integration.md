# Spec: Full Pipeline Integration & Deployment

## Overview
Wire all 9 stages of ScanTract into a complete end-to-end pipeline, from contract upload through analysis to final report generation. Includes Docker containerization, orchestration with docker-compose, and comprehensive documentation for local development setup.

## Scope
- Backend pipeline orchestration (Stages 2-9)
- Background task processing
- Status polling endpoints
- Docker containerization (frontend, backend, postgres+pgvector)
- docker-compose.yml for one-command startup
- Development and production configurations
- Top-level README with setup instructions
- Health check endpoints
- Error handling and logging throughout pipeline

## Pipeline Flow

```
User → Frontend → Backend → Processing → Database → Frontend
  │        │         │           │           │          │
  │        │         │           │           │          │
  │     Upload    Receive    Background    Store     Display
  │      File      File       Pipeline    Results    Report
  │        │         │           │           │          │
  ↓        ↓         ↓           ↓           ↓          ↓
Upload  React    FastAPI    Stages 2-9   PostgreSQL  React
 Page   Component  POST      (async)     +pgvector    Report
                  endpoint                            View
```

## Requirements

### Functional Requirements

**FR-1: Upload Endpoint with Pipeline Trigger**
- `POST /api/contracts/upload` receives file
- Validates file (type, size)
- Stores temporarily
- Creates contract record in database
- Triggers background pipeline processing
- Returns contract_id immediately (non-blocking)


### Pipeline Orchestrator

**File: backend/app/pipeline/orchestrator.py**

```python
"""
Main pipeline orchestrator for ScanTract.

Coordinates execution of stages 2-9 in sequence.
"""

import asyncio
import logging
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Contract
from ..document_processing.extractor import extract_text_from_pdf, extract_text_from_docx
from ..document_processing.normalizer import clean_and_normalize
from ..document_processing.segmenter import segment_clauses
from ..llm.classify_clauses import classify_all_clauses
from ..llm.detect_risk import detect_risks
from ..llm.generate_explanations import generate_all_explanations

logger = logging.getLogger(__name__)

async def run_full_pipeline(
    contract_id: str,
    file_path: str,
    file_extension: str,
    db: AsyncSession
) -> None:
    """
    Execute full ScanTract pipeline for uploaded contract.
    
    Stages:
        2. Document processing (extraction, segmentation)
        3. Prompt templating (used in stages 4 & 7)
        4. Clause classification
        5A. Legal rules KB search (in stage 7)
        5B. Reference corpus search (in stage 7)
        6. Retrieval merge (in stage 7)
        7. Risk detection
        8. Explanation generation
        9. Report assembly (on-demand via GET)
    
    Args:
        contract_id: Contract UUID
        file_path: Path to uploaded file
        file_extension: .pdf or .docx
        db: Database session
    """
    try:
        logger.info(f"Starting pipeline for contract {contract_id}")
        
        # Stage 2: Document Processing
        await _stage_2_document_processing(
            contract_id, file_path, file_extension, db
        )
        
        # Stage 4: Clause Classification
        await _stage_4_classification(contract_id, db)
        
        # Stage 7: Risk Detection (includes 5A, 5B, 6 internally)
        await _stage_7_risk_detection(contract_id, db)
        
        # Stage 8: Explanation Generation
        await _stage_8_explanations(contract_id, db)
        
        # Mark as complete
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(
                processing_status="complete",
                processing_completed_at=datetime.utcnow()
            )
        )
        await db.commit()
        
        logger.info(f"Pipeline complete for contract {contract_id}")
        
    except Exception as e:
        logger.error(f"Pipeline failed for contract {contract_id}: {e}", exc_info=True)
        
        # Mark as failed
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(
                processing_status="failed",
                error_message=str(e)
            )
        )
        await db.commit()
        
        raise
    
    finally:
        # Clean up temp file
        import os
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")

async def _stage_2_document_processing(
    contract_id: str,
    file_path: str,
    file_extension: str,
    db: AsyncSession
) -> None:
    """Stage 2: Extract text and segment clauses."""
    logger.info(f"Stage 2: Document processing for {contract_id}")
    
    # Update status
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(processing_status="extracting_text")
    )
    await db.commit()
    
    # Extract text
    if file_extension == ".pdf":
        extraction_result = await extract_text_from_pdf(file_path)
    elif file_extension == ".docx":
        extraction_result = await extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")
    
    # Normalize
    normalized_text = clean_and_normalize(extraction_result["full_text"])
    
    # Segment clauses
    clauses = segment_clauses(normalized_text)
    
    # Store in database
    from ..db.models import Clause
    for clause in clauses:
        db_clause = Clause(
            contract_id=contract_id,
            clause_number=clause.clause_id,
            clause_text=clause.clause_text,
            position=clause.position,
            parent_clause_id=None  # TODO: map parent references
        )
        db.add(db_clause)
    
    # Update contract
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(
            full_text=normalized_text,
            page_count=extraction_result.get("page_count")
        )
    )
    await db.commit()
    
    logger.info(f"Stage 2 complete: {len(clauses)} clauses extracted")
```


**FR-2: Background Pipeline Processing**
- Pipeline runs asynchronously (doesn't block upload response)
- Execute stages 2-9 in sequence:
  1. Stage 2: Document processing → clauses
  2. Stage 4: Clause classification
  3. Stage 7: Risk detection (includes 5A, 5B, 6)
  4. Stage 8: Explanation generation
  5. Stage 9: Available via GET (on-demand)
- Update contract status at each stage
- Handle errors gracefully (mark as failed, preserve partial results)

**FR-3: Status Polling Endpoint**
- `GET /api/contracts/{contract_id}/status`
- Returns current processing status and progress
- Status values:
  - `uploaded`: File received, pending processing
  - `extracting_text`: Stage 2 in progress
  - `classifying`: Stage 4 in progress
  - `analyzing_risks`: Stage 7 in progress
  - `generating_explanations`: Stage 8 in progress
  - `complete`: Ready for report retrieval
  - `failed`: Error occurred (with error message)
- Progress percentage (estimated)

**FR-4: Health Check Endpoints**
- `GET /health`: Basic health check (API alive)
- `GET /health/ready`: Readiness check (DB connected, models loaded)
- Used by Docker and monitoring

**FR-5: Database Migrations**
- Alembic migrations for all tables (contracts, clauses, risk_findings, etc.)
- Initial seed data for legal KB and reference corpus
- Migration command in Docker entrypoint

**FR-6: Environment Configuration**
- Separate configs for development and production
- Environment variables for all secrets and configs
- Docker secrets support for production

**FR-7: Docker Containerization**
- Backend Dockerfile (FastAPI + dependencies)
- Frontend Dockerfile (React + Vite)
- PostgreSQL with pgvector extension
- docker-compose.yml orchestrating all services

**FR-8: One-Command Setup**
- `docker-compose up` starts entire system
- Automatic database initialization
- Seed data loaded on first run
- Frontend accessible at http://localhost:3000
- Backend API at http://localhost:8000


**File: backend/app/pipeline/orchestrator.py (continued)**

```python
async def _stage_4_classification(contract_id: str, db: AsyncSession) -> None:
    """Stage 4: Classify all clauses."""
    logger.info(f"Stage 4: Clause classification for {contract_id}")
    
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(processing_status="classifying")
    )
    await db.commit()
    
    # Detect contract type (simple heuristic for now)
    contract = await db.get(Contract, contract_id)
    contract_type = _detect_contract_type(contract.full_text)
    
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(contract_type=contract_type)
    )
    await db.commit()
    
    # Classify
    result = await classify_all_clauses(
        contract_id=contract_id,
        contract_type=contract_type,
        db=db
    )
    
    logger.info(
        f"Stage 4 complete: {result['successful']} classified, "
        f"{result['failed']} failed"
    )

async def _stage_7_risk_detection(contract_id: str, db: AsyncSession) -> None:
    """Stage 7: Detect risks (includes 5A, 5B, 6 internally)."""
    logger.info(f"Stage 7: Risk detection for {contract_id}")
    
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(processing_status="analyzing_risks")
    )
    await db.commit()
    
    # Detect risks
    result = await detect_risks(contract_id=contract_id, db=db)
    
    logger.info(
        f"Stage 7 complete: {result.total_risks} risky clauses, "
        f"{result.total_missing} missing clauses"
    )

async def _stage_8_explanations(contract_id: str, db: AsyncSession) -> None:
    """Stage 8: Generate explanations."""
    logger.info(f"Stage 8: Generating explanations for {contract_id}")
    
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(processing_status="generating_explanations")
    )
    await db.commit()
    
    # Generate explanations
    count = await generate_all_explanations(contract_id=contract_id, db=db)
    
    logger.info(f"Stage 8 complete: {count} explanations generated")

def _detect_contract_type(full_text: str) -> str:
    """
    Detect contract type from text content.
    
    Simple heuristic - can be improved with ML.
    """
    text_lower = full_text.lower()
    
    # Rental indicators
    rental_keywords = ["tenant", "landlord", "rent", "lease", "premises"]
    rental_score = sum(1 for kw in rental_keywords if kw in text_lower)
    
    # Freelance indicators
    freelance_keywords = ["freelancer", "contractor", "deliverable", "milestone", "client"]
    freelance_score = sum(1 for kw in freelance_keywords if kw in text_lower)
    
    if rental_score > freelance_score:
        return "rental"
    elif freelance_score > rental_score:
        return "freelance"
    else:
        # Default to rental if unclear
        return "rental"
```


### Upload Endpoint with Pipeline Trigger

**File: backend/app/api/routes/contracts.py (updated)**

```python
"""
Contract upload and status endpoints.
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import os
from pathlib import Path
from datetime import datetime
import logging

from ...db.database import get_db
from ...db.models import Contract
from ...pipeline.orchestrator import run_full_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_TEMP_DIR", "./uploads/temp"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15")) * 1024 * 1024

@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Upload contract file and trigger analysis pipeline.
    
    Returns immediately with contract_id. Pipeline runs in background.
    Client should poll /api/contracts/{id}/status for progress.
    
    Args:
        file: Contract file (PDF or DOCX, max 15MB)
        background_tasks: FastAPI background tasks
        db: Database session
    
    Returns:
        {
            "success": true,
            "data": {
                "contract_id": "uuid",
                "filename": "contract.pdf",
                "size": 1234567,
                "upload_timestamp": "2026-08-06T10:30:00Z",
                "status": "uploaded"
            },
            "error": null
        }
    """
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in [".pdf", ".docx"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Only PDF and DOCX are supported."
            )
        
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit."
            )
        
        # Generate contract ID and temp file path
        contract_id = uuid.uuid4()
        temp_filename = f"{contract_id}{file_extension}"
        temp_path = UPLOAD_DIR / temp_filename
        
        # Save file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File saved: {temp_path} ({file_size} bytes)")
        
        # Create contract record
        contract = Contract(
            id=contract_id,
            filename=file.filename,
            file_size=file_size,
            upload_timestamp=datetime.utcnow(),
            processing_status="uploaded"
        )
        db.add(contract)
        await db.commit()
        
        # Trigger background pipeline
        background_tasks.add_task(
            run_full_pipeline,
            contract_id=str(contract_id),
            file_path=str(temp_path),
            file_extension=file_extension,
            db=db
        )
        
        logger.info(f"Pipeline triggered for contract {contract_id}")
        
        return {
            "success": True,
            "data": {
                "contract_id": str(contract_id),
                "filename": file.filename,
                "size": file_size,
                "upload_timestamp": contract.upload_timestamp.isoformat(),
                "status": "uploaded"
            },
            "error": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Upload failed")

@router.get("/{contract_id}/status")
async def get_contract_status(
    contract_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get current processing status for a contract.
    
    Poll this endpoint to track pipeline progress.
    
    Returns:
        {
            "success": true,
            "data": {
                "contract_id": "uuid",
                "status": "classifying",
                "progress": 45,
                "message": "Classifying clauses..."
            },
            "error": null
        }
    """
    try:
        contract = await db.get(Contract, contract_id)
        
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")
        
        # Map status to progress percentage
        status_progress = {
            "uploaded": 5,
            "extracting_text": 20,
            "classifying": 45,
            "analyzing_risks": 70,
            "generating_explanations": 85,
            "complete": 100,
            "failed": 0
        }
        
        status_messages = {
            "uploaded": "Pending processing...",
            "extracting_text": "Extracting text from document...",
            "classifying": "Classifying clauses...",
            "analyzing_risks": "Analyzing risks and missing clauses...",
            "generating_explanations": "Generating plain-language explanations...",
            "complete": "Analysis complete!",
            "failed": contract.error_message or "Processing failed"
        }
        
        return {
            "success": True,
            "data": {
                "contract_id": str(contract.id),
                "status": contract.processing_status,
                "progress": status_progress.get(contract.processing_status, 0),
                "message": status_messages.get(contract.processing_status, "Processing...")
            },
            "error": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Status check failed")
```


## Docker Configuration

### Backend Dockerfile

**File: backend/Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for weasyprint and PDF processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create upload directory
RUN mkdir -p uploads/temp

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && python -m backend.db.legal_kb.seed_legal_kb && python -m backend.db.reference_corpus.seed_reference_corpus && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### Frontend Dockerfile

**File: frontend/Dockerfile**

```dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Production image
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**File: frontend/nginx.conf**

```nginx
server {
    listen 80;
    server_name localhost;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # SPA routing - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```


### docker-compose.yml

**File: docker-compose.yml (root)**

```yaml
version: '3.8'

services:
  # PostgreSQL with pgvector extension
  postgres:
    image: ankane/pgvector:latest
    container_name: scantract-postgres
    environment:
      POSTGRES_DB: scantract
      POSTGRES_USER: scantract_user
      POSTGRES_PASSWORD: scantract_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U scantract_user -d scantract"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - scantract-network

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: scantract-backend
    environment:
      # Database
      DATABASE_URL: postgresql+asyncpg://scantract_user:scantract_password@postgres:5432/scantract
      
      # LLM Configuration
      LLM_PROVIDER: ${LLM_PROVIDER:-claude}
      CLAUDE_API_KEY: ${CLAUDE_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      
      # File Upload
      UPLOAD_TEMP_DIR: ./uploads/temp
      MAX_UPLOAD_SIZE_MB: 15
      
      # Embedding & RAG
      EMBEDDING_MODEL: text-embedding-3-small
      EMBEDDING_DIMENSIONS: 1536
      MAX_CONTEXT_TOKENS: 4000
      DEDUPLICATION_THRESHOLD: 0.95
      MIN_CHUNKS_PER_SOURCE: 1
      
      # LLM Processing
      LLM_CONCURRENCY_LIMIT: 5
      LLM_MAX_RETRIES: 3
      LLM_TIMEOUT_SECONDS: 30
      
      # Logging
      LOG_LEVEL: INFO
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - upload_data:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - scantract-network
    restart: unless-stopped

  # React Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: scantract-frontend
    environment:
      VITE_API_BASE_URL: http://localhost:8000
    ports:
      - "3000:80"
    depends_on:
      - backend
    networks:
      - scantract-network
    restart: unless-stopped

networks:
  scantract-network:
    driver: bridge

volumes:
  postgres_data:
  upload_data:
```

### Environment Variables Template

**File: .env.example (root)**

```bash
# ===================
# ScanTract Configuration
# ===================

# LLM Provider (claude or openai)
LLM_PROVIDER=claude

# API Keys (REQUIRED - obtain from providers)
CLAUDE_API_KEY=sk-ant-your-key-here
OPENAI_API_KEY=sk-your-key-here

# Database (default for Docker, override for production)
DATABASE_URL=postgresql+asyncpg://scantract_user:scantract_password@localhost:5432/scantract

# File Upload
UPLOAD_TEMP_DIR=./uploads/temp
MAX_UPLOAD_SIZE_MB=15

# Embedding Configuration
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# RAG Configuration
MAX_CONTEXT_TOKENS=4000
DEDUPLICATION_THRESHOLD=0.95
MIN_CHUNKS_PER_SOURCE=1

# LLM Processing
LLM_CONCURRENCY_LIMIT=5
LLM_MAX_RETRIES=3
LLM_TIMEOUT_SECONDS=30

# Logging
LOG_LEVEL=INFO

# Frontend API URL
VITE_API_BASE_URL=http://localhost:8000
```


## Top-Level README

**File: README.md (root)**

```markdown
# ScanTract

AI-powered contract analysis system that identifies risky clauses and missing provisions in rental and freelance contracts using Indian legal norms.

## Features

- 📄 **Contract Upload**: Support for PDF and DOCX files (up to 15MB)
- 🔍 **Clause Analysis**: Automatic classification and risk detection
- ⚖️ **Legal Compliance**: Cross-references with Model Tenancy Act 2021 and Indian Contract Act
- 📊 **Risk Scoring**: High/medium/low severity ratings with explanations
- 📝 **Plain Language**: Clear explanations without legal jargon
- 📑 **PDF Reports**: Downloadable analysis reports
- 🔗 **Citation Traceability**: Every finding linked to legal source

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with pgvector extension
- **LLMs**: Claude (Anthropic) / GPT (OpenAI)
- **RAG**: LangChain + OpenAI embeddings
- **OCR**: PaddleOCR for scanned documents

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Routing**: React Router v6

## Quick Start

### Prerequisites

- Docker and Docker Compose
- API keys:
  - Claude API key (or OpenAI API key)
  - OpenAI API key (for embeddings)

### 1. Clone Repository

\`\`\`bash
git clone https://github.com/your-org/scantract.git
cd scantract
\`\`\`

### 2. Configure Environment

\`\`\`bash
# Copy template
cp .env.example .env

# Edit .env and add your API keys
nano .env
\`\`\`

**Required:**
- `CLAUDE_API_KEY` or `OPENAI_API_KEY` (for LLM)
- `OPENAI_API_KEY` (for embeddings)

### 3. Start System

\`\`\`bash
docker-compose up --build
\`\`\`

This will:
- Build and start all services (frontend, backend, database)
- Run database migrations
- Seed legal knowledge base and reference corpus
- Make the system available at:
  - **Frontend**: http://localhost:3000
  - **Backend API**: http://localhost:8000
  - **API Docs**: http://localhost:8000/docs

### 4. Use the System

1. **Open Frontend**: Navigate to http://localhost:3000
2. **Upload Contract**: Drag-and-drop or browse for PDF/DOCX file
3. **Wait for Processing**: Watch progress (30-60 seconds)
4. **View Report**: Interactive analysis with highlighted clauses
5. **Download PDF**: Get printable report

## Development Setup

### Backend Only

\`\`\`bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed knowledge bases
python -m backend.db.legal_kb.seed_legal_kb
python -m backend.db.reference_corpus.seed_reference_corpus

# Start server
uvicorn app.main:app --reload
\`\`\`

### Frontend Only

\`\`\`bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
\`\`\`

### Run Tests

\`\`\`bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
\`\`\`

## Project Structure

\`\`\`
scantract/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # API endpoints
│   │   ├── db/               # Database models
│   │   ├── llm/              # LLM integrations
│   │   ├── rag/              # RAG & prompts
│   │   ├── document_processing/  # Text extraction
│   │   ├── pipeline/         # Pipeline orchestration
│   │   └── reports/          # Report generation
│   ├── alembic/              # Database migrations
│   ├── tests/                # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── hooks/            # Custom hooks
│   │   └── types/            # TypeScript types
│   ├── e2e/                  # E2E tests
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
\`\`\`

## Pipeline Stages

1. **Upload**: Frontend → Backend
2. **Text Extraction**: PyMuPDF (PDF) / python-docx (DOCX)
3. **Clause Segmentation**: Numbered/lettered pattern detection
4. **Classification**: LLM categorizes each clause
5. **Context Retrieval**: 
   - 5A: Legal rules from knowledge base
   - 5B: Reference clauses from corpus
6. **Context Merge**: Deduplicate and combine sources
7. **Risk Detection**: LLM identifies risky/missing clauses
8. **Explanation Generation**: Plain-language explanations
9. **Report Assembly**: Final structured output

## API Endpoints

### Upload
- `POST /api/contracts/upload` - Upload contract file

### Status
- `GET /api/contracts/{id}/status` - Check processing status

### Results
- `GET /api/contracts/{id}/report` - Get analysis report (JSON)
- `GET /api/contracts/{id}/report/pdf` - Download PDF report
- `GET /api/contracts/{id}/explanations` - Get explanations

### Health
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check

## Configuration

See `.env.example` for all available configuration options.

Key settings:
- `LLM_PROVIDER`: `claude` or `openai`
- `MAX_CONTEXT_TOKENS`: Context window size (default: 4000)
- `LLM_CONCURRENCY_LIMIT`: Parallel LLM calls (default: 5)
- `DEDUPLICATION_THRESHOLD`: Similarity for deduping (default: 0.95)

## Troubleshooting

### Database Connection Error

\`\`\`bash
# Verify PostgreSQL is running
docker ps | grep postgres

# Check logs
docker logs scantract-postgres
\`\`\`

### LLM API Errors

- Verify API keys in `.env`
- Check API quota/limits
- Review logs: `docker logs scantract-backend`

### Frontend Not Loading

\`\`\`bash
# Check if backend is running
curl http://localhost:8000/health

# Check frontend logs
docker logs scantract-frontend
\`\`\`

## Production Deployment

⚠️ **IMPORTANT**: Sample legal data is for development only.

Before production:
1. Replace sample legal rules with verified provisions
2. Obtain legal review of all knowledge base content
3. Set up proper secrets management (not .env file)
4. Configure HTTPS/SSL certificates
5. Set up monitoring and logging
6. Configure backup strategy
7. Review security settings

## License

[Your License Here]

## Disclaimer

⚠️ **Not Legal Advice**: ScanTract is an analysis tool, not a substitute for professional legal counsel. All findings should be reviewed by qualified legal professionals.

## Contributing

Contributions welcome! Please read CONTRIBUTING.md first.

## Support

For issues or questions:
- GitHub Issues: [github.com/your-org/scantract/issues](https://github.com/your-org/scantract/issues)
- Email: support@scantract.com

---

Made with ❤️ for safer contracts
\`\`\`


## Health Check Endpoints

**File: backend/app/api/routes/health.py**

```python
"""
Health check endpoints for monitoring and Docker.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ...db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

@router.get("/health")
async def health_check() -> dict:
    """
    Basic health check - API is alive.
    
    Returns 200 if service is running.
    """
    return {
        "status": "healthy",
        "service": "scantract-api",
        "version": "1.0.0"
    }

@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Readiness check - API is ready to serve traffic.
    
    Checks:
    - Database connection
    - Required tables exist
    
    Returns 200 if ready, 503 if not ready.
    """
    checks = {
        "database": "unknown",
        "tables": "unknown"
    }
    
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        checks["database"] = "connected"
        
        # Check required tables exist
        result = await db.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name IN ('contracts', 'clauses', 'risk_findings', 'legal_rules', 'reference_clauses')
            """)
        )
        table_count = result.scalar()
        
        if table_count == 5:
            checks["tables"] = "ready"
        else:
            checks["tables"] = f"missing ({table_count}/5)"
        
        # Determine overall readiness
        is_ready = checks["database"] == "connected" and checks["tables"] == "ready"
        
        if is_ready:
            return {
                "status": "ready",
                "checks": checks
            }
        else:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail={"status": "not_ready", "checks": checks}
            )
            
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "checks": checks,
                "error": str(e)
            }
        )
```

## Database Schema Updates

**File: backend/app/db/models.py (extended Contract model)**

```python
class Contract(Base):
    __tablename__ = "contracts"
    
    # ... existing fields ...
    
    # Pipeline tracking (added)
    contract_type = Column(String(50), nullable=True)  # 'rental' or 'freelance'
    state = Column(String(100), nullable=True)  # User's state (for legal rule filtering)
```

**File: backend/alembic/versions/007_add_contract_type_and_state.py**

```python
"""Add contract_type and state to contracts

Revision ID: 007
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('contracts', sa.Column('contract_type', sa.String(50), nullable=True))
    op.add_column('contracts', sa.Column('state', sa.String(100), nullable=True))
    
    # Add index
    op.create_index('idx_contracts_type', 'contracts', ['contract_type'])

def downgrade():
    op.drop_index('idx_contracts_type')
    op.drop_column('contracts', 'state')
    op.drop_column('contracts', 'contract_type')
```


## Testing

### Backend Integration Tests

**File: backend/tests/test_full_pipeline.py**

```python
"""
Integration tests for complete pipeline.
"""

import pytest
from pathlib import Path
from httpx import AsyncClient
import asyncio

@pytest.mark.asyncio
async def test_full_pipeline_pdf(client: AsyncClient, db, test_pdf_file):
    """Test complete pipeline with PDF file."""
    # Upload
    files = {"file": ("test.pdf", test_pdf_file, "application/pdf")}
    response = await client.post("/api/contracts/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    contract_id = data["data"]["contract_id"]
    
    # Poll status until complete
    for _ in range(60):  # Max 60 seconds
        response = await client.get(f"/api/contracts/{contract_id}/status")
        status_data = response.json()["data"]
        
        if status_data["status"] == "complete":
            break
        elif status_data["status"] == "failed":
            pytest.fail(f"Pipeline failed: {status_data}")
        
        await asyncio.sleep(1)
    
    assert status_data["status"] == "complete"
    
    # Get report
    response = await client.get(f"/api/contracts/{contract_id}/report")
    assert response.status_code == 200
    
    report = response.json()["data"]
    assert "contract_id" in report
    assert "clauses" in report
    assert "risk_summary" in report
    assert len(report["clauses"]) > 0

@pytest.mark.asyncio
async def test_full_pipeline_docx(client: AsyncClient, test_docx_file):
    """Test complete pipeline with DOCX file."""
    files = {"file": ("test.docx", test_docx_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = await client.post("/api/contracts/upload", files=files)
    
    assert response.status_code == 200
    contract_id = response.json()["data"]["contract_id"]
    
    # Wait for completion
    # ... similar to PDF test ...

@pytest.mark.asyncio
async def test_pdf_download(client: AsyncClient, completed_contract_id):
    """Test PDF report download."""
    response = await client.get(f"/api/contracts/{completed_contract_id}/report/pdf")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    
    # Verify PDF content
    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF")  # PDF magic number
```

### Frontend E2E Tests

**File: frontend/e2e/full-flow.spec.ts**

```typescript
import { test, expect } from '@playwright/test';

test.describe('Full Contract Analysis Flow', () => {
  test('should upload contract and view report', async ({ page }) => {
    // Navigate to upload page
    await page.goto('/');
    
    // Upload file
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles('./test-fixtures/sample-contract.pdf');
    
    // Wait for upload
    await expect(page.locator('text=Processing')).toBeVisible();
    
    // Wait for completion (max 60s)
    await expect(page.locator('text=Analysis Complete')).toBeVisible({ timeout: 60000 });
    
    // Navigate to report
    await page.locator('button:has-text("View Report")').click();
    
    // Verify report loaded
    await expect(page.locator('h1')).toContainText('sample-contract.pdf');
    await expect(page.locator('[data-testid="risk-summary-header"]')).toBeVisible();
    
    // Verify clauses displayed
    const clauses = await page.locator('[data-testid^="clause-"]').count();
    expect(clauses).toBeGreaterThan(0);
    
    // Click a risky clause
    const riskyClause = await page.locator('[data-risky="true"]').first();
    await riskyClause.click();
    
    // Verify explanation panel opens
    await expect(page.locator('[data-testid="explanation-panel"]')).toBeVisible();
    await expect(page.locator('text=Analysis')).toBeVisible();
    await expect(page.locator('text=Legal Reference')).toBeVisible();
    
    // Close panel
    await page.locator('[data-testid="explanation-backdrop"]').click();
    await expect(page.locator('[data-testid="explanation-panel"]')).not.toBeVisible();
    
    // Download PDF
    const downloadPromise = page.waitForEvent('download');
    await page.locator('[data-testid="download-pdf-button"]').click();
    const download = await downloadPromise;
    
    expect(download.suggestedFilename()).toMatch(/contract-report-.+\.pdf/);
  });
  
  test('should handle upload errors gracefully', async ({ page }) => {
    await page.goto('/');
    
    // Upload invalid file type
    const fileInput = await page.locator('input[type="file"]');
    await fileInput.setInputFiles('./test-fixtures/invalid.txt');
    
    // Verify error message
    await expect(page.locator('text=Only PDF and DOCX files are supported')).toBeVisible();
  });
});
```


## Files to Create/Modify

### Root Level

**New:**
1. `docker-compose.yml` - Orchestration config
2. `.env.example` - Environment template
3. `README.md` - Complete setup documentation
4. `.dockerignore` - Docker build exclusions
5. `.gitignore` - Git exclusions

### Backend

**New:**
6. `backend/Dockerfile` - Backend container
7. `backend/app/pipeline/__init__.py`
8. `backend/app/pipeline/orchestrator.py` - Main orchestrator
9. `backend/app/api/routes/health.py` - Health checks
10. `backend/alembic/versions/007_add_contract_type_and_state.py`

**Modified:**
11. `backend/app/api/routes/contracts.py` - Add upload + status endpoints
12. `backend/app/main.py` - Register all routers, add CORS
13. `backend/app/db/models.py` - Add contract_type, state columns
14. `backend/requirements.txt` - Ensure all deps

**Tests:**
15. `backend/tests/test_full_pipeline.py` - Integration tests
16. `backend/tests/conftest.py` - Test fixtures

### Frontend

**New:**
17. `frontend/Dockerfile` - Frontend container
18. `frontend/nginx.conf` - Nginx configuration
19. `frontend/.dockerignore`

**Modified:**
20. `frontend/vite.config.ts` - Proxy config for dev
21. `frontend/src/App.tsx` - Add all routes

**Tests:**
22. `frontend/e2e/full-flow.spec.ts` - E2E tests

## Success Criteria

**Backend:**
- [ ] POST /api/contracts/upload triggers full pipeline
- [ ] Pipeline executes stages 2-9 in sequence
- [ ] Status updates at each stage
- [ ] GET /api/contracts/{id}/status returns accurate progress
- [ ] GET /api/contracts/{id}/report returns complete data
- [ ] Health checks respond correctly
- [ ] Docker container builds and runs
- [ ] Database migrations run automatically

**Frontend:**
- [ ] Upload page functional
- [ ] Status polling works
- [ ] Report view renders correctly
- [ ] PDF download works
- [ ] Docker container builds and runs
- [ ] Nginx routing configured

**Integration:**
- [ ] docker-compose up starts all services
- [ ] Services communicate correctly
- [ ] Database initialized with seed data
- [ ] Full upload-to-report flow works end-to-end
- [ ] README instructions accurate

**Testing:**
- [ ] Integration tests pass
- [ ] E2E tests pass
- [ ] Health checks verify system ready


## Notes

- This spec integrates all 9 previous stages into a working system
- docker-compose provides one-command startup: `docker-compose up`
- Backend pipeline runs asynchronously (non-blocking uploads)
- Status polling enables frontend progress tracking
- Health checks support Docker health monitoring
- Production deployment requires replacing sample legal data
- Use Conventional Commits: `feat:` for integration work, `chore:` for Docker config

## References

- Docker Compose: https://docs.docker.com/compose/
- FastAPI Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- PostgreSQL pgvector: https://github.com/pgvector/pgvector
- Nginx: https://nginx.org/en/docs/
- React Router: https://reactrouter.com/

## Complete System Architecture

\`\`\`
┌─────────────────────────────────────────────────────────────────┐
│                          User Browser                           │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                      │
│  • Upload page                    Port 3000                     │
│  • Status polling                                               │
│  • Report view with highlights                                  │
│  • PDF download                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                            │
│  • Upload endpoint                Port 8000                     │
│  • Pipeline orchestrator                                        │
│  • Status tracking                                              │
│  • Report assembly                                              │
│  • PDF generation                                               │
└─────────┬─────────────┬─────────────┬─────────────┬────────────┘
          │             │             │             │
          │             │             │             │
   ┌──────▼──────┐  ┌──▼───────┐  ┌─▼──────────┐  ▼
   │  PostgreSQL │  │   LLM    │  │  Embedding │  File
   │  +pgvector  │  │   API    │  │    API     │  Storage
   │             │  │          │  │            │
   │ • contracts │  │ Claude/  │  │  OpenAI    │  uploads/
   │ • clauses   │  │ OpenAI   │  │            │  temp/
   │ • findings  │  │          │  │            │
   │ • legal_kb  │  └──────────┘  └────────────┘
   │ • corpus    │
   └─────────────┘
\`\`\`

## Deployment Checklist

### Development
- [x] All specs completed (Stages 1-9)
- [x] Docker configuration ready
- [x] docker-compose.yml complete
- [x] README with setup instructions
- [ ] Run `docker-compose up` and verify
- [ ] Test full upload-to-report flow
- [ ] Verify all API endpoints
- [ ] Run integration tests
- [ ] Run E2E tests

### Production Preparation
- [ ] Replace sample legal data with verified content
- [ ] Legal review of all knowledge base entries
- [ ] Set up secrets management (AWS Secrets Manager, etc.)
- [ ] Configure SSL/TLS certificates
- [ ] Set up monitoring (Prometheus, Grafana)
- [ ] Configure logging (ELK stack, CloudWatch)
- [ ] Set up backup strategy (automated DB backups)
- [ ] Load testing (verify performance at scale)
- [ ] Security audit
- [ ] Compliance review
- [ ] Documentation for users
- [ ] Terms of service and privacy policy
- [ ] Disaster recovery plan

### Production Deployment
- [ ] Set up production database (managed PostgreSQL)
- [ ] Configure production environment variables
- [ ] Deploy backend (ECS, Kubernetes, etc.)
- [ ] Deploy frontend (S3 + CloudFront, etc.)
- [ ] Set up CDN for static assets
- [ ] Configure domain and DNS
- [ ] Set up CI/CD pipeline
- [ ] Configure rate limiting
- [ ] Set up alerting
- [ ] Launch! 🚀

---

**Status**: All 10 specs complete. System architecture fully defined from upload to report. Ready for implementation! 🎉
