# Reports Module

This module handles contract risk report assembly and PDF generation for ScanTract.

## Modules

- **models.py**: Pydantic models for report data structures
- **assembler.py**: Report assembly logic - fetches contract data, clauses, risk findings, and builds complete ContractReport
- **pdf_generator.py**: PDF generation using weasyprint

## API Endpoints

Implemented in `backend/app/api/routes/reports.py`:

- `GET /api/contracts/{contract_id}/report` - Returns JSON report
- `GET /api/contracts/{contract_id}/report/pdf` - Returns PDF download

## PDF Generation - Platform Notes

**PDF generation requires GTK/Pango libraries not available on Windows by default.**

This is expected to work in the Dockerized deployment (Stage 10) since GTK installs cleanly via apt-get on Linux:

```dockerfile
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

**On Windows development machines:**
- ✅ The JSON report endpoint (`/api/contracts/{id}/report`) is fully functional
- ❌ The PDF endpoint will return HTTP 500 until either GTK is installed or this runs in Docker

**Error returned when GTK unavailable:**
```json
{
  "detail": "PDF generation unavailable. GTK libraries required on Windows."
}
```

This is by design - the JSON API provides all report data, and PDF generation is gracefully degraded when the native library dependencies are not available.

## Testing

Unit tests use mocks for PDF generation to avoid platform-specific GTK dependency:
- `backend/tests/test_reports.py` - Report assembly logic (6 tests)
- `backend/tests/test_api_reports.py` - API endpoints with mocked PDF generation (4 tests)
