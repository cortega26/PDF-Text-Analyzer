import pytest
from pdf_processor import PdfProcessor
from models import ExtractionStatus
from exceptions import InvalidFileError, EncryptedPdfError, FileTooLargeError, ProcessingError
import fitz

@pytest.mark.asyncio
async def test_pipeline_valid_pdf(mock_aioresponse, pdf_factory):
    """Test full processing of a valid generated PDF."""
    url = "http://example.com/test.pdf"
    content = pdf_factory(text="This is a test PDF with content.", pages=1)
    
    # Mock download
    mock_aioresponse.get(url, body=content, headers={"Content-Type": "application/pdf"})
    
    processor = PdfProcessor()
    result = await processor.process_url(url, "test")
    
    assert result['metadata']['extraction_status'] == ExtractionStatus.SUCCESS.value
    assert result['analysis']['language'] != 'unknown'
    assert 'test' in result['analysis']['text_preview'].lower()

@pytest.mark.asyncio
async def test_pipeline_invalid_file(mock_aioresponse):
    """Test detection of invalid file via signature."""
    url = "http://example.com/bad.pdf"
    content = b"<html>Not a PDF</html>"
    
    mock_aioresponse.get(url, body=content, headers={"Content-Type": "application/pdf"})
    
    processor = PdfProcessor()
    with pytest.raises(InvalidFileError):
        await processor.process_url(url, "test")

@pytest.mark.asyncio
async def test_pipeline_failed_download_retry(mock_aioresponse):
    """Test retry logic on network failure."""
    url = "http://example.com/retry.pdf"
    
    # Fail 3 times
    mock_aioresponse.get(url, exception=Exception("Network fail"))
    mock_aioresponse.get(url, exception=Exception("Network fail"))
    mock_aioresponse.get(url, exception=Exception("Network fail"))
    
    processor = PdfProcessor()
    # Speed up retries
    processor.BACKOFF_FACTOR = 0 
    
    with pytest.raises(ProcessingError) as exc:
        await processor.process_url(url, "test")
    
    assert "Failed to download PDF" in str(exc.value)

@pytest.mark.asyncio
async def test_pipeline_empty_scanned_pdf(mock_aioresponse, pdf_factory):
    """Test handling of PDF with no extractable text (image-only/scanned)."""
    url = "http://example.com/scanned.pdf"
    # Create empty page (no text inserted)
    content = pdf_factory(text="", pages=1)
    
    mock_aioresponse.get(url, body=content, headers={"Content-Type": "application/pdf"})
    
    processor = PdfProcessor()
    result = await processor.process_url(url, "test")
    
    assert result['metadata']['extraction_status'] == ExtractionStatus.SCANNED.value
    assert result['analysis']['word_count'] == 0
    assert "Analysis skipped" in result['analysis']['text_preview']
