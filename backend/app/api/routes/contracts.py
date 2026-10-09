"""
Contract upload and listing endpoints.
"""
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select, func, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Contract, User, Clause, RiskFinding
from app.document_processing.processor import process_contract
from app.auth.dependencies import get_current_user


router = APIRouter()


class UploadResponse(BaseModel):
    """Response model for contract upload matching Stage 1 frontend expectations."""
    contract_id: int  # INTEGER, not UUID
    filename: str
    size: int  # bytes
    upload_timestamp: datetime
    status: str  # 'uploaded'


class ContractListItem(BaseModel):
    """Response model for contract list item."""
    contract_id: int
    filename: str
    uploaded_at: datetime
    processing_status: str  # 'uploaded', 'processing', 'completed', 'failed'
    pipeline_stage: Optional[str]  # 'extraction', 'segmentation', etc.
    failed_stage: Optional[str]
    error_message: Optional[str]
    is_sample: bool  # True if this is a shared sample contract


# Configuration from environment
UPLOAD_DIR = os.getenv("UPLOAD_TEMP_DIR", "./uploads/temp")
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "15"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_UPLOADS_PER_DAY = int(os.getenv("MAX_UPLOADS_PER_DAY", "3"))

# Ensure upload directory exists
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def validate_file_type(filename: str) -> None:
    """
    Validate if file type is supported (.pdf or .docx).
    
    Args:
        filename: Name of uploaded file
        
    Raises:
        HTTPException: If file type is not supported
    """
    if not filename.lower().endswith(('.pdf', '.docx')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and DOCX files are supported."
        )


def validate_file_size(size: int) -> None:
    """
    Validate if file size is within allowed limit.
    
    Args:
        size: File size in bytes
        
    Raises:
        HTTPException: If file exceeds size limit
    """
    if size > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {MAX_UPLOAD_SIZE_MB}MB"
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UploadResponse:
    """
    Upload a contract file (PDF or DOCX) for processing.
    
    - Validates file type (.pdf, .docx only)
    - Validates file size (max 15MB)
    - Checks daily upload limit (MAX_UPLOADS_PER_DAY)
    - Saves to local temp/uploads directory
    - Creates Contract DB entry with status='uploaded'
    - Kicks off background extraction task
    - Returns contract_id (int), filename, size, upload_timestamp immediately
    
    Args:
        file: Uploaded file (multipart/form-data)
        background_tasks: FastAPI background tasks manager
        db: Database session
        
    Returns:
        UploadResponse with contract_id (int), filename, size, timestamp, status
        
    Raises:
        HTTPException: 400 if file type invalid or size exceeds limit, 429 if daily limit exceeded
    """
    # Check daily upload limit
    if await check_daily_upload_limit(current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily upload limit reached. Sample contracts are always available."
        )
    
    # Validate file type
    validate_file_type(file.filename)
    
    # Read file content and validate size
    file_content = await file.read()
    file_size = len(file_content)
    validate_file_size(file_size)
    
    # Generate unique filename: {timestamp}_{uuid}_{original_name}
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    unique_filename = f"{timestamp}_{unique_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file to disk
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    # Create Contract row
    contract = Contract(
        contract_type='rental',  # Default to 'rental' for uploaded contracts
        filename=file.filename,
        file_path=file_path,
        uploaded_at=datetime.utcnow(),
        processing_status='uploaded',
        user_id=current_user.id
    )
    
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    
    # Queue background processing task (don't await)
    background_tasks.add_task(process_contract, contract.id, file_path, db)
    
    # Return response immediately
    return UploadResponse(
        contract_id=contract.id,
        filename=file.filename,
        size=file_size,
        upload_timestamp=contract.uploaded_at,
        status=contract.processing_status
    )


@router.get("/list", response_model=List[ContractListItem])
async def list_contracts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ContractListItem]:
    """
    List user's contracts and all sample contracts.
    
    Returns user's own contracts first (newest first), then all sample contracts.
    Does not return other users' private contracts or legacy contracts.
    
    Returns:
        List of contracts with id, filename, upload date, status, and is_sample flag
    """
    # Get user's own contracts
    user_result = await db.execute(
        select(Contract)
        .where(Contract.user_id == current_user.id)
        .order_by(Contract.uploaded_at.desc())
    )
    user_contracts = user_result.scalars().all()
    
    # Get all sample contracts
    sample_result = await db.execute(
        select(Contract)
        .where(Contract.is_sample == True)
        .order_by(Contract.uploaded_at.desc())
    )
    sample_contracts = sample_result.scalars().all()
    
    # Combine: user's contracts first, then samples
    all_contracts = list(user_contracts) + list(sample_contracts)
    
    return [
        ContractListItem(
            contract_id=c.id,
            filename=c.filename,
            uploaded_at=c.uploaded_at,
            processing_status=c.processing_status,
            pipeline_stage=c.pipeline_stage,
            failed_stage=c.failed_stage,
            error_message=c.error_message,
            is_sample=c.is_sample
        )
        for c in all_contracts
    ]



