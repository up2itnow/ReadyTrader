"""
In-memory store implementation for single-process deployments.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict, List, Optional

from .base import StoreBackend


class InMemoryStore(StoreBackend):
    """
    Thread-safe in-memory store implementation.

    Suitable for single-process deployments and testing.
    Data is lost on restart.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._data: Dict[str, str] = {}
        self._expiry: Dict[str, float] = {}
        self._hashes: Dict[str, Dict[str, str]] = defaultdict(dict)
        self._lists: Dict[str, List[str]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)

    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key not in self._expiry:
            return False
        return time.time() > self._expiry[key]

    def _cleanup_expired(self, key: str) -> None:
        """Remove expired key if necessary."""
        if self._is_expired(key):
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            self._hashes.pop(key, None)
            self._lists.pop(key, None)
            self._counters.pop(key, None)

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            self._cleanup_expired(key)
            return self._data.get(key)

    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        with self._lock:
            self._data[key] = value
            if ttl_seconds is not None and ttl_seconds > 0:
                self._expiry[key] = time.time() + ttl_seconds
            elif key in self._expiry:
                del self._expiry[key]
            return True

    def delete(self, key: str) -> bool:
        with self._lock:
            existed = key in self._data
            self._data.pop(key, None)
            self._expiry.pop(key, None)
            self._hashes.pop(key, None)
            self._lists.pop(key, None)
            self._counters.pop(key, None)
            return existed

    def exists(self, key: str) -> bool:
        with self._lock:
            self._cleanup_expired(key)
            return key in self._data or key in self._hashes or key in self._lists

    def expire(self, key: str, ttl_seconds: int) -> bool:
        with self._lock:
            if key not in self._data and key not in self._hashes and key not in self._lists:
                return False
            self._expiry[key] = time.time() + ttl_seconds
            return True

    def incr(self, key: str, amount: int = 1) -> int:
        with self._lock:
            self._cleanup_expired(key)
            self._counters[key] += amount
            return self._counters[key]

    def hget(self, name: str, key: str) -> Optional[str]:
        with self._lock:
            self._cleanup_expired(name)
            return self._hashes.get(name, {}).get(key)

    def hset(self, name: str, key: str, value: str) -> bool:
        with self._lock:
            self._hashes[name][key] = value
            return True

    def hgetall(self, name: str) -> Dict[str, str]:
        with self._lock:
            self._cleanup_expired(name)
            return dict(self._hashes.get(name, {}))

    def hdel(self, name: str, key: str) -> bool:
        with self._lock:
            if name in self._hashes and key in self._hashes[name]:
                del self._hashes[name][key]
                return True
            return False

    def lpush(self, key: str, value: str) -> int:
        with self._lock:
            self._lists[key].insert(0, value)
            return len(self._lists[key])

    def rpush(self, key: str, value: str) -> int:
        with self._lock:
            self._lists[key].append(value)
            return len(self._lists[key])

    def lpop(self, key: str) -> Optional[str]:
        with self._lock:
            if key in self._lists and self._lists[key]:
                return self._lists[key].pop(0)
            return None

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        with self._lock:
            lst = self._lists.get(key, [])
            # Redis-style inclusive end index
            if end == -1:
                return lst[start:]
            return lst[start : end + 1]

    def llen(self, key: str) -> int:
        with self._lock:
            return len(self._lists.get(key, []))

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        with self._lock:
            self._data.clear()
            self._expiry.clear()
            self._hashes.clear()
            self._lists.clear()
            self._counters.clear()
