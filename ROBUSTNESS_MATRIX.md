# Robustness Matrix: PDF-Text-Analyzer

**Date:** 2026-02-04
**Auditor:** Antigravity

---

## 1. Failure Mode Enumerable

| Failure Mode | Current Behavior | Desired Behavior | Recommendation | Effort/Risk |
| :--- | :--- | :--- | :--- | :--- |
| **Invalid/Timeout URL** | `aiohttp.ClientError` caught, retried (backoff), then `ProcessingError`. | Explicit `DownloadError` with cause. | Create `DownloadError` subclass. | Low/Low |
| **Non-PDF Content (e.g., HTML)** | Checks `Content-Type` (warns), checks magic bytes (fails). | Fail fast on header check (configurable strictness). | Add `strict_content_type` flag. | Low/Low |
| **Oversized PDF (>100MB)** | Checks `Content-Length` header, then byte count post-download. | Stream download and abort if size exceeds limit. | Implement streaming download with chunk size monitoring. | Med/Med |
| **Encrypted (User Password)** | Checked via `doc.is_encrypted` -> tries empty pass -> fails later in `page_count` or extraction. | Explicitly check `doc.authenticate('')` result. | Simplify encryption check logic interactively. | Low/Low |
| **Scanned / Image-Only** | Returns `ExtractionStatus.SCANNED`, empty text. | Same, but notify caller explicitly in results. | No change needed, status is correct. | - |
| **Huge Text Content (OCR dump)** | `full_text` loaded into RAM, passed around as string. | Streaming processing / chunked analysis. | Generators for text extraction. | High/High |
| **NLTK Data Missing** | Downloads at runtime (slow/network dependent). | Check at startup, fail fast or warn properly. | Pre-download script or container build step. | Low/Low |
| **Language Detection Failure** | Defaults to "unknown" or crashes if text < 3 chars? | Fallback to "english" or "unknown" safely. | Wrap `detect()` in safe block with default. | Low/Low |

---

## 2. Error Handling Quality

### Current Gaps
*   **Swallowed Exceptions:** In `_process_pdf`, `fitz` exceptions are caught broadly as `ProcessingError`. This masks specific parsing issues (e.g., "damaged xref table").
*   **Implicit Control Flow:** Using exceptions for control flow in `_download_pdf` (raising `FileTooLargeError` inside loop). This is okay but makes debugging harder.
*   **Logging:** Generally good, structured logging used.

### Critical Risks (High Impact)
1.  **Memory Exhaustion (DoS):**
    *   **Risk:** Malicious user provides a valid 99MB PDF that expands to 10GB of text (ZIP bomb equivalent for PDF).
    *   **Mitigation:** Limit total extracted characters or tokens (e.g., `MAX_TEXT_CHARS = 10_000_000`).
2.  **Resource Leak:**
    *   **Risk:** `fitz.open` context manager handles file handle, but `aiohttp.ClientSession` creation inside `_download_pdf` is good.
    *   **Mitigation:** `PdfProcessor` should likely carry a session if reused heavily, pooling connections.

---

## 3. Defense Strategy
*   **Input Validation:** Strengthen URL and size checks.
*   **Resource Limits:** Add memory/CPU timeouts for `multiprocessing` workers if used (currently `asyncio` implementation only uses `run_in_executor`).
*   **Dependencies:** Vendor NLTK data or verify presence in Dockerfile/setup script.
