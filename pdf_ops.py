
import asyncio
import re
import nltk
from collections import Counter
from typing import Dict, Any, List, Tuple
from concurrent.futures import Executor
from models import PdfMetadata, ExtractionStatus
from exceptions import EncryptedPdfError, ProcessingError
import fitz
from utils import setup_logging
from text_analysis import ContentAnalyzer

logger = setup_logging(__name__)

def process_pdf_content(content: bytes) -> Tuple[str, PdfMetadata]:
    """
    Process PDF content bytes to extract text and metadata.
    This pure function can be run in a separate process.
    """
    try:
        with fitz.open(stream=content, filetype="pdf") as doc:
            # 1. Encryption Check (Fail Fast)
            if doc.is_encrypted:
                # Attempt to authenticate with empty password
                pass 

            # Extract metadata
            raw_metadata = doc.metadata
            metadata_dict = {
                'title': raw_metadata.get('title'),
                'author': raw_metadata.get('author'),
                'subject': raw_metadata.get('subject'),
                'keywords': raw_metadata.get('keywords'),
                'creator': raw_metadata.get('creator'),
                'producer': raw_metadata.get('producer'),
                'creation_date': raw_metadata.get('creationDate'),
                'modification_date': raw_metadata.get('modDate'),
                'file_size': len(content),
                'page_count': len(doc),
                'encrypted': doc.is_encrypted,
                'permissions': {
                    'print': bool(doc.permissions & fitz.PDF_PERM_PRINT),
                    'modify': bool(doc.permissions & fitz.PDF_PERM_MODIFY),
                    'copy': bool(doc.permissions & fitz.PDF_PERM_COPY),
                    'annotate': bool(doc.permissions & fitz.PDF_PERM_ANNOTATE)
                }
            }
            
            # 2. Strict Encryption Stop
            try:
                _ = doc.page_count
            except Exception:
                 raise EncryptedPdfError("PDF is encrypted and cannot be read.")

            # Extract text
            texts = []
            for page in doc:
                text = page.get_text()
                texts.append(text)
                
            full_text = ''.join(texts)
            
            # 3. Determine Status
            status = ExtractionStatus.SUCCESS
            if doc.is_encrypted and not full_text.strip():
                 status = ExtractionStatus.ENCRYPTED 
            elif not full_text.strip():
                status = ExtractionStatus.SCANNED
            
            metadata = PdfMetadata(
                **metadata_dict,
                extraction_status=status
            )
            
            return full_text, metadata
            
    except Exception as e:
        if "password" in str(e).lower():
            raise EncryptedPdfError("PDF requires password")
        raise ProcessingError(f"PDF parsing failed: {e}")

def analyze_text_content(
        text: str, 
        word_or_phrase: str, 
        language: str, 
        analyzer: ContentAnalyzer,
        stopwords: set
    ) -> Dict[str, Any]:
    """
    Perform content analysis on text.
    Pure function (mostly, relies on passed analyzer).
    """
    try:
        words = nltk.word_tokenize(text.lower())
        
        # Count exact occurrences of the search term
        search_term_count = len(re.findall(
            rf'\\b{re.escape(word_or_phrase.lower())}\\b', 
            text.lower()
        ))
        
        # Extract keywords using the passed analyzer
        # Note: ContentAnalyzer is already initialized with language
        keywords = analyzer.extract_keywords(text)
        
        matching_keywords = [
            (kw, score) for kw, score in keywords
            if word_or_phrase.lower() in kw.lower()
        ]
        
        # Filter out non-alphabetic tokens and stopwords for top words
        top_words = dict(Counter(
            word for word in words
            if word.isalpha() and word not in stopwords
        ).most_common(10))
        
        # Create a preview of the text (first 500 characters)
        text_preview = text[:500] + "..." if len(text) > 500 else text
        
        return {
            'language': language,
            'word_count': len(words),
            'character_count': len(text),
            'sentence_count': len(nltk.sent_tokenize(text)),
            'search_term_count': search_term_count,
            'keywords': keywords,
            'matching_keywords': matching_keywords,
            'readability_score': analyzer.calculate_readability_score(text),
            'text_preview': text_preview,
            'top_words': top_words
        }
    except Exception as e:
        logger.error(f"Error in content analysis: {e}")
        raise
