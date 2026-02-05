# Configuration constants
MAX_PDF_SIZE = 100 * 1024 * 1024  # 100MB
DOWNLOAD_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
BACKOFF_FACTOR = 2
CACHE_SIZE = 100
CHUNK_SIZE = 8192
ALLOWED_CONTENT_TYPES = {'application/pdf', 'application/x-pdf'}
