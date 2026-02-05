class ProcessingError(Exception):
    """Base exception for PDF processing errors."""
    pass

class InvalidFileError(ProcessingError):
    """Raised when the file is not a valid PDF."""
    pass

class EncryptedPdfError(ProcessingError):
    """Raised when the PDF is encrypted and cannot be processed."""
    pass

class EmptyContentError(ProcessingError):
    """Raised when the PDF contains no extractable content."""
    pass

class FileTooLargeError(ProcessingError):
    """Raised when the file exceeds the maximum allowed size."""
    pass
