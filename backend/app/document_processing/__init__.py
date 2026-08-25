"""
Document processing pipeline for contract extraction and segmentation.
"""
from .extractor import extract_text_from_pdf, extract_text_from_docx
from .normalizer import clean_and_normalize
from .segmenter import segment_clauses

__all__ = [
    'extract_text_from_pdf',
    'extract_text_from_docx',
    'clean_and_normalize',
    'segment_clauses',
]
