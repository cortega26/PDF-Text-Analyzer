
import unittest
from unittest.mock import MagicMock
import nltk
from search import PdfSearchEngine
from text_analysis import ContentAnalyzer

class TestFixes(unittest.TestCase):
    def setUp(self):
        # Ensure NLTK data (might need it)
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')
            nltk.download('punkt')

    def test_search_indexing_full_text(self):
        """Verify that PdfSearchEngine indexes full text, not just preview."""
        engine = PdfSearchEngine()
        
        # Create a document where the target word is NOT in the first 500 chars (preview)
        # but IS in the full text.
        dummy_preview = "Start of the document... " * 10 
        target_word = "SuperCALIFRAGILISTIC"
        full_text = dummy_preview + " " + target_word
        
        # Ensure target is not in preview
        self.assertNotIn(target_word, dummy_preview)
        
        analysis_mock = {
            'text_preview': dummy_preview,
            'keywords': [],
            'matching_keywords': [],
            'search_term_count': 1,
            'language': 'en'
        }
        metadata_mock = {'title': 'Test Doc'}
        
        # Add document with full_text
        engine.add_document("http://test.com", analysis_mock, metadata_mock, full_text=full_text)
        
        # Search
        results = engine.search(target_word)
        
        self.assertEqual(len(results), 1, "Should find the document based on full_text")
        self.assertEqual(results[0]['url'], "http://test.com")

    def test_nlp_language_stopwords(self):
        """Verify ContentAnalyzer loads correct stopwords for non-English languages."""
        
        # Test Spanish
        analyzer_es = ContentAnalyzer("es")
        # 'de' is a common Spanish stopword
        self.assertIn('de', analyzer_es.stop_words, "Spanish analyzer should include 'de' in stopwords")
        self.assertNotIn('the', analyzer_es.stop_words, "Spanish analyzer should NOT include 'the'")
        
        # Test English default
        analyzer_en = ContentAnalyzer("en")
        self.assertIn('the', analyzer_en.stop_words)

if __name__ == '__main__':
    unittest.main()
