FROM python:3.11-slim

# Install system dependencies for PDF generation and OCR
# IMPORTANT: PDF generation via weasyprint is UNTESTED on Linux and will need
# verification once container is built. If it fails, consider alternative PDF
# libraries (reportlab, xhtml2pdf) or debug GTK/Pango configuration.
RUN apt-get update && apt-get install -y \
    # GTK dependencies for weasyprint PDF generation
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    # PaddleOCR dependencies
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads/temp

# Add /app to PYTHONPATH so seed scripts can import db, app, rag modules
ENV PYTHONPATH=/app

EXPOSE 8000

# Default command: run migrations, seed databases, then start server
# Uses PORT environment variable (defaults to 8000) for Render compatibility
CMD ["sh", "-c", "alembic upgrade head && python db/legal_kb/seed_legal_kb.py && python db/reference_corpus/seed_reference_corpus.py && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
