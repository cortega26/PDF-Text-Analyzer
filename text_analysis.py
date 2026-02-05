import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Tuple
from utils import setup_logging

logger = setup_logging(__name__)

class ContentAnalyzer:
    """Analyzes text content using various NLP techniques."""
    
    def __init__(self, language: str):
        self.language = language
        self.vectorizer = TfidfVectorizer(
            stop_words='english', 
            max_features=1000,
            ngram_range=(1, 2)
        )
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """Extract important keywords using TF-IDF."""
        try:
            tfidf_matrix = self.vectorizer.fit_transform([text])
            feature_names = self.vectorizer.get_feature_names_out()
            scores = zip(feature_names, tfidf_matrix.toarray()[0])
            sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
            return sorted_scores[:top_n]
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []
    
    def calculate_readability_score(self, text: str) -> float:
        """Calculate text readability using Flesch Reading Ease."""
        try:
            words = text.split()
            sentences = nltk.sent_tokenize(text)
            
            if not words or not sentences:
                return 0.0
            
            word_count = len(words)
            sentence_count = len(sentences)
            syllable_count = sum(self._count_syllables(word) for word in words)
            
            score = 206.835 - 1.015 * (word_count / sentence_count)
            if word_count > 0:
                score -= 84.6 * (syllable_count / word_count)
            
            return round(max(0.0, min(100.0, score)), 2)
        except Exception as e:
            logger.error(f"Readability calculation failed: {e}")
            return 0.0
    
    @staticmethod
    def _count_syllables(word: str) -> int:
        """Count syllables in a word."""
        word = word.lower().strip()
        if not word:
            return 0
            
        count = 0
        vowels = set("aeiouy")
        prev_char = None
        
        for char in word:
            if char in vowels and (prev_char is None or prev_char not in vowels):
                count += 1
            prev_char = char
            
        if word.endswith(('e', 'es', 'ed')) and count > 1:
            count -= 1
        
        return max(1, count)
