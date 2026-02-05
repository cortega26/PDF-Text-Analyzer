# Architecture Notes & Refactor Plan

## Responsibility Map
| File | Actual Responsibility | Issues |
|------|----------------------|--------|
| `pdf_processor.py` | Defines data models (`PdfMetadata`, `ProcessingStatistics`), exceptions (`ProcessingError`), caching (`Cache`, `SimpleMemoryCache`), text analysis (`ContentAnalyzer`), PDF processing (`PdfProcessor`), batch processing (`PdfBatch`), search (`PdfSearchEngine`), logging setup, and script entry point. | **Critical Violation**: God Object. Multiple responsibilities tied together. High cognitive load. |
| `languages.py` | Maps language codes to names. | Clean. Single responsibility. |
| `example.py` | Example usage script. | Clean. |
| `requirements.txt` | Dependency listing. | Clean. |

## Structural Smells
1.  **God File / God Class**: `pdf_processor.py` contains 7+ distinct classes and logic for HTTP, PDF parsing, NLP, Caching, and Search.
2.  **Hidden Global State**: `logging.basicConfig` is called at the module level in `pdf_processor.py`, which side-effects the global logging configuration upon import.
3.  **Mixed Abstractions**: `PdfProcessor` handles downloading (HTTP), PDF parsing (fitz), and analysis logic (calling `ContentAnalyzer`).
4.  **Hardcoded Configuration**: Constants like `MAX_PDF_SIZE`, `DOWNLOAD_TIMEOUT` are hardcoded in `PdfProcessor`.
5.  **Implicit Dependencies**: NLTK data downloading happens implicitly inside `PdfProcessor` initialization (`_ensure_nltk_data`).

## Refactor Plan
**Goal**: Decompose `pdf_processor.py` into focused modules adhering to Single Responsibility Principle.

1.  **Extract Models**: Move `PdfMetadata`, `ProcessingStatistics` to `models.py`. Move `ProcessingError` to `exceptions.py` (or keep in models if small).
2.  **Extract Utilities**: Move `CorrelationFilter` and logging setup to `utils.py`.
3.  **Extract Cache**: Move `Cache` and `SimpleMemoryCache` to `cache.py`.
4.  **Extract Analysis**: Move `ContentAnalyzer` to `text_analysis.py`.
5.  **Extract Search**: Move `PdfSearchEngine` to `search.py`.
6.  **Extract Batch**: Move `PdfBatch` to `batch.py`.
7.  **Refine Processor**: Keep `PdfProcessor` in `pdf_processor.py` but delegate logic.
    *   `pdf_processor.py` will serve as the facade and entry point to preserve backward compatibility (`from pdf_processor import PdfProcessor`).
    *   It will import exceptions and models from the new modules.
8.  **Explicit Configuration**: Move constants to `config.py`.

**What will NOT be changed**:
*   The public API of `PdfProcessor` (methods `process_url`, `main`, etc. will have same signatures).
*   The logic of `ContentAnalyzer` (text statistics, keyword extraction).
*   The logic of `PdfSearchEngine`.
*   The logic involving `multiprocessing` and `asyncio` (unless needed to decouple).

## Proposed Module Layout
*   `models.py`: Data classes (`PdfMetadata`, `ProcessingStatistics`).
*   `exceptions.py`: `ProcessingError`.
*   `config.py`: Configuration constants.
*   `utils.py`: Logging and helper functions.
*   `cache.py`: Caching protocol and implementation.
*   `text_analysis.py`: `ContentAnalyzer` class.
*   `search.py`: `PdfSearchEngine`.
*   `batch.py`: `PdfBatch`.
*   `pdf_processor.py`: Main `PdfProcessor` class.
