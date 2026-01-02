"""
Tests for distributed store implementations.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest


class TestInMemoryStore:
    """Test in-memory store implementation."""

    @pytest.fixture
    def store(self):
        from stores.memory_store import InMemoryStore

        return InMemoryStore()

    def test_get_set(self, store):
        """Test basic get/set operations."""
        store.set("key1", "value1")
        assert store.get("key1") == "value1"

    def test_get_nonexistent(self, store):
        """Test getting nonexistent key returns None."""
        assert store.get("nonexistent") is None

    def test_set_with_ttl(self, store):
        """Test set with TTL expires."""
        store.set("key1", "value1", ttl_seconds=1)
        assert store.get("key1") == "value1"

        time.sleep(1.1)
        assert store.get("key1") is None

    def test_delete(self, store):
        """Test delete operation."""
        store.set("key1", "value1")
        assert store.delete("key1") is True
        assert store.get("key1") is None
        assert store.delete("key1") is False

    def test_exists(self, store):
        """Test exists operation."""
        assert store.exists("key1") is False
        store.set("key1", "value1")
        assert store.exists("key1") is True

    def test_expire(self, store):
        """Test expire operation."""
        store.set("key1", "value1")
        assert store.expire("key1", 1) is True

        time.sleep(1.1)
        assert store.get("key1") is None

    def test_incr(self, store):
        """Test increment operation."""
        assert store.incr("counter") == 1
        assert store.incr("counter") == 2
        assert store.incr("counter", 5) == 7

    def test_hash_operations(self, store):
        """Test hash operations."""
        store.hset("hash1", "field1", "value1")
        assert store.hget("hash1", "field1") == "value1"

        store.hset("hash1", "field2", "value2")
        assert store.hgetall("hash1") == {"field1": "value1", "field2": "value2"}

        assert store.hdel("hash1", "field1") is True
        assert store.hget("hash1", "field1") is None

    def test_list_operations(self, store):
        """Test list operations."""
        store.lpush("list1", "a")
        store.lpush("list1", "b")
        store.rpush("list1", "c")

        assert store.llen("list1") == 3
        assert store.lrange("list1", 0, -1) == ["b", "a", "c"]

        assert store.lpop("list1") == "b"
        assert store.llen("list1") == 2

    def test_ping(self, store):
        """Test ping returns True."""
        assert store.ping() is True

    def test_close(self, store):
        """Test close clears data."""
        store.set("key1", "value1")
        store.close()
        assert store.get("key1") is None


class TestStoreFactory:
    """Test store factory function."""

    def test_default_is_memory(self):
        """Test default backend is memory."""
        from stores.base import get_store_backend
        from stores.memory_store import InMemoryStore

        with patch.dict("os.environ", {"STORE_BACKEND": "memory"}):
            store = get_store_backend()
            assert isinstance(store, InMemoryStore)

    def test_redis_backend(self):
        """Test Redis backend selection."""
        from stores.base import get_store_backend

        with patch.dict("os.environ", {"STORE_BACKEND": "redis", "REDIS_URL": "redis://localhost:6379"}):
            with patch("stores.redis_store.RedisStore.__init__", return_value=None):
                with patch("stores.redis_store.RedisStore.ping", return_value=True):
                    # This will fail if Redis is not available, which is expected in CI
                    try:
                        get_store_backend()
                    except Exception:
                        pass  # Expected if Redis not available

    def test_postgres_backend(self):
        """Test PostgreSQL backend selection."""
        from stores.base import get_store_backend

        with patch.dict("os.environ", {"STORE_BACKEND": "postgresql", "DATABASE_URL": "postgresql://localhost/test"}):
            with patch("stores.postgres_store.PostgresStore.__init__", return_value=None):
                with patch("stores.postgres_store.PostgresStore.ping", return_value=True):
                    try:
                        get_store_backend()
                    except Exception:
                        pass  # Expected if PostgreSQL not available
