"""
Tests for document processing pipeline: extraction, normalization, segmentation.
"""
import os
import tempfile
from pathlib import Path

import pytest
import fitz  # PyMuPDF
from docx import Document

from app.document_processing.extractor import extract_text_from_pdf, extract_text_from_docx
from app.document_processing.normalizer import clean_and_normalize
from app.document_processing.segmenter import segment_clauses


# Test fixture creators

def create_test_pdf(text: str, output_path: str) -> None:
    """Create minimal PDF with PyMuPDF for testing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    doc.save(output_path)
    doc.close()


def create_test_docx(paragraphs: list[str], output_path: str) -> None:
    """Create minimal DOCX with python-docx for testing."""
    doc = Document()
    for para in paragraphs:
        doc.add_paragraph(para)
    doc.save(output_path)


# Extraction tests

def test_extract_pdf_text():
    """Test PDF text extraction returns correct text and page count."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp_path = tmp.name
    
    test_text = "This is a test PDF document for extraction testing."
    create_test_pdf(test_text, tmp_path)
    
    try:
        full_text, page_count = extract_text_from_pdf(tmp_path)
        
        # Verify page count
        assert page_count == 1
        
        # Verify text content (may have extra whitespace)
        assert test_text in full_text
        assert "PAGE 1" in full_text
        
    finally:
        os.unlink(tmp_path)


def test_extract_docx_text():
    """Test DOCX text extraction returns correct text and paragraph count."""
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        tmp_path = tmp.name
    
    test_paragraphs = [
        "This is the first paragraph.",
        "This is the second paragraph.",
        "This is the third paragraph."
    ]
    create_test_docx(test_paragraphs, tmp_path)
    
    try:
        full_text, para_count = extract_text_from_docx(tmp_path)
        
        # Verify paragraph count
        assert para_count == 3
        
        # Verify all paragraphs present
        for para in test_paragraphs:
            assert para in full_text
        
    finally:
        os.unlink(tmp_path)


def test_extract_pdf_file_not_found():
    """Test PDF extraction raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("/nonexistent/path/file.pdf")


def test_extract_docx_file_not_found():
    """Test DOCX extraction raises FileNotFoundError for missing file."""
    with pytest.raises(FileNotFoundError):
        extract_text_from_docx("/nonexistent/path/file.docx")


# Normalization tests

def test_normalize_hyphenation():
    """Test hyphenation break fixing: prop-\\nerty -> property."""
    input_text = "The prop-\nerty must be main-\ntained properly."
    expected = "The property must be maintained properly."
    
    result = clean_and_normalize(input_text)
    
    assert result == expected


def test_normalize_whitespace():
    """Test excessive whitespace collapse."""
    input_text = "Line 1\n\n\n\nLine 2\n\n\n\n\nLine 3"
    
    result = clean_and_normalize(input_text)
    
    # Should collapse 3+ newlines to 2
    assert "\n\n\n" not in result
    assert "Line 1" in result
    assert "Line 2" in result
    assert "Line 3" in result


def test_normalize_page_numbers():
    """Test page number removal."""
    input_text = "Some text here\nPage 1 of 10\nMore text\n- 5 -\nFinal text"
    
    result = clean_and_normalize(input_text)
    
    # Page numbers should be removed
    assert "Page 1 of 10" not in result
    assert "- 5 -" not in result
    # Content should remain
    assert "Some text here" in result
    assert "More text" in result
    assert "Final text" in result


def test_normalize_preserves_legal_text():
    """Test that legal wording is preserved exactly."""
    input_text = "The Party shall pay $1,000.00 per month (the \"Rent\")."
    
    result = clean_and_normalize(input_text)
    
    # All legal elements preserved
    assert "$1,000.00" in result
    assert "(the \"Rent\")" in result or '(the "Rent")' in result
    assert "shall" in result


# Segmentation tests

def test_segment_numbered_clauses():
    """Test detection of numbered clauses (1., 2., 3.)."""
    input_text = """1. The Tenant shall pay rent on the first day of each month.

2. The Landlord shall maintain the property in good condition.

