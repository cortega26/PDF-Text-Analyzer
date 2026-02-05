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
    
    async def process_stream(self, urls: List[str], word_or_phrase: str):
        """
        Process multiple URLs concurrently and yield results as they complete.
        Returns an AsyncGenerator yielding (url, result, error_message).
        """
        tasks = []
        # Create a mapping from task to URL to track which URL completed
        task_to_url = {}
        
        for url in urls:
            # We wrap the internal call to return the URL with the result/error
            task = asyncio.create_task(self._safe_process(url, word_or_phrase))
            tasks.append(task)
            task_to_url[task] = url
            
        for completed_task in asyncio.as_completed(tasks):
            url, result, error = await completed_task
            
            if error:
                self.errors[url] = error
            else:
                self.results[url] = result
                
            yield url, result, error

    async def _safe_process(self, url: str, word_or_phrase: str):
        try:
            result = await self.processor.process_url(url, word_or_phrase)
            return url, result, None
        except Exception as e:
            return url, None, str(e)

    async def process_urls(self, urls: List[str], word_or_phrase: str) -> Dict[str, Any]:
        """
        Process multiple URLs concurrently (Legacy Method).
        WARNING: Accumulates all results in memory.
        """
        async for _ in self.process_stream(urls, word_or_phrase):
            pass # We just consume the stream to populate self.results/self.errors
        
        return {
            'results': self.results,
            'errors': self.errors,
            'summary': self._generate_summary()
        }
    

    
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
