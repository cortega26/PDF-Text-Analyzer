# Pipeline Failure Modes & Robustness Analysis

## 1. Classification of Failure Modes

| Failure Mode | Detection Strategy | Current Handling | Proposed Handling |
|--------------|-------------------|------------------|-------------------|
| **Invalid Magic Bytes** | Check file header for `%PDF-` | None (Relies on `fitz.open`) | **Reject early**: Read first 1024 bytes, check signature. |
| **Encrypted/Protected** | Check `doc.is_encrypted` | Checks `doc.is_encrypted` in metadata, but proceeds to extract. | **Abort with specific error**: If `is_encrypted` and no password, fail explicitly before extraction. |
| **Corrupted PDF** | `fitz.open` raises `RxError` or similar. | Generic `Exception` catch. | **Catch specific fitz errors**: Map to `CorruptedPdfError`. |
| **Empty File** | `len(content) == 0` | Implicitly handled? | **Explicit check**: `ProcessingError` if bytes=0. |
| **Zero Extractable Text** | `len(text.strip()) == 0` | Returns empty string. | **Flag as Scanned/Image-only**: Return specific status/warning in metadata. **Do NOT** auto-OCR, but report "OCR Required". |
| **Oversized Layout** | Page dimensions excessively large (plotters). | None. | **Log warning**: If dimensions > A0, log warning. |
| **Text Bomb / Loop** | Extraction never terminates. | Timeout (via `aiohttp` download, but not extraction). | **Timeout Enforcement**: Enforce per-page or global timeout during `get_text`. |

## 2. Pipeline Stage Diagram (Proposed)

```mermaid
graph TD
    A[URL Input] -->|Download| B{Network Success?}
    B -- No --> X[Error: NetworkError]
    B -- Yes --> C{Validation}
    C -->|Check Size| C1{> 100MB?}
    C -->|Check Valid PDF| C2{Has %PDF header?}
    C1 -- Yes --> X1[Error: FileTooLarge]
    C2 -- No --> X2[Error: InvalidPdfFormat]
    C --> D{Encryption Check}
    D -- Yes --> X3[Error: EncryptedPdf]
    D -- No --> E[Ingestion Phase]
    E -->|fitz.open| F[Metadata Extraction]
    F --> G[Text Extraction]
    G --> H{Has Text?}
    H -- No --> I[Status: Scanned/Empty (OCR Required)]
    H -- Yes --> J[Text Analysis]
    J --> K[Result]
```

## 3. Failure Detection Gaps
- **Late Failure**: Currently, we potentially read the whole file into memory before validating if it's even a PDF (relying on `Content-Type` header which is unreliable).
- **Silent Failures**: If a PDF is image-only, we currently return `""` (empty string) analysis. The user thinks it's processed but has 0 words. We must explicitly flag this.
- **Resource Exhaustion**: We read full content into RAM (`await response.read()`). streaming logic or strictly enforcing limit on read is better. (Config shows 100MB limit, but we download it all first).

## 4. Proposed Changes
1.  **Strict Validation Module**: Add `validators.py` to check headers/structure.
2.  **Structured Exceptions**: Add `EncryptedPdfError`, `InvalidPdfFormatError`, `EmptyPdfError` inheriting from `ProcessingError`.
3.  **Extraction Result Class**: instead of returning `(str, Metadata)`, return a `ExtractionResult` object containing `text`, `status` (SUCCESS, SCANNED, ENCRYPTED), and `errors`.
4.  **Memory Safety**: Enforce size limit *during* download chunking.