3. Either party may terminate with 30 days notice."""
    
    clauses = segment_clauses(input_text)
    
    # Should detect 3 numbered clauses
    assert len(clauses) == 3
    
    # Verify clause numbers
    assert clauses[0]['clause_number'] == '1'
    assert clauses[1]['clause_number'] == '2'
    assert clauses[2]['clause_number'] == '3'
    
    # Verify positions
    assert clauses[0]['position'] == 0
    assert clauses[1]['position'] == 1
    assert clauses[2]['position'] == 2
    
    # Verify text content
    assert "Tenant shall pay rent" in clauses[0]['clause_text']
    assert "Landlord shall maintain" in clauses[1]['clause_text']


def test_segment_nested_numbering():
    """Test detection of nested clause numbering (1.1, 1.2)."""
    input_text = """1.1 First nested clause with some content here.

1.2 Second nested clause with more content here."""
    
    clauses = segment_clauses(input_text)
    
    # Should detect 2 nested clauses
    assert len(clauses) == 2
    assert clauses[0]['clause_number'] == '1.1'
    assert clauses[1]['clause_number'] == '1.2'


def test_segment_lettered_clauses():
    """Test detection of lettered clauses (a), (b)."""
    input_text = """(a) The first lettered clause with sufficient content.

(b) The second lettered clause with sufficient content.

(c) The third lettered clause with sufficient content."""
    
    clauses = segment_clauses(input_text)
    
    # Should detect 3 lettered clauses
    assert len(clauses) == 3
    assert clauses[0]['clause_number'] == '(a)'
    assert clauses[1]['clause_number'] == '(b)'
    assert clauses[2]['clause_number'] == '(c)'


def test_segment_paragraph_fallback():
    """Test paragraph fallback when no numbering detected."""
    input_text = """This is the first paragraph without any numbering.

This is the second paragraph also without numbering.

This is the third paragraph continuing the pattern."""
    
    clauses = segment_clauses(input_text)
    
    # Should use paragraph fallback with P1, P2, P3
    assert len(clauses) == 3
    assert clauses[0]['clause_number'] == 'P1'
    assert clauses[1]['clause_number'] == 'P2'
    assert clauses[2]['clause_number'] == 'P3'


def test_segment_filters_empty_clauses():
    """Test that very short clauses (< 20 chars) are filtered out."""
    input_text = """1. This is a proper clause with sufficient content to be included.

2. Short.

3. Another proper clause with enough content to pass the filter."""
    
    clauses = segment_clauses(input_text)
    
    # Should only get 2 clauses (clause 2 filtered out)
    assert len(clauses) == 2
    assert clauses[0]['clause_number'] == '1'
    assert clauses[1]['clause_number'] == '3'
    # Verify "Short." was filtered
    assert not any('Short' in c['clause_text'] for c in clauses)


def test_segment_mixed_content():
    """Test segmentation with mixed content (numbers, letters, text)."""
    input_text = """1. Main clause with content.

(a) Sub-clause under main clause with sufficient length.

2. Second main clause with more content here."""
    
    clauses = segment_clauses(input_text)
    
    # Should detect all patterns
    assert len(clauses) == 3
    assert clauses[0]['clause_number'] == '1'
    assert clauses[1]['clause_number'] == '(a)'
    assert clauses[2]['clause_number'] == '2'


@pytest.mark.parametrize("heading,expected_number", [
    ("1.", "1"),
    ("2.", "2"),
    ("1.1.", "1.1"),
])
def test_clause_number_strips_trailing_dot(heading, expected_number):
    """Regression: clause numbers should never end with '.'. 
    
    Bug fix in commit 5f64f92 added .rstrip('.') to remove trailing dots from parsed numbers.
    This test pins that behavior: inputs '1.', '2.', '1.1.' should return '1', '2', '1.1'.
    """
    input_text = f"{heading} This is a clause with sufficient content for the segmenter to accept it."
    
    clauses = segment_clauses(input_text)
    
    assert len(clauses) == 1
    assert clauses[0]['clause_number'] == expected_number
    assert not clauses[0]['clause_number'].endswith('.')
