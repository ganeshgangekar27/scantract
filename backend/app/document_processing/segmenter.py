"""
Clause segmentation logic.
"""
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def segment_clauses(text: str) -> List[Dict[str, any]]:
    """
    Segment normalized text into individual clauses with numbering and position.
    
    This function:
    - Detects numbered clause patterns (1., 1.1, (a), (i), etc.)
    - Falls back to paragraph-based segmentation if no numbering detected
    - Filters out empty clauses (< 20 characters)
    - Assigns sequential position numbers
    
    Args:
        text: Normalized contract text
        
    Returns:
        List of clause dictionaries with keys:
        - clause_number: str (e.g., "1", "1.1", "(a)", "P1")
        - clause_text: str
        - position: int (0-indexed)
    """
    logger.info(f"Starting clause segmentation: {len(text)} characters")
    
    # Pattern to detect numbered clauses at line start
    # Matches: 1. 2. 3. | 1.1 1.2 | (a) (b) | (i) (ii) (iii)
    # 
    # KNOWN LIMITATION: This pattern does not match three-level nested numbering
    # (e.g., "1.2.3"). Clauses using this depth of numbering will not be split at
    # that boundary and will merge into the preceding clause's text rather than
    # erroring. This is acceptable for the current scope since most rental/freelance
    # contracts use at most two levels of numbering (1, 1.1), but should be revisited
    # if real-world testing surfaces this pattern.
    clause_pattern = re.compile(
        r'^(\d+\.\d+\.?|\d+\.|\([a-z]\)|\([ivxIVX]+\))\s+',
        re.MULTILINE
    )
    
    matches = list(clause_pattern.finditer(text))
    
    clauses = []
    
    if matches:
        # Numbered clause detection
        logger.info(f"Detected {len(matches)} numbered clauses")
        
        for i, match in enumerate(matches):
            clause_number = match.group(1).strip()
            start_pos = match.end()
            
            # Text extends until next clause or end of document
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(text)
            
            clause_text = text[start_pos:end_pos].strip()
            
            # Filter out very short clauses (likely not real clauses)
            if len(clause_text) >= 20:
                clauses.append({
                    'clause_number': clause_number,
                    'clause_text': clause_text,
                    'position': len(clauses)
                })
    
    else:
        # Fallback: paragraph-based segmentation
        logger.info("No numbered clauses detected, using paragraph fallback")
        
        paragraphs = text.split('\n\n')
        
        for i, para in enumerate(paragraphs):
            para = para.strip()
            
            # Filter out very short paragraphs
            if len(para) >= 20:
                clauses.append({
                    'clause_number': f'P{len(clauses) + 1}',
                    'clause_text': para,
                    'position': len(clauses)
                })
    
    logger.info(f"Clause segmentation complete: {len(clauses)} clauses extracted")
    return clauses
