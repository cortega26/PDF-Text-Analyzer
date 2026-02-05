from models import PdfMetadata, ExtractionStatus

def test_metadata_defaults():
    """Verify default values for metadata."""
    meta = PdfMetadata()
    assert meta.extraction_status == ExtractionStatus.SUCCESS
    assert meta.file_size == 0
    assert meta.encrypted is False

def test_metadata_serialization():
    """Verify to_dict converts ENUM to value."""
    meta = PdfMetadata(extraction_status=ExtractionStatus.SCANNED)
    data = meta.to_dict()
    assert data['extraction_status'] == 'scanned_ocr_required'
    assert data['encrypted'] is False
