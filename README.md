# PDF Text Analyzer

A robust, modular, and high-performance Python system for downloading, extracting, analyzing, and searching text from PDF documents.

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
    git clone https://github.com/cortega26/PDF-Text-Analizer.git
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

async def process_batch():
    processor = PdfProcessor()
    batch_processor = PdfBatch(processor)
    
    urls = [
        "https://example.com/doc1.pdf",
        "https://example.com/doc2.pdf"
    ]
    
    results = await batch_processor.process_urls(urls, "keyword")
    print(f"Processed {results['summary']['total_processed']} files.")

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
