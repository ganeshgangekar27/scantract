"""
Full pipeline orchestration for contract processing.

Coordinates all stages from upload through explanation generation.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.models import Contract, RiskFinding
from app.llm.classify_clauses import classify_all_clauses
from app.llm.detect_risk import detect_risks
from app.llm.generate_explanations import generate_all_explanations
from app.utils.error_handling import friendly_error

logger = logging.getLogger(__name__)


async def run_full_pipeline(
    contract_id: int,
    db: AsyncSession
) -> None:
    """
    Run the full contract processing pipeline after segmentation.
    
    Pipeline stages:
    1. Classification (Stage 4) - classify all clauses
    2. Risk Detection (Stage 7) - detect risky/missing clauses
    3. Explanation Generation (Stage 8) - generate plain-language explanations
    
    Updates pipeline_stage after each stage. If any stage fails, sets
    failed_stage and error_message, then stops the pipeline.
    
    Args:
        contract_id: Contract ID to process
        db: Database session
        
    Raises:
        ValueError: If contract not found or not in correct stage
    """
    logger.info(f"Starting full pipeline for contract {contract_id}")
    
    # Load contract
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")
    
    try:
        # Stage 4: Classification
        await _run_classification_stage(contract, db)
        
        # Stage 7: Risk Detection
        await _run_risk_detection_stage(contract, db)
        
        # Stage 8: Explanation Generation
        await _run_explanation_stage(contract, db)
        
        # Mark as completed
        contract.pipeline_stage = 'completed'
        contract.processing_status = 'completed'
        contract.failed_stage = None
        contract.error_message = None
        await db.commit()
        
        logger.info(f"✅ Full pipeline completed successfully for contract {contract_id}")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed for contract {contract_id}: {e}", exc_info=True)
        # If the stage handlers didn't catch it, or contract not yet failed, mark as failed
        if contract.pipeline_stage != 'failed':
            contract.pipeline_stage = 'failed'
            contract.processing_status = 'failed'
            if not contract.error_message:
                contract.error_message = friendly_error(e)
            # Leave failed_stage as is if already set
            try:
                await db.commit()
            except Exception:
                await db.rollback()
                await db.commit()
        raise


async def _run_classification_stage(contract: Contract, db: AsyncSession) -> None:
    """
    Run Stage 4: Clause Classification.
    
    Args:
        contract: Contract object
        db: Database session
        
    Raises:
        Exception: If classification fails
    """
    try:
        logger.info(f"[Contract {contract.id}] Starting Stage 4: Classification")
        
        # Update stage
        contract.pipeline_stage = 'classifying'
        await db.commit()
        
        # Run classification
        stats = await classify_all_clauses(
            contract_id=contract.id,
            contract_type=contract.contract_type,
            db=db
        )
        
        logger.info(
            f"[Contract {contract.id}] Classification complete: "
            f"{stats['successful']}/{stats['total']} successful, "
            f"{stats['total_tokens']} tokens"
        )
        
        # Check if any clauses classified
        if stats['successful'] == 0:
            # Include first error for diagnosis
            error_msg = f"Classification failed: 0/{stats['total']} clauses classified"
            if stats.get('first_error'):
                error_msg += f" (first error: {stats['first_error']})"
            raise RuntimeError(error_msg)
        
        # Update stage
        contract.pipeline_stage = 'classified'
        await db.commit()
        
    except Exception as e:
        contract.pipeline_stage = 'failed'
        contract.processing_status = 'failed'
        contract.failed_stage = 'classifying'
        contract.error_message = friendly_error(e)
        await db.commit()
        raise


async def _run_risk_detection_stage(contract: Contract, db: AsyncSession) -> None:
    """
    Run Stage 7: Risk Detection.
    
    Args:
        contract: Contract object
        db: Database session
        
    Raises:
        Exception: If risk detection fails
    """
    try:
        logger.info(f"[Contract {contract.id}] Starting Stage 7: Risk Detection")
        
        # Update stage
        contract.pipeline_stage = 'detecting_risks'
        await db.commit()
        
        # Run risk detection
        result = await detect_risks(
            contract_id=str(contract.id),
            db=db
        )
        
        logger.info(
            f"[Contract {contract.id}] Risk detection complete: "
            f"{result.total_risks} risky clauses, "
            f"{result.total_missing} missing clauses, "
            f"{result.high_severity_count} high severity"
        )
        
        # Update stage
        contract.pipeline_stage = 'risks_detected'
        await db.commit()
        
    except Exception as e:
        contract.pipeline_stage = 'failed'
        contract.processing_status = 'failed'
        contract.failed_stage = 'detecting_risks'
        contract.error_message = friendly_error(e)
        await db.commit()
        raise


async def _run_explanation_stage(contract: Contract, db: AsyncSession) -> None:
    """
    Run Stage 8: Explanation Generation.
    
    Args:
        contract: Contract object
        db: Database session
        
    Raises:
        Exception: If explanation generation fails
    """
    try:
        logger.info(f"[Contract {contract.id}] Starting Stage 8: Explanation Generation")
        
        # Update stage
        contract.pipeline_stage = 'generating_explanations'
        await db.commit()
        
        # Generate explanations
        count = await generate_all_explanations(
            contract_id=contract.id,
            db=db
        )
        
        logger.info(
            f"[Contract {contract.id}] Explanation generation complete: "
            f"{count} explanations generated"
        )
        
        # Verify all findings have valid explanations
        from app.llm.generate_explanations import parse_explanation, validate_explanation
        result = await db.execute(select(RiskFinding).where(RiskFinding.contract_id == contract.id))
        findings = result.scalars().all()
        
        missing_count = 0
        for finding in findings:
            if finding.explanation is None:
                missing_count += 1
            else:
                parsed = parse_explanation(finding.explanation)
                if not validate_explanation(parsed):
                    missing_count += 1
        
        if missing_count > 0:
            # Some explanations are missing or invalid
            contract.pipeline_stage = 'failed'
            contract.processing_status = 'failed'
            contract.failed_stage = 'generating_explanations'
            error_msg = f"Explanations missing or invalid for {missing_count} finding(s)"
            contract.error_message = friendly_error(error_msg)
            await db.commit()
            raise RuntimeError(error_msg)
        
        # All explanations valid, proceed
        contract.pipeline_stage = 'explanations_generated'
        await db.commit()
        
    except Exception as e:
        # If not already set to failed above
        if contract.pipeline_stage != 'failed':
            contract.pipeline_stage = 'failed'
            contract.processing_status = 'failed'
            contract.failed_stage = 'generating_explanations'
            contract.error_message = friendly_error(e)
            await db.commit()
        raise

