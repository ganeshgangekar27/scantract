"""
Legal rules similarity search with state-aware filtering.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from db.legal_kb.models import LegalRule, LegalRuleSearchResult
from rag.embeddings import embed_text
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def search_legal_rules(
    clause_text: str,
    db: AsyncSession,
    state: Optional[str] = None,
    contract_type: Optional[str] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> list[LegalRuleSearchResult]:
    """
    Search legal rules using semantic similarity with state-aware filtering.
    
    State filtering logic:
    - If state provided (e.g., "MH"): Returns state-specific rules OR central rules (state IS NULL)
    - If state is None: Returns ONLY central rules (state IS NULL)
    
    Args:
        clause_text: Clause text to search for similar legal rules
        state: State code (e.g., "MH", "KA", "DL", "TN") or None for central laws only
        contract_type: Contract type ("rental" or "freelance") - reserved for future use
        top_k: Maximum number of results to return
        similarity_threshold: Minimum similarity score (0.0-1.0) to include
        db: SQLAlchemy async session
    
    Returns:
        List of LegalRuleSearchResult with similarity scores, ordered by similarity desc
    """
    # Handle empty query
    if not clause_text or not clause_text.strip():
        logger.warning("Empty clause_text provided to search_legal_rules")
        return []
    
    logger.info(
        f"Searching legal rules: state={state}, top_k={top_k}, "
        f"threshold={similarity_threshold}, clause_length={len(clause_text)}"
    )
    
    try:
        # Generate embedding for query
        query_embedding = await embed_text(clause_text)
        
        # Build SQLAlchemy query with cosine distance
        # Note: cosine_distance returns 0.0 for identical vectors, 2.0 for opposite
        distance_expr = LegalRule.embedding.cosine_distance(query_embedding)
        
        # Start building query
        query = select(
            LegalRule,
            distance_expr.label('distance')
        )
        
        # Apply state filtering logic
        if state is not None:
            # State provided: include state-specific rules OR central rules
            query = query.where(
                or_(
                    LegalRule.state == state,
                    LegalRule.state.is_(None)
                )
            )
            logger.debug(f"Filtering: state={state} OR state IS NULL")
        else:
            # No state: include ONLY central rules
            query = query.where(LegalRule.state.is_(None))
            logger.debug("Filtering: state IS NULL (central laws only)")
        
        # Order by similarity (closest first) and limit
        query = query.order_by(distance_expr).limit(top_k)
        
        # Execute query
        result = await db.execute(query)
        rows = result.all()
        
        # Convert results to LegalRuleSearchResult with similarity scores
        search_results = []
        for row in rows:
            rule = row[0]  # LegalRule object
            distance = row[1]  # distance value
            
            # Convert distance to similarity: similarity = 1.0 - distance
            # For cosine distance: 0.0 = identical (similarity 1.0), 2.0 = opposite (similarity -1.0)
            similarity = 1.0 - distance
            
            # Filter by similarity threshold
            if similarity >= similarity_threshold:
                search_results.append(
                    LegalRuleSearchResult(
                        id=rule.id,
                        state=rule.state,
                        act_name=rule.act_name,
                        section_reference=rule.section_reference,
                        rule_text=rule.rule_text,
                        similarity=similarity
                    )
                )
        
        logger.info(
            f"Found {len(search_results)} legal rules above threshold "
            f"(out of {len(rows)} total matches)"
        )
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching legal rules: {e}")
        raise

