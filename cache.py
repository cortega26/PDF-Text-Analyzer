import time
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Dict, Any

# Type variables
CacheKey = TypeVar('CacheKey')
CacheValue = TypeVar('CacheValue')

class Cache(Generic[CacheKey, CacheValue], ABC):
    """Protocol defining the cache interface."""
    
    @abstractmethod
    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """Retrieve a value from cache."""
        pass
    
    @abstractmethod
    def put(self, key: CacheKey, value: CacheValue) -> None:
        """Store a value in cache."""
        pass
    
    @abstractmethod
    def invalidate(self, key: CacheKey) -> None:
        """Remove a value from cache."""
        pass

class SimpleMemoryCache(Cache[str, Any]):
    """Simple in-memory cache implementation with TTL."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        value, timestamp = self._cache[key]
        if time.time() - timestamp > self._ttl_seconds:
            del self._cache[key]
            return None
        return value
    
    def put(self, key: str, value: Any) -> None:
        self._cache[key] = (value, time.time())
    
    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)
