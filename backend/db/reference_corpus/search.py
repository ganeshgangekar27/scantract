"""
Reference corpus semantic similarity search.

Search over reference contract clauses using pgvector cosine distance.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.reference_corpus.models import ReferenceClause, ReferenceClauseSearchResult
from rag.embeddings import embed_text
import logging

logger = logging.getLogger(__name__)


async def search_reference_corpus(
    clause_text: str,
    contract_type: str,
    db: AsyncSession,
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> list[ReferenceClauseSearchResult]:
    """
    Search reference corpus using semantic similarity with contract_type filtering.
    
    Args:
        clause_text: Clause text to search for similar reference clauses
        contract_type: Contract type to filter by ("rental" or "freelance")
        top_k: Maximum number of results to return
        similarity_threshold: Minimum similarity score (0.0-1.0) to include
        db: SQLAlchemy async session
    
    Returns:
        List of ReferenceClauseSearchResult with similarity scores, 
        ordered by similarity descending
    """
    # Handle empty query
    if not clause_text or not clause_text.strip():
        logger.warning("Empty clause_text provided to search_reference_corpus")
        return []
    
    logger.info(
        f"Searching reference corpus: contract_type={contract_type}, "
        f"top_k={top_k}, threshold={similarity_threshold}, "
        f"clause_length={len(clause_text)}"
    )
    
    try:
        # Generate embedding for query
        query_embedding = await embed_text(clause_text)
        
        # Build SQLAlchemy query with cosine distance
        # Note: cosine_distance returns 0.0 for identical vectors, 2.0 for opposite
        distance_expr = ReferenceClause.embedding.cosine_distance(query_embedding)
        
        # Build query with contract_type filter
        query = select(
            ReferenceClause,
            distance_expr.label('distance')
        ).where(
            ReferenceClause.contract_type == contract_type
        )
        
        # Order by similarity (closest first) and limit
        query = query.order_by(distance_expr).limit(top_k)
        
        logger.debug(f"Filtering: contract_type={contract_type}")
        
        # Execute query
        result = await db.execute(query)
        rows = result.all()
        
        # Convert results to ReferenceClauseSearchResult with similarity scores
        search_results = []
        for row in rows:
            clause = row[0]  # ReferenceClause object
            distance = row[1]  # distance value
            
            # Convert distance to similarity: similarity = 1.0 - distance
            # For cosine distance: 0.0 = identical (similarity 1.0), 2.0 = opposite (similarity -1.0)
            similarity = 1.0 - distance
            
            # Filter by similarity threshold
            if similarity >= similarity_threshold:
                search_results.append(
                    ReferenceClauseSearchResult(
                        id=clause.id,
                        contract_type=clause.contract_type,
                        clause_category=clause.clause_category,
                        clause_text=clause.clause_text,
                        source_label=clause.source_label,
                        similarity=similarity
                    )
                )
        
        logger.info(
            f"Found {len(search_results)} reference clauses above threshold "
            f"(out of {len(rows)} total matches)"
        )
        
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching reference corpus: {e}")
        raise

