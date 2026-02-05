import asyncio
import numpy as np
from typing import List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from pdf_processor import PdfProcessor

class PdfBatch:
    """Handle batch processing of multiple PDFs."""
    
    def __init__(self, processor: 'PdfProcessor'):
        self.processor = processor
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}
    
    async def process_urls(self, urls: List[str], word_or_phrase: str) -> Dict[str, Any]:
        """Process multiple URLs concurrently."""
        tasks = []
        for url in urls:
            task = asyncio.create_task(self._process_single_url(url, word_or_phrase))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        return {
            'results': self.results,
            'errors': self.errors,
            'summary': self._generate_summary()
        }
    
    async def _process_single_url(self, url: str, word_or_phrase: str) -> None:
        """Process a single URL."""
        try:
            result = await self.processor.process_url(url, word_or_phrase)
            self.results[url] = result
        except Exception as e:
            self.errors[url] = str(e)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate processing summary."""
        total_docs = len(self.results) + len(self.errors)
        return {
            'total_processed': len(self.results),
            'total_errors': len(self.errors),
            'success_rate': (len(self.results) / total_docs * 100) if total_docs > 0 else 0,
            'average_processing_time': np.mean([
                result['statistics']['processing_time']
                for result in self.results.values()
            ]) if self.results else 0,
            'total_pages_processed': sum(
                result['metadata']['page_count']
                for result in self.results.values()
            )
        }
