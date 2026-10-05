<div align="center">

# PDF Text Analyzer

<p><strong>Turn PDFs into searchable, analyzable text without pretending every PDF is clean.</strong></p>
<p>Validation, extraction, language detection, batch processing and TF-IDF search in one modular Python pipeline.</p>

[![GitHub stars](https://img.shields.io/github/stars/cortega26/PDF-Text-Analyzer?style=flat&logo=github)](https://github.com/cortega26/PDF-Text-Analyzer/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Part of Tooltician](https://img.shields.io/badge/Part_of-Tooltician.com-6C47FF?v=2)](https://tooltician.com)

</div>

```python
import asyncio
from pdf_processor import PdfProcessor

async def main():
    result = await PdfProcessor().process_url(
        "https://example.com/document.pdf",
        "search phrase",
    )
    print(result["analysis"]["language"])
    print(result["analysis"]["search_term_count"])

asyncio.run(main())
```

## PDFs fail in more ways than “text found / text not found”

A production PDF pipeline needs to distinguish invalid files, encrypted documents, scanned PDFs that require OCR, oversized inputs, network failures and normal extraction — **before** downstream analysis quietly produces garbage.

PDF Text Analyzer is built around that reality:

| Problem | Built-in answer |
|:---|:---|
| Fake or malformed PDFs | Signature and file validation |
| Encrypted documents | Explicit `EncryptedPdfError` |
| Scanned / empty PDFs | `SCANNED_OCR_REQUIRED` status |
| Large batches | Async downloads + multiprocessing extraction |
| Repeated analysis | Cache layer |
| Finding concepts across documents | TF-IDF indexing and search |
| Mixed-language corpora | Language detection + text analysis |

> **Good fit:** ingestion pipelines, document research, compliance workflows, batch analysis, search prototypes and backend services where failure modes must stay visible.

## Key Features

*   **Robust Ingestion**: Strict validation of PDF signatures, size limits, and encryption detection.
*   **Modular Architecture**: Clean separation of concerns (Processing, Analysis, Models, Caching, Search).
*   **Advanced Analysis**:
    *   Language detection (`langdetect`).
    *   Keyword extraction and readability scoring (`textstat` equivalent logic).
    *   Stopword removal using NLTK.
*   **Performance**:
    *   Asynchronous I/O (`aiohttp`) for downloads.
    *   Multiprocessing for text extraction (`fitz` / PyMuPDF).
    *   In-memory caching for repeated requests.
*   **Scalability**:
    *   **Batch Processing**: Concurrent processing of multiple PDFs.
    *   **Search Engine**: TF-IDF based indexing and searching of processed documents.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/cortega26/PDF-Text-Analyzer.git
    cd PDF-Text-Analyzer
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

    For development and testing:
    ```bash
    pip install -r requirements-dev.txt
    ```

## Usage

### Basic Usage

```python
import asyncio
from pdf_processor import PdfProcessor

async def main():
    processor = PdfProcessor()
    url = "https://example.com/document.pdf"
    
    # Process a single PDF
    results = await processor.process_url(url, "search phrase")
    
    print(f"Status: {results['metadata']['extraction_status']}")
    print(f"Language: {results['analysis']['language']}")
    print(f"Word Count: {results['analysis']['word_count']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Batch Processing

```python
from batch import PdfBatch
from pdf_processor import PdfProcessor

async def process_batch():
    processor = PdfProcessor()
    batch_processor = PdfBatch(processor)
    
    urls = [
        "https://example.com/doc1.pdf",
        "https://example.com/doc2.pdf"
    ]
    
    results = await batch_processor.process_urls(urls, "keyword")
    print(f"Processed {results['summary']['total_processed']} files.")
```

### Batch Processing (Streaming)
For memory-efficient processing of huge batches, use the new `process_stream` API:

```python
from batch import PdfBatch

async def process_many(processor, urls):
    batch = PdfBatch(processor)
    async for url, result, error in batch.process_stream(urls, "search term"):
        if error:
            print(f"Failed {url}: {error}")
        else:
            print(f"Success {url}: Found {result['analysis']['search_term_count']} matches")
            # Save result to DB immediately...
```

### Search Engine

```python
from search import PdfSearchEngine

# Add processed results to the index
engine = PdfSearchEngine()
engine.add_document(url="...", analysis_result=..., metadata=...)

# Search
matches = engine.search("important concept")
for match in matches:
    print(f"Found in {match['url']} (Score: {match['relevance_score']})")
```

## Architecture

The project has been refactored into single-responsibility modules:

*   `pdf_processor.py`: Main facade/coordinator.
*   `models.py`: Data classes (`PdfMetadata`, `ProcessingStatistics`, `ExtractionStatus`).
*   `validators.py`: Security and file validation logic.
*   `text_analysis.py`: NLP and content analysis logic.
*   `cache.py`: Caching protocols and implementations.
*   `search.py`: Vector-based search engine functionality.
*   `batch.py`: Orchestration for multiple files.
*   `config.py`: Centralized configuration.
*   `exceptions.py`: Custom error hierarchy.

## Robustness & Error Handling

The system now distinguishes between different failure modes:
*   **Encrypted PDFs**: Raises `EncryptedPdfError` immediately.
*   **Invalid Files**: Rejects non-PDFs (even with `.pdf` extension) via `InvalidFileError`.
*   **Scanned/Empty**: Returns `ExtractionStatus.SCANNED_OCR_REQUIRED` rather than failing silenty.
*   **Size Limits**: Enforced via `MAX_PDF_SIZE` in `config.py`.

## Testing

A full regression suite is available using `pytest`.

```bash
# Run all tests
python -m pytest

# Run with coverage report
python -m pytest --cov=.
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

*Part of the [Tooltician](https://tooltician.com) ecosystem — robust PDF text extraction, analysis and search.*
