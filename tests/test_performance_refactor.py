
import unittest
from unittest.mock import MagicMock, patch
import asyncio
from pdf_processor import PdfProcessor
from text_analysis import ContentAnalyzer

class TestPerformanceRefactor(unittest.TestCase):
    def test_analyzer_caching(self):
        """Verify that PdfProcessor caches ContentAnalyzer instances."""
        processor = PdfProcessor(pdf_url="http://dummy")
        
        # Manually verify internal state (white-box test)
        self.assertEqual(len(processor.analyzers), 0)
        
        # Simulate analyzing English text
        # We need to run the async method properly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # First call
            loop.run_until_complete(processor._analyze_content("Hello world this is a test.", "test"))
            self.assertIn("en", processor.analyzers)
            self.assertEqual(len(processor.analyzers), 1)
            first_analyzer = processor.analyzers["en"]
            
            # Second call (same language)
            loop.run_until_complete(processor._analyze_content("Another english text.", "test"))
            self.assertEqual(len(processor.analyzers), 1)
            self.assertIs(processor.analyzers["en"], first_analyzer, "Should reuse the exact same instance")
            
            # Third call (different language)
            loop.run_until_complete(processor._analyze_content("Hola mundo esto es una prueba.", "prueba"))
            self.assertEqual(len(processor.analyzers), 2)
            self.assertIn("es", processor.analyzers)
            
        finally:
            loop.close()

if __name__ == '__main__':
    unittest.main()
