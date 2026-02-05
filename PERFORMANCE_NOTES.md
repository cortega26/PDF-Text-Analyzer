# Performance Notes: PDF-Text-Analyzer

**Date:** 2026-02-04
**Auditor:** Antigravity

---

## 1. Hot Paths & Bottlenecks

### A. Repeated Vectorizer Initialization (High Impact)
*   **Issue:** `ContentAnalyzer` is instantiated inside `PdfProcessor._analyze_content`.
*   **Cost:** Scikit-learn's `TfidfVectorizer` is heavyweight. Creating it for every single PDF processed adds 100ms+ overhead per file.
*   **Fix:** Instantiate `ContentAnalyzer` once (singleton or injected dependency) and reuse it. **Note:** `TfidfVectorizer.fit_transform` is for *training* a model. Here we are using it for *extraction*? Code checks: `vectorizer.fit_transform([text])`. This fits a new vocabulary for *every single document*. It's functionally correct for extracting keywords *per document* but extremely inefficient vs using a global model or simpler counter.

### B. Unused Heavy Dependency (Dead Code)
*   **Issue:** `PdfSearchEngine` imports and initializes `TfidfVectorizer` but **never uses it** in `add_document` or `search`.
*   **Cost:** Unnecessary memory usage and import time.
*   **Fix:** Remove `TfidfVectorizer` from `search.py`.

### C. GIL Contention (Throughput Limiter)
*   **Issue:** `PdfProcessor` uses `loop.run_in_executor(None, ...)` which defaults to `ThreadPoolExecutor`.
*   **Impact:** PDF parsing (`fitz`) and NLP (`nltk`) are CPU-bound. The Global Interpreter Lock (GIL) prevents true parallelism. threads fight for the GIL.
*   **Observation:** The "Async" architecture only helps with downloading. Processing 10 PDFs will take `10 * T` time, not `T` time.
*   **Fix:** Use `ProcessPoolExecutor` for CPU-bound tasks (requires picklability, harder to implement but necessary for scale).

---

## 2. Memory Profile

### Estimated Footprint
*   **Input:** 100MB PDF.
*   **Internal Representation:** `fitz.Document` (C-level struct, usually efficient) -> `full_text` (Python String, UTF-8, High Overhead).
*   **NLP Phase:** `nltk.word_tokenize(text)` creates a `List[str]`. This explodes memory usage by 4-8x (pointer overhead + string objects).
*   **Example:** 10MB text -> Python String 10MB -> Tokens List ~50-80MB.

### Risk
*   **Batch Processing:** `PdfBatch` stores ALL results in `self.results`. Processing 1000 large PDFs will Crash the process (OOM).

---

## 3. Recommended Optimizations
1.  **Refactor `PdfBatch`:** Use a generator or callback system to yield results immediately and clear memory. Do NOT accumulate.
2.  **Multiprocessing:** Switch `run_in_executor` to use `ProcessPoolExecutor` for `_process_pdf` and `_analyze_content`.
3.  **Reuse Analyzer:** Move `ContentAnalyzer` to module scope or singleton.
4.  **Remove Dead Code:** Delete `TfidfVectorizer` from `search.py`.
