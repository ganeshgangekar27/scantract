"""
API endpoints for explanation generation and retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
import logging

from ...llm.generate_explanations import get_contract_explanations, generate_all_explanations
from ...llm.models import ContractExplanationsResponse
from ...db.models import RiskFinding
from ...db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contracts", tags=["explanations"])


@router.get("/{contract_id}/explanations")
async def get_explanations(
    contract_id: int,
    auto_generate: bool = True,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get all risk findings with explanations for a contract.
    
    Args:
        contract_id: Contract ID (INTEGER)
        auto_generate: Generate missing explanations on-the-fly (default: True)
        db: Database session
    
    Returns:
        {
            "success": true,
            "data": {
                "contract_id": 1,
                "risky_clauses": [...],
                "missing_clauses": [...],
                "summary": {...}
            },
            "error": null
        }
    
    Notes:
        - Explanations are cached after first generation
        - Citations are deterministically formatted (never LLM-generated)
        - All citations traceable to Stage 7 findings
    """
    try:
        result = await get_contract_explanations(
            contract_id=contract_id,
            db=db,
            auto_generate=auto_generate
        )
        
        return {
            "success": True,
            "data": result.model_dump(),
            "error": None
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        logger.error(f"Failed to get explanations for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{contract_id}/explanations/regenerate")
async def regenerate_explanations(
    contract_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Regenerate all explanations for a contract.
    
    Clears cached explanations and regenerates from scratch.
    Useful if explanation quality needs improvement.
    
    Args:
        contract_id: Contract ID (INTEGER)
        db: Database session
    
    Returns:
        {
            "success": true,
            "data": {"regenerated_count": 5},
            "error": null
        }
    """
    try:
        # Clear cached explanations
        await db.execute(
            update(RiskFinding)
            .where(RiskFinding.contract_id == contract_id)
            .values(explanation=None, explanation_generated_at=None)
        )
        await db.commit()
        
        # Regenerate all
        count = await generate_all_explanations(contract_id, db)
        
        return {
            "success": True,
            "data": {"regenerated_count": count},
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Failed to regenerate explanations for contract {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
