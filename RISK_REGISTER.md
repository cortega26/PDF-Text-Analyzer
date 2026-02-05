# Risk Register: PDF-Text-Analyzer

**Date:** 2026-02-04
**Auditor:** Antigravity

---

## 1. Critical Risks (Must Fix Immediately)

| Risk ID | Description | Likelihood | Impact | Severity | Mitigation Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-01** | **Search Indexing Defect:** `PdfSearchEngine` indexes only the *text preview* (first ~500 chars), ignoring 99% of document content. Search results are fundamentally incorrect. | Definite | High | **Critical** | `PdfSearchEngine.add_document` |
| **R-02** | **NLP Language Mismatch:** `ContentAnalyzer` hardcodes `stop_words='english'` for `TfidfVectorizer`, ignoring the detected document language. Keyword extraction is invalid for non-English docs. | Definite | Med | **High** | `ContentAnalyzer.__init__` |
| **R-03** | **Memory Unbounded Growth:** `PdfBatch` accumulates all results in memory. Processing large batches leads to `MemoryError` crash. | High | High | **High** | `PdfBatch.process_urls` |

---

## 2. Moderate Risks (Address in Next Cycle)

| Risk ID | Description | Likelihood | Impact | Severity | Mitigation Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-04** | **NLTK Runtime Dependency:** `_ensure_nltk_data` downloads data at runtime. Fails if offline/firewalled. Slow startup. | Med | Med | **Medium** | Deployment Script / Dockerfile |
| **R-05** | **GIL Bottleneck:** CPU-bound tasks run in `ThreadPoolExecutor` due to default `run_in_executor`. Limits effective throughput to 1 core. | Definite | Low | **Medium** | Architecture (Move to `multiprocessing`) |
| **R-06** | **Search Performance:** `PdfSearchEngine` uses Python-based inverted index building. Slow for large document counts (>10k). | Low | Low | **Low** | `PdfSearchEngine` |

---

## 3. Low Risks (Tech Debt)

| Risk ID | Description | Likelihood | Impact | Severity | Mitigation Owner |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-07** | **Dead Code:** `TfidfVectorizer` imported/initialized in `search.py` but never used. Wastes resources. | Definite | Low | **Low** | Cleanup |
| **R-08** | **Implicit Encryption Check:** `_process_pdf` assumes empty password failure = encrypted. | Low | Low | **Low** | `PdfProcessor._process_pdf` |
