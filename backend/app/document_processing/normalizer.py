"""
Text normalization and cleaning.
"""
import re
import logging

logger = logging.getLogger(__name__)


def clean_and_normalize(text: str) -> str:
    """
    Clean and normalize extracted text while preserving legal wording.
    
    This function:
    - Fixes hyphenation breaks (e.g., "prop-\\nerty" -> "property")
    - Collapses excessive whitespace while preserving structure
    - Removes common page numbers and headers/footers
    - Preserves legal wording, clause numbering, and special characters
    
    Args:
        text: Raw extracted text from document
        
    Returns:
        Cleaned and normalized text
    """
    logger.info(f"Starting text normalization: {len(text)} characters")
    
    # Fix hyphenation breaks: word-\n word -> wordword
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    
    # Remove common page number patterns
    text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'- \d+ -', '', text)
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)  # Standalone page numbers
    
    # Collapse multiple newlines (3+ -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Collapse multiple spaces/tabs into single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove leading/trailing whitespace from entire text
    text = text.strip()
    
    logger.info(f"Text normalization complete: {len(text)} characters")
    return text
