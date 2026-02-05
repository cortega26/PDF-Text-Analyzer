# Scalability Review: PDF-Text-Analyzer

**Date:** 2026-02-04
**Auditor:** Antigravity

---

## 1. Scale Constraints

### Vertical Scaling (Single Machine)
| Constraint | Impact | Limit |
| :--- | :--- | :--- |
| **Memory** | **Critical.** `PdfBatch` accumulates ALL results in memory (`self.results` dict). A batch of 100 large PDFs (e.g., 50MB text each) will consume 50GB+ RAM. | ~20-50 simultaneous large PDFs depending on RAM. |
| **CPU (GIL)** | **Critical.** `asyncio` uses `ThreadPoolExecutor` (default) for `_process_pdf` and `_analyze_content`. Both `fitz` (parsing) and `nltk` (tokenization) are CPU heavy and contend for the Python GIL. | 1 Core effective utilization. Adding threads adds context switching overhead without speedup. |
| **I/O** | **Moderate.** Sequential/concurrent downloads work well due to `asyncio`. | Downlink bandwidth becomes the bottleneck before CPU if simple downloads are fast. |

### Horizontal Scaling (Distributed)
*   **Status:** Not supported. State is local (in-memory results).
*   **Blockers:** No queue mechanism (Celery/RQ), no external result store (Redis/DB).

---

## 2. Failure Handling at Scale
*   **Partial Failures:** `PdfBatch` captures exceptions in `self.errors` dict. If a single PDF crashes the process (e.g., C-extension segfault in `fitz` or memory error), the entire batch is lost.
*   **Recovery:** No checkpointing. A crash means restarting from zero.

---

## 3. Recommended Architecture Changes
1.  **Streaming Pipeline:**
    *   Change `PdfBatch.process_urls` to yield results as they complete (`async generator`).
    *   Write results to disk/DB immediately instead of accumulating.
2.  **Process Isolation:**
    *   Use `ProcessPoolExecutor` for CPU-bound tasks (`_process_pdf`, `_analyze_content`). This bypasses the GIL and utilizes multicore CPUs properly.
3.  **Checkpointing:**
    *   Maintain a simple ledger (e.g., SQLite or JSONL file) of processed URLs to allow resuming.

---

## 4. Complexity vs. Scale Trade-off
Current implementation is simple (in-memory list) but unscalable. Moving to a queue-based system adds significant complexity (Redis, Workers).
**Middle Ground:** Use `concurrent.futures.ProcessPoolExecutor` with an iterator interface and write results to JSONL files line-by-line. This solves memory and CPU issues without external infrastructure.
