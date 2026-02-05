from config import MAX_PDF_SIZE

def validate_pdf_signature(content: bytes) -> bool:
    """
    Validate that the file starts with the PDF magic bytes (%PDF-).
    """
    # Check for %PDF- in the first 1024 bytes (standard allows some preamble)
    header_check = content[:1024]
    return b'%PDF-' in header_check

def validate_file_size(content: bytes) -> bool:
    """
    Validate that the file size is within limits.
    """
    return len(content) <= MAX_PDF_SIZE
