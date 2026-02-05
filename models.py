import dataclasses
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum

class ExtractionStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SCANNED = "scanned_ocr_required"
    ENCRYPTED = "encrypted"

@dataclass
class ProcessingStatistics:
    """Statistics about the PDF processing operation."""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_pages: int = 0
    processed_pages: int = 0
    total_words: int = 0
    processing_time: float = 0.0
    memory_used: float = 0.0

@dataclass
class PdfMetadata:
    """Enhanced metadata structure for PDF documents."""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    file_size: int = 0
    page_count: int = 0
    encrypted: bool = False
    permissions: Dict[str, bool] = field(default_factory=dict)
    extraction_status: ExtractionStatus = ExtractionStatus.SUCCESS

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary format."""
        data = dataclasses.asdict(self)
        # Convert Enum to string for serialization
        data['extraction_status'] = self.extraction_status.value
        return data
