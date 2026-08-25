"""
Utility functions for document processing.
"""
import logging

logger = logging.getLogger(__name__)


def validate_file_type(filename: str) -> bool:
    """
    Validate if the file type is supported for processing.
    
    Args:
        filename: Name of the file to validate
        
    Returns:
        True if file type is supported (.pdf or .docx), False otherwise
    """
    return filename.lower().endswith(('.pdf', '.docx'))


def get_file_extension(filename: str) -> str:
    """
    Extract file extension from filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension in lowercase (e.g., ".pdf", ".docx")
    """
    return filename.lower().split('.')[-1] if '.' in filename else ''
