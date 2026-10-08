"""
Contract upload and listing endpoints.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Contract, User
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
        HTTPException: 400 if file type invalid or size exceeds limit
    """
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
