"""
Base store interface and factory for distributed storage.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class StoreBackend(ABC):
    """
    Abstract base class for distributed store backends.

    All store implementations must implement these methods for:
    - Key-value storage with TTL
    - List/queue operations
    - Hash/dict operations
    """

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        pass

    @abstractmethod
    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        """Set a value with optional TTL."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    def expire(self, key: str, ttl_seconds: int) -> bool:
        """Set expiration on a key."""
        pass

    @abstractmethod
    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter."""
        pass

    # Hash operations
    @abstractmethod
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get a hash field."""
        pass

    @abstractmethod
    def hset(self, name: str, key: str, value: str) -> bool:
        """Set a hash field."""
        pass

    @abstractmethod
    def hgetall(self, name: str) -> Dict[str, str]:
        """Get all fields in a hash."""
        pass

    @abstractmethod
    def hdel(self, name: str, key: str) -> bool:
        """Delete a hash field."""
        pass

    # List operations
    @abstractmethod
    def lpush(self, key: str, value: str) -> int:
        """Push to the left of a list."""
        pass

    @abstractmethod
    def rpush(self, key: str, value: str) -> int:
        """Push to the right of a list."""
        pass

    @abstractmethod
    def lpop(self, key: str) -> Optional[str]:
        """Pop from the left of a list."""
        pass

    @abstractmethod
    def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get a range of list elements."""
        pass

    @abstractmethod
    def llen(self, key: str) -> int:
        """Get list length."""
        pass

    # Pub/Sub operations (optional, for real-time updates)
    def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel."""
        return 0  # Default no-op

    def subscribe(self, channel: str, callback) -> None:
        """Subscribe to a channel."""
        pass  # Default no-op

    # Health check
    @abstractmethod
    def ping(self) -> bool:
        """Check if store is healthy."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connections."""
        pass


def get_store_backend() -> StoreBackend:
    """
    Factory function to get the configured store backend.

    Configure via environment:
    - STORE_BACKEND: "memory", "redis", "postgresql" (default: "memory")
    - REDIS_URL: Redis connection URL (for redis backend)
    - DATABASE_URL: PostgreSQL connection URL (for postgresql backend)
    """
    backend = os.getenv("STORE_BACKEND", "memory").strip().lower()

    if backend == "redis":
        from .redis_store import RedisStore

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return RedisStore(redis_url)

    elif backend in ("postgresql", "postgres", "pg"):
        from .postgres_store import PostgresStore

        db_url = os.getenv("DATABASE_URL", "postgresql://localhost/readytrader")
        return PostgresStore(db_url)

    else:
        from .memory_store import InMemoryStore

        return InMemoryStore()