class StatsResponse(BaseModel):
    """Response model for contract stats."""
    total: int
    completed: int
    processing: int
    failed: int


@router.get("/stats")
async def get_contract_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get contract statistics for the current user.
    
    Returns counts for total, completed, processing, and failed contracts.
    Excludes sample contracts.
    
    Returns:
        Dict with success and data containing stats
    """
    # Get all user's non-sample contracts
    result = await db.execute(
        select(Contract)
        .where(Contract.user_id == current_user.id)
        .where(Contract.is_sample == False)
    )
    contracts = result.scalars().all()
    
    total = len(contracts)
    completed = sum(1 for c in contracts if c.processing_status == 'completed')
    processing = sum(1 for c in contracts if c.processing_status in ['uploaded', 'processing'])
    failed = sum(1 for c in contracts if c.processing_status == 'failed')
    
    return {
        "success": True,
        "data": {
            "total": total,
            "completed": completed,
            "processing": processing,
            "failed": failed
        }
    }


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a contract and all related data.
    
    - Verifies ownership (owner-only)
    - Refuses if contract is processing (409)
    - Never allows deletion of sample contracts (404)
    - Deletes risk_findings, clauses, and contract row via cascade
    - Deletes stored file if it exists
    
    Args:
        contract_id: Contract ID to delete
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Success response
        
    Raises:
        HTTPException: 404 if not found/not owner/sample, 409 if processing
    """
    # Get contract
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    # Return 404 for: non-existent, not owner, or sample
    if not contract or contract.user_id != current_user.id or contract.is_sample:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Refuse if processing
    if contract.processing_status in ['processing', 'uploaded']:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete contract while it is processing"
        )
    
    # Delete related data (cascade will handle risk_findings and clauses)
    # But we'll be explicit for clarity
    await db.execute(
        sql_delete(RiskFinding).where(RiskFinding.contract_id == contract_id)
    )
    await db.execute(
        sql_delete(Clause).where(Clause.contract_id == contract_id)
    )
    
    # Delete stored file if it exists
    if contract.file_path and os.path.exists(contract.file_path):
        try:
            os.remove(contract.file_path)
        except Exception:
            pass  # File deletion failure shouldn't block contract deletion
    
    # Delete contract
    await db.delete(contract)
    await db.commit()
    
    return {"success": True, "message": "Contract deleted successfully"}


@router.post("/{contract_id}/retry", status_code=202)
async def retry_contract(
    contract_id: int,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry processing a failed contract.
    
    - Only works when processing_status == 'failed'
    - Resets contract to 'uploaded' status
    - Queues reprocessing via the same pipeline
    - Returns 202-style response
    
    Args:
        contract_id: Contract ID to retry
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Authenticated user
        
    Returns:
        202 response with contract_id
        
    Raises:
        HTTPException: 404 if not found/not owner/sample, 409 if not failed
    """
    # Get contract
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id)
    )
    contract = result.scalar_one_or_none()
    
    # Return 404 for: non-existent, not owner, or sample
    if not contract or contract.user_id != current_user.id or contract.is_sample:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Can only retry failed contracts
    if contract.processing_status != 'failed':
        raise HTTPException(
            status_code=409,
            detail="Can only retry contracts that have failed processing"
        )
    
    # Reset contract status
    contract.processing_status = 'uploaded'
    contract.pipeline_stage = 'uploaded'  # Set to initial stage
    contract.failed_stage = None
    contract.error_message = None
    await db.commit()
    
    # Queue reprocessing
    background_tasks.add_task(process_contract, contract.id, contract.file_path, db)
    
    return {
        "success": True,
        "data": {
            "contract_id": contract.id,
            "status": "queued",
            "message": "Contract reprocessing queued"
        }
    }


async def check_daily_upload_limit(
    user_id: int,
    db: AsyncSession
) -> bool:
    """
    Check if user has exceeded daily upload limit.
    
    Args:
        user_id: User ID to check
        db: Database session
        
    Returns:
        True if limit exceeded, False otherwise
    """
    # Count uploads in last 24 hours
    cutoff_time = datetime.utcnow() - timedelta(days=1)
    result = await db.execute(
        select(func.count(Contract.id))
        .where(Contract.user_id == user_id)
        .where(Contract.uploaded_at >= cutoff_time)
    )
    count = result.scalar()
    
    return count >= MAX_UPLOADS_PER_DAY
