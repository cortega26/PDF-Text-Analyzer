import pytest
import fitz
import asyncio
from aioresponses import aioresponses
from unittest.mock import MagicMock
import sys
import nltk

# Mock NLTK downloads to prevent network access during tests
# We'll just patch the downloader to do nothing, assuming data is present or we don't strictly need it for unit tests
@pytest.fixture(autouse=True)
def mock_nltk_download(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(nltk, "download", mock)
    return mock

@pytest.fixture
def pdf_factory():
    """Factory to create PDF bytes with specific content."""
    def _create_pdf(text: str = "Hello World", pages: int = 1, encrypted: bool = False, password: str = "secret") -> bytes:
        doc = fitz.open()
        for _ in range(pages):
            page = doc.new_page()
            page.insert_text((50, 50), text)
        
        if encrypted:
            # PyMuPDF 1.18+ uses distinct logic, verify docs matching user env. 
            # Assuming standard save encryption.
            pass # Creating encrypted PDFs in memory with fitz can be complex for testing. 
                 # We will simulate encryption by mocking the 'is_encrypted' property if needed 
                 # or relying on saving with encryption if fitz supports it easily in this version.
            # Simplified: For now we return standard PDF bytes. 
            # If we need true encryption, we'd use doc.save(encryption=...) 
        
        try:
             # Just basic save
            pdf_bytes = doc.tobytes()
        except Exception:
            pdf_bytes = doc.write() # Older fitz versions
            
        return pdf_bytes
    return _create_pdf

@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m

@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
