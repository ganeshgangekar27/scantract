"""
API endpoints for manual pipeline stage triggering.

These endpoints allow manual/debug triggering of individual pipeline stages
on existing contracts.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import Contract
from app.llm.classify_clauses import classify_all_clauses
from app.llm.detect_risk import detect_risks
from app.llm.generate_explanations import generate_all_explanations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["pipeline"])


class PipelineStatusResponse(BaseModel):
    """Response model for pipeline stage operations."""
    success: bool
    contract_id: int
    pipeline_stage: str
    processing_status: str
    message: str
    details: dict | None = None
    error: str | None = None


@router.post("/{contract_id}/classify", response_model=PipelineStatusResponse)
async def trigger_classification(
    contract_id: int,
    db: AsyncSession = Depends(get_db)
) -> PipelineStatusResponse:
    """
    Manually trigger clause classification for a contract.
    
    Useful for:
    - Re-classifying contracts after model improvements
    - Debugging classification issues
    - Processing stuck contracts
    
    Args:
        contract_id: Contract ID (INTEGER)
        db: Database session
    
    Returns:
        PipelineStatusResponse with current stage and classification stats
    """
    try:
        # Load contract
        result = await db.execute(select(Contract).where(Contract.id == contract_id))
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
        
        logger.info(f"Manual classification trigger for contract {contract_id}")
        
        # Update stage
        contract.pipeline_stage = 'classifying'
        await db.commit()
        
        # Run classification
        stats = await classify_all_clauses(
            contract_id=contract_id,
            contract_type=contract.contract_type,
            db=db
        )
        
        # Update stage
        contract.pipeline_stage = 'classified'
        await db.commit()
        
        # Refresh to get updated fields
        await db.refresh(contract)
        
        return PipelineStatusResponse(
            success=True,
            contract_id=contract_id,
            pipeline_stage=contract.pipeline_stage,
            processing_status=contract.processing_status,
            message=f"Classification completed: {stats['successful']}/{stats['total']} clauses",
            details=stats
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Classification failed for contract {contract_id}: {e}", exc_info=True)
        
        # Update contract with failure
        try:
            result = await db.execute(select(Contract).where(Contract.id == contract_id))
            contract = result.scalar_one_or_none()
            if contract:
                contract.pipeline_stage = 'failed'
                contract.failed_stage = 'classifying'
                contract.error_message = str(e)
                await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update contract status: {db_error}")
        
        return PipelineStatusResponse(
            success=False,
            contract_id=contract_id,
            pipeline_stage='failed',
            processing_status='failed',
            message="Classification failed",
            error=str(e)
        )


@router.post("/{contract_id}/detect-risks", response_model=PipelineStatusResponse)
async def trigger_risk_detection(
    contract_id: int,
    db: AsyncSession = Depends(get_db)
) -> PipelineStatusResponse:
    """
    Manually trigger risk detection for a contract.
    
    Prerequisites:
    - Contract must have classified clauses
    
    Args:
        contract_id: Contract ID (INTEGER)
        db: Database session
    
    Returns:
        PipelineStatusResponse with current stage and risk detection stats
    """
    try:
        # Load contract
        result = await db.execute(select(Contract).where(Contract.id == contract_id))
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
        
        logger.info(f"Manual risk detection trigger for contract {contract_id}")
        
        # Update stage
        contract.pipeline_stage = 'detecting_risks'
        await db.commit()
        
        # Run risk detection
        risk_result = await detect_risks(
            contract_id=str(contract_id),
            db=db
        )
        
        # Update stage
        contract.pipeline_stage = 'risks_detected'
        await db.commit()
        
        # Refresh to get updated fields
        await db.refresh(contract)
        
        return PipelineStatusResponse(
            success=True,
            contract_id=contract_id,
            pipeline_stage=contract.pipeline_stage,
            processing_status=contract.processing_status,
            message=f"Risk detection completed: {risk_result.total_risks} risky, {risk_result.total_missing} missing",
            details={
                "total_risks": risk_result.total_risks,
                "total_missing": risk_result.total_missing,
                "high_severity": risk_result.high_severity_count,
                "medium_severity": risk_result.medium_severity_count,
                "low_severity": risk_result.low_severity_count
            }
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Risk detection failed for contract {contract_id}: {e}", exc_info=True)
        
        # Update contract with failure
        try:
            result = await db.execute(select(Contract).where(Contract.id == contract_id))
            contract = result.scalar_one_or_none()
            if contract:
                contract.pipeline_stage = 'failed'
                contract.failed_stage = 'detecting_risks'
                contract.error_message = str(e)
                await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update contract status: {db_error}")
        
        return PipelineStatusResponse(
            success=False,
            contract_id=contract_id,
            pipeline_stage='failed',
            processing_status='failed',
            message="Risk detection failed",
            error=str(e)
        )


@router.post("/{contract_id}/generate-explanations", response_model=PipelineStatusResponse)
async def trigger_explanation_generation(
    contract_id: int,
    db: AsyncSession = Depends(get_db)
) -> PipelineStatusResponse:
    """
    Manually trigger explanation generation for a contract.
    
    Note: This endpoint provides the same functionality as the existing
    POST /api/contracts/{id}/explanations/regenerate endpoint, but with
    a different response format that includes pipeline stage information.
    
    Use this endpoint for:
    - Pipeline orchestration and debugging
    - Getting detailed stage information
    
    Use /explanations/regenerate for:
    - Simple explanation regeneration
    - When you only need the count of regenerated explanations
    
    Prerequisites:
    - Contract must have risk findings
    
    Args:
        contract_id: Contract ID (INTEGER)
        db: Database session
    
    Returns:
        PipelineStatusResponse with current stage and explanation generation stats
    """
    try:
        # Load contract
        result = await db.execute(select(Contract).where(Contract.id == contract_id))
        contract = result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"Contract {contract_id} not found")
        
        logger.info(f"Manual explanation generation trigger for contract {contract_id}")
        
        # Update stage
        contract.pipeline_stage = 'generating_explanations'
        await db.commit()
        
        # Generate explanations
        count = await generate_all_explanations(
            contract_id=contract_id,
            db=db
        )
        
        # Update stage
        contract.pipeline_stage = 'explanations_generated'
        await db.commit()
        
        # Refresh to get updated fields
        await db.refresh(contract)
        
        return PipelineStatusResponse(
            success=True,
            contract_id=contract_id,
            pipeline_stage=contract.pipeline_stage,
            processing_status=contract.processing_status,
            message=f"Explanation generation completed: {count} explanations generated",
            details={"explanations_generated": count}
        )
        
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Explanation generation failed for contract {contract_id}: {e}", exc_info=True)
        
        # Update contract with failure
        try:
            result = await db.execute(select(Contract).where(Contract.id == contract_id))
            contract = result.scalar_one_or_none()
            if contract:
                contract.pipeline_stage = 'failed'
                contract.failed_stage = 'generating_explanations'
                contract.error_message = str(e)
                await db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update contract status: {db_error}")
        
        return PipelineStatusResponse(
            success=False,
            contract_id=contract_id,
            pipeline_stage='failed',
            processing_status='failed',
            message="Explanation generation failed",
            error=str(e)
        )
