"""
Distributed store implementations for horizontal scaling.

This module provides pluggable storage backends:
- SQLite (default, single-process)
- Redis (distributed, high-performance)
- PostgreSQL (distributed, ACID-compliant)

Configure via STORE_BACKEND environment variable:
- "sqlite" (default)
- "redis" (requires REDIS_URL)
- "postgresql" (requires DATABASE_URL)
"""

from .base import StoreBackend, get_store_backend
from .memory_store import InMemoryStore
from .postgres_store import PostgresStore
from .redis_store import RedisStore

__all__ = [
    "StoreBackend",
    "get_store_backend",
    "RedisStore",
    "PostgresStore",
    "InMemoryStore",
]
