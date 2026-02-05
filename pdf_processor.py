"""
Enhanced PDF Processing System
A comprehensive solution for PDF analysis, text extraction, and content processing
with advanced features including caching, async operations, and content analysis.
Version: 2.2.0
"""

import asyncio
import dataclasses
import hashlib
import multiprocessing
import os
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List

import aiohttp
import fitz
import nltk
from langdetect import detect

# Import from modules
from config import (
    MAX_PDF_SIZE, DOWNLOAD_TIMEOUT, MAX_RETRIES, 
    BACKOFF_FACTOR, ALLOWED_CONTENT_TYPES
)
from exceptions import (
    ProcessingError, InvalidFileError, EncryptedPdfError, 
    FileTooLargeError
)
from models import PdfMetadata, ProcessingStatistics, ExtractionStatus
from utils import setup_logging
from cache import Cache, SimpleMemoryCache
from text_analysis import ContentAnalyzer
from batch import PdfBatch
from search import PdfSearchEngine
from validators import validate_pdf_signature, validate_file_size

# Configure logging
logger = setup_logging()

class PdfProcessor:
    """Enhanced PDF processor with advanced features."""
    
    # Keep constants for backward compatibility
    MAX_PDF_SIZE = MAX_PDF_SIZE
    DOWNLOAD_TIMEOUT = DOWNLOAD_TIMEOUT
    MAX_RETRIES = MAX_RETRIES
    BACKOFF_FACTOR = BACKOFF_FACTOR
    
    def __init__(
        self,
        pdf_url: Optional[str] = None,
        cache: Optional[Cache] = None,
        max_workers: Optional[int] = None,
        storage_path: Optional[Path] = None
    ):
        """
        Initialize the PDF processor.
        
        Args:
            pdf_url: Optional URL of the PDF to process.
            cache: Optional cache instance.
            max_workers: Maximum number of threads for text extraction.
            storage_path: Path to store temporary data.
        """
        self.url = pdf_url
        self.cache = cache or SimpleMemoryCache()
        self.max_workers = max_workers or min(32, (multiprocessing.cpu_count() or 1) * 4)
        self.storage_path = storage_path or Path.home() / ".pdfprocessor"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.stats = ProcessingStatistics()
        self._correlation_id = '-'
        
        # Initialize NLTK data at startup
        self._ensure_nltk_data()
    
    def _ensure_nltk_data(self) -> None:
        """Ensure all required NLTK data is downloaded."""
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('tokenizers/punkt_tab')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading required NLTK data...")
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)
            nltk.download('stopwords', quiet=True)
    
    def _get_nltk_stopwords(self, language: str) -> set:
        """
        Map detected language code to NLTK language name and return its stopwords.
        If the mapping is not available, it attempts to use the provided language directly.
        """
        lang_mapping = {
            "en": "english",
            "fr": "french",
            "de": "german",
            "es": "spanish",
            "it": "italian",
            "pt": "portuguese",
            "nl": "dutch",
            "sv": "swedish",
            "no": "norwegian",
            "fi": "finnish",
            "ru": "russian"
            # Add more mappings as needed
        }
        nltk_lang = lang_mapping.get(language, language)
        try:
            return set(nltk.corpus.stopwords.words(nltk_lang))
        except LookupError:
            logger.warning(f"Stopwords not available for {nltk_lang}, using empty set")
            return set()
    
    async def process_url(self, url: str, word_or_phrase: str) -> Dict[str, Any]:
        """Process a PDF from URL."""
        self._correlation_id = hashlib.md5(url.encode()).hexdigest()[:8]
        self.stats.start_time = time.time()
        
        try:
            # Check cache
            cache_key = f"pdf_analysis_{hashlib.md5(url.encode()).hexdigest()}"
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info("Returning cached result")
                return cached_result
            
            # Download and validate
            content = await self._download_pdf(url)
            
            # Processing Phase
            text, metadata = await self._process_pdf(content)
            
            # If failed or scanned, skip analysis but return metadata
            if metadata.extraction_status != ExtractionStatus.SUCCESS:
                logger.warning(f"Analysis skipped due to status: {metadata.extraction_status.value}")
                analysis_results = {
                    'language': 'unknown',
                    'word_count': 0,
                    'keywords': [],
                    'text_preview': '[Analysis skipped: No extractable text found]'
                }
            else:
                # Analyze content
                analysis_results = await self._analyze_content(text, word_or_phrase)
            
            # Update statistics
            self.stats.end_time = time.time()
            self.stats.processing_time = self.stats.end_time - self.stats.start_time
            self.stats.total_words = analysis_results.get('word_count', 0)
            
            # Format timestamps for presentation
            stats_dict = dataclasses.asdict(self.stats)
            stats_dict['start_time'] = datetime.fromtimestamp(self.stats.start_time).isoformat()
            stats_dict['end_time'] = datetime.fromtimestamp(self.stats.end_time).isoformat() if self.stats.end_time else None
            
            # Prepare results without the full text
            results = {
                "metadata": metadata.to_dict(),
                "analysis": analysis_results,
                "statistics": stats_dict,
                "full_text": text
            }
            
            # Cache results
            self.cache.put(cache_key, results)
            
            return results
            
        except ProcessingError as e:
            logger.error(f"Processing error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise ProcessingError(f"Failed to process PDF: {str(e)}")
    
    async def _download_pdf(self, url: str) -> bytes:
        """Download PDF with strict validation."""
        async with aiohttp.ClientSession() as session:
            for attempt in range(MAX_RETRIES):
                try:
                    # Enforce strict size check if Content-Length is available
                    async with session.get(url, timeout=DOWNLOAD_TIMEOUT) as response:
                        response.raise_for_status()
                        
                        content_length = response.headers.get("Content-Length")
                        if content_length and int(content_length) > MAX_PDF_SIZE:
                            raise FileTooLargeError(f"File size exceeds limit ({content_length} bytes)")
                        
                        # Validate content type (advisory check)
                        content_type = response.headers.get("Content-Type", "").split(";")[0]
                        if content_type not in ALLOWED_CONTENT_TYPES:
                             logger.warning(f"Advisory: Unexpected content type {content_type}")

                        content = await response.read()
                        
                        if not validate_file_size(content):
                            raise FileTooLargeError("File size exceeds limit after download")
                            
                        if not validate_pdf_signature(content):
                            raise InvalidFileError("File does not have a valid PDF signature (%PDF-)")
                        
                        return content
                        
                except ProcessingError:
                    raise  # Re-raise known errors immediately
                except Exception as e:
                    if attempt == MAX_RETRIES - 1:
                        raise ProcessingError(f"Failed to download PDF: {str(e)}")
                    await asyncio.sleep(BACKOFF_FACTOR ** attempt)
    
    async def _process_pdf(self, content: bytes) -> tuple[str, PdfMetadata]:
        """Process PDF content with encryption and text checks."""
        def process_in_thread() -> tuple[str, PdfMetadata]:
            try:
                with fitz.open(stream=content, filetype="pdf") as doc:
                    # 1. Encryption Check (Fail Fast)
                    if doc.is_encrypted:
                        # Attempt to authenticate with empty password (some "encrypted" pdfs open fine)
                        # If failed, fitz usually raises specific errors or is_encrypted remains true without access
                        # We explicitly assume if it's encrypted and we can't get text, it's locked.
                        pass # fitz handles some transparent encryption. We check strictly below.

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
                    # If we can't access pages, it is effectively encrypted for us.
                    try:
                        _ = doc.page_count
                    except Exception:
                         raise EncryptedPdfError("PDF is encrypted and cannot be read.")

                    # Extract text
                    self.stats.total_pages = len(doc)
                    texts = []
                    
                    # Use ThreadPool only if we passed the encryption check
                    # Note: We need to be careful with PyMuPDF objects across threads.
                    # Text extraction is CPU bound, best done in this process or carefully managed.
                    # For safety in this thread-based executor (from _process_pdf wrapper), 
                    # we do simple iteration here to avoid complexity of nested executors or pickling errors.
                    
                    for page in doc:
                        text = page.get_text()
                        texts.append(text)
                        self.stats.processed_pages += 1
                        
                    full_text = ''.join(texts)
                    
                    # 3. Determine Status
                    status = ExtractionStatus.SUCCESS
                    if doc.is_encrypted and not full_text.strip():
                         status = ExtractionStatus.ENCRYPTED # Should likely have been caught above
                    elif not full_text.strip():
                        status = ExtractionStatus.SCANNED
                    
                    metadata = PdfMetadata(
                        **metadata_dict,
                        extraction_status=status
                    )
                    
                    return full_text, metadata
                    
            except Exception as e:
                # Catch specific fitz errors if they map to our domain
                if "password" in str(e).lower():
                    raise EncryptedPdfError("PDF requires password")
                raise ProcessingError(f"PDF parsing failed: {e}")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, process_in_thread)
    
    async def _analyze_content(self, text: str, word_or_phrase: str) -> Dict[str, Any]:
        """Perform content analysis with improved search term counting and output formatting."""
        try:
            # Short-circuit if empty
            if not text.strip():
                return {
                    'language': 'unknown',
                    'word_count': 0, 
                    'text_preview': '[No content to analyze]'
                }
                
            # Detect language using a snippet of text for efficiency
            language = detect(text[:10000]) if text.strip() else "unknown"
            
            # Initialize analyzer
            analyzer = ContentAnalyzer(language)
            
            loop = asyncio.get_event_loop()
            
            def analyze_in_thread():
                try:
                    words = nltk.word_tokenize(text.lower())
                    
                    # Use the helper to get the proper stopwords
                    stop_words = self._get_nltk_stopwords(language)
                    
                    # Count exact occurrences of the search term
                    search_term_count = len(re.findall(
                        rf'\\b{re.escape(word_or_phrase.lower())}\\b', 
                        text.lower()
                    ))
                    
                    # Extract keywords and find matching ones
                    keywords = analyzer.extract_keywords(text)
                    matching_keywords = [
                        (kw, score) for kw, score in keywords
                        if word_or_phrase.lower() in kw.lower()
                    ]
                    
                    # Filter out non-alphabetic tokens and stopwords for top words
                    top_words = dict(Counter(
                        word for word in words
                        if word.isalpha() and word not in stop_words
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
                    logger.error(f"Error in content analysis thread: {e}")
                    raise
            
            return await loop.run_in_executor(None, analyze_in_thread)
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return {
                'language': 'unknown',
                'word_count': len(text.split()),
                'character_count': len(text),
                'sentence_count': 0,
                'search_term_count': text.lower().count(word_or_phrase.lower()),
                'keywords': [],
                'matching_keywords': [],
                'readability_score': 0.0,
                'text_preview': text[:500] + "..." if len(text) > 500 else text,
                'top_words': {}
            }
    
    def main(self, word_or_phrase: str) -> Dict[str, Any]:
        """
        Synchronous wrapper to process the PDF using the stored URL.
        
        Args:
            word_or_phrase: The phrase to search in the PDF.
            
        Returns:
            A dictionary with metadata, analysis, and processing statistics.
        """
        if not self.url:
            raise ValueError("PDF URL not provided.")
        return asyncio.run(self.process_url(self.url, word_or_phrase))
    
    def __call__(self, word_or_phrase: str) -> Dict[str, Any]:
        """
        Allow the instance to be called directly as a function.
        
        Args:
            word_or_phrase: The phrase to search in the PDF.
            
        Returns:
            A dictionary with metadata, analysis, and processing statistics.
        """
        return self.main(word_or_phrase)

def print_pdf_summary(results: Dict[str, Any]) -> None:
    """Print a formatted summary of single PDF processing results."""
    metadata = results.get("metadata", {})
    analysis = results.get("analysis", {})
    statistics = results.get("statistics", {})
    
    print("\\n--- PDF Metadata ---")
    print(f"Status: {metadata.get('extraction_status', 'N/A').upper()}")
    for key, value in metadata.items():
        if key != 'extraction_status':
            print(f"{key.title()}: {value}")
            
    if metadata.get('extraction_status') == 'success':
        print("\\n--- PDF Analysis ---")
        print(f"Language: {analysis.get('language', 'N/A')}")
        print(f"Word Count: {analysis.get('word_count', 'N/A')}")
        print(f"Character Count: {analysis.get('character_count', 'N/A')}")
        print(f"Sentence Count: {analysis.get('sentence_count', 'N/A')}")
        print(f"Search Term Count: {analysis.get('search_term_count', 'N/A')}")
        print(f"Readability Score: {analysis.get('readability_score', 'N/A')}")
        print("Keywords:")
        for kw, score in analysis.get("keywords", []):
            print(f"  {kw}: {score:.2f}")
        print("Top Words:")
        for word, count in analysis.get("top_words", {}).items():
            print(f"  {word}: {count}")
        print("\\nText Preview:")
        print(analysis.get("text_preview", ""))
    
    print("\\n--- Processing Statistics ---")
    for key, value in statistics.items():
        print(f"{key.replace('_',' ').title()}: {value}")

def print_batch_summary(batch_results: Dict[str, Any]) -> None:
    """Print a formatted summary for batch processing results."""
    summary = batch_results.get("summary", {})
    print("\\n=== Batch Processing Summary ===")
    print(f"Total Processed: {summary.get('total_processed')}")
    print(f"Total Errors: {summary.get('total_errors')}")
    print(f"Success Rate: {summary.get('success_rate'):.2f}%")
    print(f"Average Processing Time: {summary.get('average_processing_time'):.2f} seconds")
    print(f"Total Pages Processed: {summary.get('total_pages_processed')}")

def print_search_results(search_results: List[Dict[str, Any]]) -> None:
    """Print formatted search results."""
    print("\\n=== Search Results ===")
    for result in search_results:
        metadata = result.get("metadata", {})
        print("\\n----------------------------------------")
        print(f"Title: {metadata.get('title', 'N/A')}")
        print(f"Status: {metadata.get('extraction_status', 'N/A')}")
        print(f"URL: {result.get('url', 'N/A')}")
        print(f"Relevance Score: {result.get('relevance_score', 'N/A')}")
        print(f"Snippet: {result.get('snippet', '')}")
        print("----------------------------------------\\n")

def setup_nltk_data() -> None:
    """Download required NLTK data."""
    required_packages = ['punkt', 'stopwords', 'averaged_perceptron_tagger']
    for package in required_packages:
        try:
            nltk.download(package, quiet=True)
            if package == 'punkt':
                nltk.download('punkt_tab', quiet=True)
        except Exception as e:
            logger.error(f"Failed to download NLTK package {package}: {e}")

async def main():
    """Example usage of the PDF processor with improved output presentation."""
    # Setup
    setup_nltk_data()
    
    # Initialize processor with cache
    processor = PdfProcessor(
        pdf_url="https://antilogicalism.com/wp-content/uploads/2017/07/atlas-shrugged.pdf",
        cache=SimpleMemoryCache(ttl_seconds=3600),
        storage_path=Path.home() / '.pdfprocessor'
    )
    
    search_term = "Who is John Galt?"
    
    try:
        # Process single PDF
        print("\\nProcessing single PDF...")
        results = await processor.process_url(processor.url, search_term)
        print_pdf_summary(results)
        
        # Process directory of PDFs (if a directory exists)
        print("\\nProcessing directory of PDFs...")
        directory = Path("./pdfs")  # Replace with actual directory if needed
        if directory.exists():
            batch_results = await PdfBatch(processor).process_urls(
                [f'file://{pdf_file.absolute()}' for pdf_file in directory.glob('**/*.pdf')],
                search_term
            )
            print_batch_summary(batch_results)
        
        # Search example
        print("\\nPerforming search...")
        search_engine = PdfSearchEngine()
        search_engine.add_document(processor.url, results['analysis'], results['metadata'], results.get('full_text'))
        search_results = search_engine.search(search_term)
        print_search_results(search_results)
        
    except ProcessingError as e:
        print(f"Known Processing Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Processing failed: {e}")

if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
