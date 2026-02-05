import pytest
from text_analysis import ContentAnalyzer
from unittest.mock import MagicMock, patch

# We mock TfidfVectorizer if feasible, or let it run (it's fast enough usually).
# But for hermeticity, strict pure logic is better. 
# ContentAnalyzer uses nltk, so we assume mocked NLTK data from conftest works or we patch internal calls.

def test_readability_score_simple():
    """Test Flesch Reading Ease calculation."""
    analyzer = ContentAnalyzer("en")
    
    # Simple calculation check
    # sentence count = 1, word count = 5, syllables approx 1 each
    # "Can you read this text?"
    text = "Can you read this text?" 
    
    # We patch nltk.sent_tokenize and syllabification to be 100% deterministic irrespective of NLTK models
    with patch('nltk.sent_tokenize', return_value=[text]):
        score = analyzer.calculate_readability_score(text)
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0

def test_readability_score_empty():
    """Test empty text returns 0.0."""
    analyzer = ContentAnalyzer("en")
    assert analyzer.calculate_readability_score("") == 0.0

def test_syllable_count():
    """Test private syllable counting logic."""
    analyzer = ContentAnalyzer("en")
    assert analyzer._count_syllables("hello") == 2
    assert analyzer._count_syllables("a") == 1
    assert analyzer._count_syllables("software") == 2 # Approximation logic
