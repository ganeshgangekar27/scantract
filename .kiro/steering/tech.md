# Tech Stack Rules

- Frontend: React + Vite + TypeScript + Tailwind CSS. Functional components,
  hooks only, no class components.
- Backend: FastAPI (Python 3.11+), async endpoints, Pydantic v2 models for
  every request/response.
- DB: PostgreSQL + pgvector extension. Use SQLAlchemy (async) + Alembic for
  migrations. Never write raw psycopg without going through the ORM layer
  unless doing a pgvector similarity query.
- RAG orchestration: LangChain. Keep prompt templates in
  backend/rag/prompts/ as separate files, not inline strings.
- LLM calls: abstract behind a single `llm_client.py` so we can swap between
  Claude API and GPT API via an env var (LLM_PROVIDER).
- All secrets via .env / python-dotenv, never hardcoded.
- Every backend module needs type hints and docstrings.
- Containerize with Docker; docker-compose.yml should bring up frontend,
  backend, and postgres together.