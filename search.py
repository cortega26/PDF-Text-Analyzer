import hashlib
import nltk
from collections import defaultdict
from typing import Dict, Any, List, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from utils import setup_logging

logger = setup_logging(__name__)

class PdfSearchEngine:
    """Search engine for processed PDF content."""
    
    def __init__(self):
        self.index = defaultdict(list)
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)
        )
    
    def add_document(self, url: str, analysis_results: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        """Add a document to the search index using analysis results."""
        doc_id = hashlib.md5(url.encode()).hexdigest()
        
        # Extract text content from analysis results (using the preview)
        content = analysis_results.get('text_preview', '')
        
        self.documents[doc_id] = {
            'url': url,
            'metadata': metadata,
            'content': content,
            'keywords': analysis_results.get('keywords', []),
            'matching_keywords': analysis_results.get('matching_keywords', []),
            'search_term_count': analysis_results.get('search_term_count', 0),
            'language': analysis_results.get('language', 'unknown')
        }
        
        # Index words from content
        words = set(word.lower() for word in nltk.word_tokenize(content))
        for word in words:
            self.index[word].append(doc_id)
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for documents matching query."""
        query_words = set(word.lower() for word in nltk.word_tokenize(query))
        
        # Calculate document scores
        doc_scores = defaultdict(float)
        for word in query_words:
            matching_docs = self.index.get(word, [])
            word_score = 1.0 / (len(matching_docs) if matching_docs else 1.0)
            for doc_id in matching_docs:
                doc_scores[doc_id] += word_score
        
        # Sort documents by score
        sorted_docs = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        # Format results
        results = []
        for doc_id, score in sorted_docs:
            doc = self.documents[doc_id]
            snippet = self._generate_snippet(doc['content'], query_words)
            
            results.append({
                'url': doc['url'],
                'metadata': doc['metadata'],
                'relevance_score': round(score, 3),
                'snippet': snippet,
                'language': doc['language'],
                'search_term_count': doc['search_term_count'],
                'matching_keywords': [
                    {'keyword': kw, 'score': score}
                    for kw, score in doc['matching_keywords']
                ]
            })
        
        return results
    
    def _generate_snippet(self, content: str, query_words: Set[str], 
                         context_words: int = 10) -> str:
        """Generate a relevant text snippet containing query words."""
        words = content.split()
        best_snippet = ""
        max_matches = 0
        
        # Slide a window over the text to find the best matching context
        for i in range(len(words)):
            window = words[i:i + context_words * 2]
            if not window:
                break
            
            # Count query word matches in this window
            matches = sum(1 for word in window 
                         if word.lower() in query_words)
            
            # Update best snippet if this window has more matches
            if matches > max_matches:
                max_matches = matches
                best_snippet = ' '.join(window)
        
        # Add ellipsis if we have a snippet
        return f"{best_snippet}..." if best_snippet else ""
