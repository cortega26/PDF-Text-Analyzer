# Refactor Plan: PDF-Text-Analyzer

**Date:** 2026-02-04
**Auditor:** Antigravity

---

## 1. Prioritized Action List (Top 15)

| Rank | Priority Score | Item | Category | Effort | Risk | Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **23** | **Fix Search Indexing** | Correctness | S | Low | High |
| **2** | **18** | **Fix Non-English Keywords** | Correctness | S | Low | High |
| **3** | **12** | **Singleton/Reuse ContentAnalyzer** | Performance | M | Med | High |
| **4** | **10** | **Remove Dead Code (Search Vectorizer)** | Maintainability | S | Low | Low |
| **5** | **9** | **Refactor `_process_pdf` Nesting** | Maintainability | M | Med | Med |
| **6** | **8** | **Extract Encryption Validation** | Robustness | S | Low | Med |
| **7** | **7** | **Implement Result Streaming** | Scalability | L | High | High |
| **8** | **7** | **Explicit NLTK Data Check** | Robustness | S | Low | Med |
| **9** | **6** | **Type Strictness for `PdfBatch`** | Maintainability | S | Low | Low |
| **10** | **5** | **Switch to `ProcessPoolExecutor`** | Performance | L | High | High |

*Priority = (Impact[1-5] × Confidence[1-5]) - (Risk[1-5] + Effort[1-5])*

---

## 2. Detailed Specs (Top 5)

### 1. Fix Search Indexing
*   **Description:** Change `PdfSearchEngine.add_document` to accept logic for full text indexing. Currently, it pulls `analysis_results['text_preview']`.
*   **Files:** `search.py`, `pdf_processor.py` (caller).
*   **Change:**
    *   Update `PdfSearchEngine.add_document` signature to accept `full_text` optional arg? No, better to fix the data passed.
    *   **Or better:** The caller `PdfProcessor.main` calls `search_engine.add_document(..., results['analysis'], ...)`. result['analysis'] typically doesn't contain full text (by design to save memory).
    *   **Recommendation:** `PdfSearchEngine` should probably accept the `full_text` explicitly at index time if available, or we need to rethink the "no full text in result" policy if search is required locally.
*   **Acceptance:** Searching for a unique word in the middle of a PDF (past 500 chars) returns the result.

### 2. Fix Non-English Keywords
*   **Description:** `ContentAnalyzer` hardcodes `stop_words='english'`.
*   **Files:** `text_analysis.py`.
*   **Change:**
    *   Update `__init__` to map `self.language` to sklearn compatible stop words list or pass `stop_words=self.language` if supported (sklearn supports 'english' but for others usually requires a list).
    *   Reuse the mapping logic from `pdf_processor` (or move it to a shared `utils/languages` module).
*   **Acceptance:** Processing a Spanish PDF filters out "de", "la", "que" from keywords.

### 3. Singleton/Reuse ContentAnalyzer
*   **Description:** `PdfProcessor` creates new `ContentAnalyzer` (and `TfidfVectorizer`) for every call.
*   **Files:** `pdf_processor.py`.
*   **Change:**
    *   Create a cache/registry of Analyzers by language key: `self.analyzers = {}`.
    *   `if language not in self.analyzers: self.analyzers[language] = ContentAnalyzer(language)`.
*   **Acceptance:** Batch processing time drops significantly.

### 4. Remove Dead Code (Search)
*   **Description:** Remove `self.vectorizer` from `PdfSearchEngine`.
*   **Files:** `search.py`.
*   **Change:** Delete lines 16-20 and import.
*   **Acceptance:** Code is cleaner, imports fewer libs.

### 5. Refactor `_process_pdf` Nesting
*   **Description:** Move valid pure functions out of the method scope.
*   **Files:** `pdf_processor.py`.
*   **Change:** Move `process_in_thread` inner logic to `_extract_pdf_data(content: bytes) -> tuple`.
*   **Acceptance:** `_process_pdf` is readable and calls a helper. Unit tests can test extraction without async loop.

---

## 3. "No-Regression" Notes
*   **API Contract:** Must keep `process_url` signature identical.
*   **Output Format:** JSON structure of `results` must remains stable for consumers.
*   **Dependencies:** Do not add new heavy libs (e.g., SpaCy) to replace NLTK unless approved.
