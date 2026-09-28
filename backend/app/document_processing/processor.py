"""
Background contract processing orchestration.
"""
import logging
import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Contract, Clause
from app.document_processing.extractor import extract_text_from_pdf, extract_text_from_docx
from app.document_processing.normalizer import clean_and_normalize
from app.document_processing.segmenter import segment_clauses
from app.document_processing.orchestrator import run_full_pipeline


logger = logging.getLogger(__name__)


async def process_contract(
    contract_id: int,
    file_path: str,
    db: AsyncSession
) -> None:
    """
    Background task to process uploaded contract.
    
    Steps:
    1. Determine file type (.pdf or .docx)
    2. Extract text (extractor.py)
    3. Normalize text (normalizer.py)
    4. Segment into clauses (segmenter.py)
    5. Insert Clause rows linked to contract_id
    6. Update Contract:
       - full_text = normalized_text
       - page_count = extracted_page_count
       - processing_status = 'completed' or 'failed'
       - error_message if failed
    7. Clean up temp file (optional: keep for debugging)
    
    Args:
        contract_id: Database ID of contract to process
        file_path: Path to uploaded file
        db: Database session (note: this is passed but we need to create a new session)
        
    Note:
        This function is designed to run as a FastAPI BackgroundTask.
        All errors are caught and stored in the database rather than propagated.
        Creates its own database session since background tasks run outside request context.
    """
    from app.db.database import AsyncSessionLocal
    
    logger.info(f"Starting background processing for contract_id={contract_id}, file={file_path}")
    
    # Create new database session for background task
    async with AsyncSessionLocal() as db:
        try:
            # Update status to 'processing'
            result = await db.execute(select(Contract).where(Contract.id == contract_id))
            contract = result.scalar_one()
            contract.processing_status = 'processing'
            await db.commit()
            
            # Determine file type
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Extract text based on file type
            if file_extension == '.pdf':
                full_text, page_count = extract_text_from_pdf(file_path)
            elif file_extension == '.docx':
                full_text, page_count = extract_text_from_docx(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            logger.info(f"Extracted {len(full_text)} characters, {page_count} pages/paragraphs")
            
            # Normalize text
            normalized_text = clean_and_normalize(full_text)
            logger.info(f"Normalized to {len(normalized_text)} characters")
            
            # Segment into clauses
            clauses = segment_clauses(normalized_text)
            logger.info(f"Segmented into {len(clauses)} clauses")
            
            # Insert Clause rows
            for clause_dict in clauses:
                clause = Clause(
                    contract_id=contract_id,
                    clause_id=clause_dict['clause_number'],
                    position=clause_dict['position'],
                    text=clause_dict['clause_text']
                )
                db.add(clause)
            
            # Update Contract with results
            contract.full_text = normalized_text
            contract.page_count = page_count
            contract.processing_status = 'completed'
            contract.pipeline_stage = 'segmented'
            contract.error_message = None
            
            await db.commit()
            
            logger.info(f"Successfully processed contract_id={contract_id}: {len(clauses)} clauses created")
            
            # Run full pipeline (Stage 4 -> 7 -> 8)
            logger.info(f"Starting full pipeline orchestration for contract_id={contract_id}")
            await run_full_pipeline(contract_id, db)
            
            # Optional: Clean up temp file (commented out for debugging)
            # os.remove(file_path)
            
        except Exception as e:
            # Log error
            logger.error(f"Error processing contract_id={contract_id}: {str(e)}", exc_info=True)
            
            # Update contract status to 'failed'
            try:
                result = await db.execute(select(Contract).where(Contract.id == contract_id))
                contract = result.scalar_one()
                contract.processing_status = 'failed'
                contract.error_message = f"{type(e).__name__}: {str(e)}"
                await db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update contract status after error: {str(db_error)}")
