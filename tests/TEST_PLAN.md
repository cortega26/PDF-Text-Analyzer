# Test Plan for PDF-Text-Analyzer

## 1. Public API Surface
The primary entry point is the `PdfProcessor` class in `pdf_processor.py`.

*   **Initialization**: `PdfProcessor(pdf_url=None, cache=None, max_workers=None, storage_path=None)`
*   **Method**: `async def process_url(url: str, word_or_phrase: str) -> Dict[str, Any]`
*   **Method**: `def main(word_or_phrase: str) -> Dict[str, Any]` (Synchronous wrapper)

**I/O Contract:**
*   **Input**: URL (string), Search Term (string).
*   **Output**: Dictionary with keys:
    *   `metadata`: Dict (title, author, ..., extraction_status)
    *   `analysis`: Dict (word_count, language, keywords, text_preview, etc.)
    *   `statistics`: Dict (timings, page counts)

**Dependencies/Side-Effects:**
*   **Network**: `aiohttp` for downloading PDFs.
*   **Filesystem**: NLTK data (should be pre-downloaded or mocked).
*   **CPU**: `fitz` (PyMuPDF) for parsing, `nltk`/`scikit-learn` for analysis.

## 2. Test Strategy

### Layer 1: Unit Tests
Focus on pure logic in helper modules.
*   `tests/test_unit_validators.py`: Verify `validate_pdf_signature`, `validate_file_size`.
*   `tests/test_unit_models.py`: Verify `PdfMetadata` serialization, `ExtractionStatus` enum.
*   `tests/test_unit_text_analysis.py`: Verify `ContentAnalyzer` (readability, keywords) with fixed text.

### Layer 2: Integration Tests (Hermetic)
Test the `PdfProcessor` pipeline with mocked dependencies.
*   `tests/test_integration_pipeline.py`:
    *   **Mock `aiohttp`**: Intercept calls to returning bytes.
    *   **Mock NLTK**: Verify it doesn't try to download if data exists (or mock the downloader).
    *   **Fixtures**: Generate real valid/invalid PDF bytes using `fitz` in memory.
    *   **Scenarios**:
        *   Valid PDF: Check metadata and text extraction.
        *   Invalid PDF: `InvalidFileError`.
        *   Encrypted PDF: `EncryptedPdfError`.
        *   Empty PDF: `ExtractionStatus.SCANNED`.

### Layer 3: Golden Tests
Snapshot testing for stability.
*   `tests/test_golden_contract.py`:
    *   Run processor against a synthesized "complex" PDF (generated in fixture).
    *   Compare `result['analysis']` and `result['metadata']` against a stored JSON file.
    *   Ensure sorted keys/lists for deterministic comparison.

## 3. Fixtures & Mocking
*   `conftest.py`:
    *   `pdf_bytes_factory(text, encrypted=False)`: Returns bytes of a PDF created with `fitz`.
    *   `mock_aioresponse`: Auto-use fixture to block all real network calls.

## 4. Dependencies
*   `pytest`
*   `pytest-asyncio`
*   `pytest-cov`
*   `aioresponses`
