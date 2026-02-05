
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from batch import PdfBatch

class TestBatchStreaming(unittest.TestCase):
    def test_streaming_yields(self):
        """Verify process_stream yields results as they complete."""
        
        # Mock processor
        mock_processor = MagicMock()
        mock_processor.process_url = AsyncMock()
        
        # Setup delays: URL1 takes 0.2s, URL2 takes 0.05s
        # We expect URL2 to be yielded BEFORE URL1
        async def delayed_process(url, phrase):
            if "slow" in url:
                await asyncio.sleep(0.2)
                return {"id": "slow"}
            else:
                await asyncio.sleep(0.01)
                return {"id": "fast"}
        
        mock_processor.process_url.side_effect = delayed_process
        
        batch = PdfBatch(mock_processor)
        
        async def run_test():
            urls = ["http://slow.com", "http://fast.com"]
            results = []
            
            async for url, res, err in batch.process_stream(urls, "test"):
                results.append((url, res, err))
                
            return results

        results = asyncio.run(run_test())
        
        self.assertEqual(len(results), 2)
        
        # Check order: Fast should be first
        self.assertEqual(results[0][0], "http://fast.com")
        self.assertEqual(results[1][0], "http://slow.com")
        
        # Verify backward compatibility (process_urls still works)
        # We can't reuse the same loop easily, so we run a fresh check or just trust the logic if stream works
        
    def test_backward_compatibility(self):
        """Verify process_urls still returns the dict."""
        mock_processor = MagicMock()
        mock_processor.process_url = AsyncMock(return_value={"meta": "data", "statistics": {"processing_time": 0.1}, "metadata": {"page_count": 1}})
        
        batch = PdfBatch(mock_processor)
        
        res = asyncio.run(batch.process_urls(["http://test.com"], "foo"))
        
        self.assertIn("results", res)
        self.assertIn("summary", res)
        self.assertEqual(len(res['results']), 1)

if __name__ == '__main__':
    unittest.main()
