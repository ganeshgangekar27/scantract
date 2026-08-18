"""
API endpoints for contract risk report generation and retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from io import BytesIO
import logging
import re

from ...reports import assemble_contract_report, generate_pdf_report
from ...db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["reports"])


@router.get("/{contract_id}/report")
async def get_contract_report(
    contract_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get complete contract report (JSON).
    
    Args:
        contract_id: Contract ID (INTEGER)
        db: Database session
    
    Returns:
        {
            "success": true,
            "data": {
                "contract_id": 1,
                "filename": "lease.pdf",
                "all_clauses": [...],
                "risky_clauses": [...],
                "missing_clauses": [...],
                "risk_summary": {...},
                "legal_references": [...]
            },
            "error": null
        }
    """
    try:
        report = await assemble_contract_report(contract_id, db)
        
        return {
            "success": True,
            "data": report.model_dump(),
            "error": None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to get report for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{contract_id}/report/pdf")
async def get_contract_report_pdf(
    contract_id: int,
    db: AsyncSession = Depends(get_db)
) -> StreamingResponse:
    """
    Download contract report as PDF.
    
    Args:
        contract_id: Contract ID (INTEGER)
        db: Database session
    
    Returns:
        PDF file with Content-Disposition attachment header
    """
    try:
        # Assemble report
        report = await assemble_contract_report(contract_id, db)
        
        # Generate PDF
        pdf_bytes = generate_pdf_report(report)
        
        # Create sanitized filename
        safe_filename = _sanitize_filename(report.filename)
        filename = f"{safe_filename}_report.pdf"
        
        # Return streaming response
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except RuntimeError as e:
        # weasyprint not available (GTK libraries missing on Windows)
        logger.error(f"PDF generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="PDF generation unavailable. GTK libraries required on Windows."
        )
    
    except Exception as e:
        logger.error(f"Failed to generate PDF for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize contract filename for use in PDF filename.
    
    Removes file extension and special characters.
    """
    # Remove file extension
    name = filename.rsplit('.', 1)[0]
    
    # Replace spaces and special characters with underscores
    name = re.sub(r'[^\w\-]', '_', name)
    
    # Remove consecutive underscores
    name = re.sub(r'_+', '_', name)
    
    # Trim underscores from start/end
    name = name.strip('_')
    
    # Limit length
    if len(name) > 50:
        name = name[:50]
    
    return name or "contract"
