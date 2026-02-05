from validators import validate_pdf_signature, validate_file_size
from config import MAX_PDF_SIZE

def test_validate_pdf_signature_valid():
    """Test that a valid PDF signature is detected."""
    content = b'%PDF-1.4\n...'
    assert validate_pdf_signature(content) is True

def test_validate_pdf_signature_invalid():
    """Test that missing signature fails."""
    content = b'<html>...</html>'
    assert validate_pdf_signature(content) is False

def test_validate_pdf_signature_offset():
    """Test signature slightly offset (allowed within first 1024 bytes)."""
    content = b'junk\n%PDF-1.4'
    assert validate_pdf_signature(content) is True

def test_validate_file_size_ok():
    """Test file size within limit."""
    content = b'0' * (MAX_PDF_SIZE - 1)
    assert validate_file_size(content) is True

def test_validate_file_size_too_large():
    """Test file size exceeding limit."""
    content = b'0' * (MAX_PDF_SIZE + 1)
    assert validate_file_size(content) is False
