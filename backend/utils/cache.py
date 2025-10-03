import time
from typing import Any, Optional

# Simple in-memory TTL cache. For production, swap with Redis.
_store = {}
_ttl = 600  # default seconds; can be overridden when integration improves

def cache_get(key: str) -> Optional[Any]:
    item = _store.get(key)
    if not item:
        return None
    value, expires_at = item
    if expires_at and expires_at < time.time():
        _store.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    global _ttl
    expires = None
    if (ttl or _ttl) > 0:
        expires = time.time() + (ttl or _ttl)
    _store[key] = (value, expires)
