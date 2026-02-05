import pytest
import json
import os
from pathlib import Path
from pdf_processor import PdfProcessor

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_DIR.mkdir(exist_ok=True)
GOLDEN_FILE = GOLDEN_DIR / "complex_pdf_v1.json"

@pytest.mark.asyncio
async def test_golden_contract(mock_aioresponse, pdf_factory):
    """
    Golden test ensuring the public API contract remains identical.
    Uses a fixed PDF structure and asserts JSON output matches exactly.
    """
    url = "http://example.com/golden.pdf"
    
    # Create deterministic content
    text_content = (
        "Golden test content. "
        "Search term: consistency. "
        "Repeat consistency consistency. "
        "End of page 1."
    )
    pdf_bytes = pdf_factory(text=text_content, pages=2)
    
    mock_aioresponse.get(url, body=pdf_bytes, headers={"Content-Type": "application/pdf"})
    
    processor = PdfProcessor()
    # Mock time/stats for deterministic output in golden file?
    # We can override stats or just exclude them from comparison.
    # But usually we want to snapshot everything except timestamps.
    
    result = await processor.process_url(url, "consistency")
    
    # Normalize result for snapshot (remove varying timestamps/paths)
    snapshot = _normalize_result(result)
    
    # Round-trip through JSON to ensure deterministic types (e.g. tuples -> lists)
    snapshot = json.loads(json.dumps(snapshot))
    
    # If golden file doesn't exist, fail with instruction or create it (if in update mode)
    if not GOLDEN_FILE.exists():
        with open(GOLDEN_FILE, "w") as f:
            json.dump(snapshot, f, indent=2, sort_keys=True)
        print(f"Created new golden file at {GOLDEN_FILE}")
    
    with open(GOLDEN_FILE, "r") as f:
        expected = json.load(f)
    
    # Assert
    assert snapshot == expected

def _normalize_result(result):
    """Remove non-deterministic fields."""
    res = result.copy()
    
    # Statistics: timestamps vary
    if 'statistics' in res:
        res['statistics'] = {k: v for k, v in res['statistics'].items() 
                           if k not in ['start_time', 'end_time', 'processing_time']}
        # memory_used might vary slightly? Set to 0 or check range?
        res['statistics']['memory_used'] = 0.0
    
    # Analysis: usually deterministic given fixed nltk.
    # Metadata: creation_date might come from fitz generation time?
    if 'metadata' in res:
        if 'creation_date' in res['metadata']:
            res['metadata']['creation_date'] = "MOCKED_DATE"
        if 'modification_date' in res['metadata']:
            res['metadata']['modification_date'] = "MOCKED_DATE"
            
    return res
