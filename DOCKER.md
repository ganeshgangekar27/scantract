# ScanTract Docker Deployment Guide

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose v2.0 or higher
- API keys:
  - **REQUIRED:** Gemini API key (for embeddings)
  - **REQUIRED:** At least one LLM provider key (OpenAI, Claude, or Gemini)

## Quick Start

1. **Copy environment template:**
   ```bash
   cp .env.docker .env
   ```

2. **Edit `.env` file and add your API keys:**
   ```bash
   # Required
   GEMINI_API_KEY=your_actual_gemini_key
   OPENAI_API_KEY=your_actual_openai_key  # or CLAUDE_API_KEY, depending on LLM_PROVIDER

   # Optional: Change database password
   DB_PASSWORD=your_secure_password
   ```

3. **Build and start all services:**
   ```bash
   docker-compose up --build
   ```

4. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs

## Service Architecture

```
┌─────────────────┐
│   Frontend      │  Port 3000 (nginx)
│   (React+Vite)  │  Serves built static files
└────────┬────────┘  Proxies /api/* to backend
         │
         │ HTTP
         ▼
┌─────────────────┐
│   Backend       │  Port 8000 (uvicorn)
│   (FastAPI)     │  Runs migrations on startup
└────────┬────────┘  Seeds KB tables if empty
         │
         │ PostgreSQL
         ▼
┌─────────────────┐
│   Database      │  Port 5432 (PostgreSQL)
│   (pgvector)    │  Persistent volume: postgres_data
└─────────────────┘
```

## Configuration

### Environment Variables

All configuration is done via `.env` file. See `.env.docker` for template.

**Required:**
- `GEMINI_API_KEY` - Gemini API key (embeddings, **always required**)
- `OPENAI_API_KEY` or `CLAUDE_API_KEY` or `GEMINI_API_KEY` - LLM provider key

**Optional:**
- `LLM_PROVIDER` - Choose: `openai`, `claude`, `gemini` (default: `openai`)
- `LLM_BASE_URL` - Custom base URL (for OpenRouter, etc.)
- `OPENAI_MODEL` - Model name override (default: `gpt-3.5-turbo`)
- `DB_PASSWORD` - Database password (default: `devpass`)
- See `.env.docker` for full list

### ⚠️ IMPORTANT: Gemini Dependency

**Gemini API key is REQUIRED regardless of `LLM_PROVIDER` setting.**

The system uses Gemini for embeddings in risk detection, even when using OpenAI or Claude for text generation. If Gemini quota is exhausted, risk detection will fail.

- Gemini free tier: 60 requests/minute, 1500/day (embedding-specific)
- Full pipeline consumes 2 Gemini embedding calls per contract

## First-Time Setup

The backend container automatically performs the following on startup:

1. **Run Alembic migrations** - Creates/updates database schema
2. **Seed legal_rules table** - Inserts 53 sample Indian legal rules
3. **Seed reference_clauses table** - Inserts 40 sample reference clauses
4. **Start FastAPI server** - Listens on port 8000

All seed scripts are **idempotent** - safe to run multiple times, won't create duplicates.

## Development Workflow

### Rebuild after code changes

```bash
# Rebuild specific service
docker-compose build backend
docker-compose build frontend

# Restart services
docker-compose up backend frontend
```

### View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### Run backend tests

```bash
docker-compose exec backend pytest tests/ -v
```

### Access database

```bash
docker-compose exec db psql -U postgres -d scantract
```

### Stop all services

```bash
docker-compose down
```

### Stop and remove volumes (fresh start)

```bash
docker-compose down -v
```

## Troubleshooting

### Backend fails to start

**Check logs:**
```bash
docker-compose logs backend
```

**Common issues:**
1. **Missing API keys** - Ensure `.env` file has `GEMINI_API_KEY` and LLM provider key
2. **Database not ready** - Backend waits for DB healthcheck, should auto-retry
3. **Migration failure** - Check database connection string in `.env`

### Frontend shows blank page

1. **Check nginx logs:**
   ```bash
   docker-compose logs frontend
   ```

2. **Verify backend is running:**
   ```bash
   curl http://localhost:8000/docs
   ```

3. **Check browser console** - Look for CORS or network errors

### PDF download returns 500 error

**Status:** PDF generation via weasyprint is **UNTESTED on Linux Docker**.

If PDF download fails:
1. Check backend logs: `docker-compose logs backend`
2. Look for GTK/Pango errors
3. **Workaround:** Use JSON report endpoint instead:
   ```
   GET /api/contracts/{id}/report
   ```

If GTK is misconfigured, consider alternative PDF libraries (reportlab, xhtml2pdf).

### Gemini quota exhausted

**Error:** `429 Too Many Requests` or quota limit messages

**Solutions:**
1. Wait for daily/monthly quota reset
2. Upgrade to Gemini paid tier
3. Reduce batch sizes (process one contract at a time)

### Database connection refused

**Check database status:**
```bash
docker-compose ps db
docker-compose logs db
```

**Common fixes:**
- Ensure `DB_PASSWORD` matches in `.env` and `DATABASE_URL`
- Check port 5432 isn't already in use: `docker ps | grep 5432`

## Production Deployment

### Security Hardening

1. **Change default passwords:**
   ```bash
   # In .env
   DB_PASSWORD=use_strong_random_password_here
   ```

2. **Use secrets management** (e.g., Docker secrets, Kubernetes secrets, AWS Secrets Manager)

3. **Enable HTTPS** - Add reverse proxy (nginx, Traefik, Caddy)

4. **Add rate limiting** - Protect against abuse

5. **Restrict ports** - Remove public database port exposure in `docker-compose.yml`:
   ```yaml
   db:
     ports: []  # Remove or comment out "- 5432:5432"
   ```

### Performance Tuning

1. **Increase database resources:**
   ```yaml
   db:
     deploy:
       resources:
         limits:
           cpus: '2'
           memory: 4G
   ```

2. **Tune pgvector index** - Run `VACUUM ANALYZE` after seeding:
   ```bash
   docker-compose exec db psql -U postgres -d scantract -c "VACUUM ANALYZE legal_rules;"
   docker-compose exec db psql -U postgres -d scantract -c "VACUUM ANALYZE reference_clauses;"
   ```

3. **Adjust LLM concurrency:**
   ```bash
   # In .env
   LLM_CONCURRENCY_LIMIT=10  # Increase if you have quota
   ```

### Monitoring

Add health check endpoints:
- Backend: http://localhost:8000/health (if implemented)
- Database: Use `pg_isready` (already configured)

Recommended monitoring stack:
- Prometheus + Grafana for metrics
- ELK stack or Loki for log aggregation
- Sentry for error tracking

## Known Limitations

1. **PDF Generation Untested** - weasyprint + GTK on Linux Docker needs verification
2. **OCR Unavailable on Windows** - PaddleOCR only works in Docker (Linux)
3. **Gemini Dependency** - Cannot run without Gemini API key (embeddings)
4. **Free Tier Limits:**
   - OpenRouter: 50 requests/day
   - Gemini: 60/min, 1500/day (embeddings)
5. **Classification Accuracy:**
   - Provisionally 90.9% (n=11, unconfirmed at scale)
   - Free models have inherent semantic limitations

## Support

See `HANDOVER.md` for:
- Detailed architecture documentation
- Database schema
- API endpoint reference
- Test coverage status
- Known issues

For code structure and conventions:
- `.kiro/steering/tech.md` - Tech stack rules
- `.kiro/steering/product.md` - Product context
- `.kiro/steering/conventions.md` - Coding standards
