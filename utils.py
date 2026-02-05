import logging
import sys

# Custom logging filter for correlation ID
class CorrelationFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = '-'
        return True

def setup_logging(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)
    # Only add handler if not already present to avoid duplicates
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] %(message)s'
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler.addFilter(CorrelationFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
