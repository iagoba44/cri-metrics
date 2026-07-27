"""Cache TTL en memoria para APIs externas."""
import time
import threading
from typing import Any, Dict, Optional

class TTLCache:
    def __init__(self, default_ttl: int = 300):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expiry = entry
            if time.time() > expiry:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int = None):
        with self._lock:
            expiry = time.time() + (ttl or self._default_ttl)
            self._cache[key] = (value, expiry)

    def clear(self):
        with self._lock:
            self._cache.clear()

# Singleton
_cache_instance = None

def get_cache() -> TTLCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TTLCache()
    return _cache_instance


def cached(ttl: int = 300):
    """Decorador para cachear resultados de funciones."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache()
            key = f"{func.__module__}.{func.__qualname__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator
