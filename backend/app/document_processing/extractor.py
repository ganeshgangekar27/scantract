"""
Text extraction from PDF and DOCX files.
"""
import logging
from pathlib import Path

# Note: 'import fitz' is deprecated, but using it for compatibility with PyMuPDF 1.28.2
# Future versions should use 'import pymupdf as fitz'
import fitz  # PyMuPDF
from docx import Document

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> tuple[str, int]:
    """
    Extract text from a PDF file using PyMuPDF.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple of (extracted_text, page_count)
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: If the PDF is corrupted or cannot be read
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    logger.info(f"Starting PDF extraction: {file_path}")
    
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        pages_text = []
        
        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text()
            pages_text.append(f"\n\n--- PAGE {page_num + 1} ---\n\n{text}")
        
        doc.close()
        full_text = "".join(pages_text)
        
        logger.info(f"PDF extraction complete: {page_count} pages, {len(full_text)} characters")
        return full_text, page_count
        
    except Exception as e:
        logger.error(f"Error extracting PDF {file_path}: {str(e)}")
        raise Exception(f"Failed to extract PDF: {str(e)}")


def extract_text_from_docx(file_path: str) -> tuple[str, int]:
    """
    Extract text from a DOCX file using python-docx.
    
    Args:
        file_path: Path to the DOCX file
        
    Returns:
        Tuple of (extracted_text, paragraph_count)
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: If the DOCX is corrupted or cannot be read
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {file_path}")
    
    logger.info(f"Starting DOCX extraction: {file_path}")
    
    try:
        doc = Document(file_path)
        paragraphs = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:  # Only include non-empty paragraphs
                paragraphs.append(text)
        
        paragraph_count = len(paragraphs)
        full_text = "\n\n".join(paragraphs)
        
        logger.info(f"DOCX extraction complete: {paragraph_count} paragraphs, {len(full_text)} characters")
        return full_text, paragraph_count
        
    except Exception as e:
        logger.error(f"Error extracting DOCX {file_path}: {str(e)}")
        raise Exception(f"Failed to extract DOCX: {str(e)}")
