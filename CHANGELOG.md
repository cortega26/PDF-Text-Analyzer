# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2026-02-04

### Added
- **Validation**: Strict file signature (`%PDF-`) and size validation (`validators.py`).
- **Models**: `ExtractionStatus` enum (SUCCESS, FAILED, SCANNED_OCR_REQUIRED, ENCRYPTED).
- **Exceptions**: Specific errors `EncryptedPdfError`, `InvalidFileError`, `EmptyContentError`.
- **Search Engine**: Simple TF-IDF search implementation in `search.py`.
- **Batch Processing**: `PdfBatch` class for concurrent processing of URLs.
- **Testing**: Comprehensive regression test suite (`tests/`) covering unit, integration, and contract tests.
- **Dev Dependencies**: `requirements-dev.txt` for development tools.

### Changed
- **Architecture**: Decomposed `pdf_processor.py` into modular components (`config`, `models`, `utils`, `cache`, `text_analysis`).
- **Robustness**: Improved handling of encrypted PDFs (fail-fast) and empty content (status reporting).
- **Performance**: Optimized text analysis with cached stopwords and language detection.
- **Configuration**: Moved hardcoded constants to `config.py`.

### Fixed
- NLTK Data initialization issue (`punkt_tab` missing).
- Silent failures on non-PDF files (now raises `InvalidFileError`).

## [2.1.0] - 2026-02-04 (Initial Refactor)

### Added
- **Caching**: `SimpleMemoryCache` implementation.
- **Async**: Fully asynchronous download pipeline using `aiohttp`.
- **Logging**: Structured logging via `utils.setup_logging`.

### Changed
- Refactored synchronous `requests` calls to `aiohttp`.
- Updated `pdf_processor.py` to use new modular imports.

## [1.0.0] - Initial Release

### Added
- Basic PDF download and text extraction using `requests` and `PyMuPDF`.
- Language detection and keyword extraction.
