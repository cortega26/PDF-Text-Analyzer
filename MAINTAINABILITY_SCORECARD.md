# Maintainability Scorecard: PDF-Text-Analyzer

**Date:** 2026-02-04
**Auditor:** Antigravity

---

## 1. Scorecard (1-5 Scale)
*1 = Poor, 5 = Excellent*

| Category | Score | Notes |
| :--- | :--- | :--- |
| **Code Style & Formatting** | 4 | PEP-8 compliance is good. Type hinting is present. |
| **Naming Conventions** | 4 | Generally clear (`pdf_url`, `content`, `metadata`). `word_or_phrase` is a bit verbose. |
| **Modularity** | 2 | `PdfProcessor` knows too much. Functions are deeply nested inside methods. |
| **Error Handling** | 3 | Uses custom exceptions, but sometimes swallows context in generic `ProcessingError`. |
| **Testing Readiness** | 2 | Hard to unit test core logic because it's wrapped in `PdfProcessor` instance methods with side effects (download). |
| **Documentation** | 3 | Docstrings are present but could be more detailed about edge cases and return shapes. |

---

## 2. Code Smells Checklist

### High Leverage Improvements
1.  **Remove Nested Functions:**
    *   **Files:** `pdf_processor.py` (`process_in_thread`, `analyze_in_thread`)
    *   **Why:** Impossible to unit test in isolation. Hides complexity.
    *   **Fix:** promote to `_static_process_pdf` and `ContentAnalyzer.analyze(text)`.
2.  **Explicit Config:**
    *   **Files:** `config.py`, `pdf_processor.py`
    *   **Why:** `MAX_PDF_SIZE` and `DOWNLOAD_TIMEOUT` are global constants but also copied as class attributes.
    *   **Fix:** Use a settings object or dict passed into `__init__`.
3.  **Hardcoded Data:**
    *   **Files:** `pdf_processor.py` (`_get_nltk_stopwords` mapping)
    *   **Why:** Maintenance headache if adding languages.
    *   **Fix:** Use a config file or proper `languages.py` constants.
4.  **Magic Numbers:**
    *   `10000` (char limit for language detection)
    *   `500` (preview length)
    *   `100` (MB limit)
    *   **Fix:** Move all to `config.py`.

### Duplication
*   **Stopwords:** Logic for fetching stopwords exists in `pdf_processor` but `ContentAnalyzer` (wraps `TfidfVectorizer`) uses its own default `stop_words='english'`.
    *   **Result:** `ContentAnalyzer` ignores the detected language for TF-IDF! It always uses English unless manually overridden (which it isn't). This is a **Correctness Bug**.

---

## 3. Top Recommendations
1.  **Decouple NLP:** Move all NLP logic (including stopwords fetching) into `ContentAnalyzer`.
2.  **Fix TF-IDF Language:** Pass the detected language to `ContentAnalyzer` so it uses correct stopwords for keywords.
3.  **Flatten Functions:** Extract nested functions to module-level private functions or static methods.
