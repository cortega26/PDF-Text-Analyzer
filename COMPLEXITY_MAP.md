# Complexity Map: PDF-Text-Analyzer

**Date:** 2026-02-04
**Auditor:** Antigravity

---

## 1. Macro Complexity (Architecture)

### Boundary Violations
| Violation | Why it's bad | Simplest Fix |
| :--- | :--- | :--- |
| **`PdfProcessor` mixes Network, Parsing, and NLP** | Violates Single Responsibility Principle. Makes testing network failures independent of parsing impossible. | Extract `Downloader` strategy and `Analyzer` strategy. |
| **`ContentAnalyzer` Lifecycle** | Instantiated *inside* `_analyze_content` method. Forces re-initialization of heavy `TfidfVectorizer` per PDF. | Inject an instance of `ContentAnalyzer` into `PdfProcessor` or use a factory/singleton for the vectorizer. |
| **`PdfSearchEngine` coupled to Preview** | Indexes `analysis_results['text_preview']` instead of raw text. Search results are fundamentally incorrect/limited. | Accept full text or a dedicated searchable field in `add_document`. |
| **Thread/Async Mixing** | `_process_pdf` defines a nested function `process_in_thread` to run in executor. Hard to debug/profile. | Move `process_in_thread` to a top-level function or static method to isolate pure logic. |

---

## 2. Cyclomatic Complexity (Micro)

### Top Complex Functions
*Estimated Cyclomatic Complexity (CC)*

| Function | File | CC | Risk | Smells | Suggestion |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_process_pdf` | `pdf_processor.py` | 18 | High | Deep nesting, nested function definition, multiple try/except/finally blocks implicit in context managers. | Extract encryption check, metadata extraction, and text extraction into small pure functions. |
| `_analyze_content` | `pdf_processor.py` | 14 | Med | Nested function definition, mixed IO/CPU logic. | Move `analyze_in_thread` logic to `ContentAnalyzer` class entirely. |
| `_download_pdf` | `pdf_processor.py` | 12 | Med | Retry loop + Size check + Content-Type check + Signature check. | Extract validation logic into `validators.py` fully. |
| `calculate_readability_score` | `text_analysis.py` | 8 | Low | Syllable counting loop logic mixed with score calc. | Extract `_count_syllables` (already done) but simplify the main scoring logic. |
| `_get_nltk_stopwords` | `pdf_processor.py` | 4 | Low | Hardcoded mapping dictionary inside method. | Move constant mapping to `languages.py` or module level. |

### Refactor Priority
1.  **Extract Analyzers:** Move the logic inside `analyze_in_thread` (lines 317-360) directly into `ContentAnalyzer`. This removes the weird dependency and complexity from `PdfProcessor`.
2.  **Flatten `_process_pdf`:** The nested `process_in_thread` function is unnecessary closure. Make it a static method or standalone function that takes bytes and returns (text, metadata).
3.  **Unified Validation:** `_download_pdf` has inline validation logic that duplicates `validators.py` intent.

---

## 3. Complexity Conclusions

The codebase suffers from "Russian Doll" function design—functions defined inside functions to capture scope or run in executors. This increases cognitive load and makes unit testing specific logical blocks (like "extract metadata from fitz doc") impossible without mocking the entire `PdfProcessor` flow.
