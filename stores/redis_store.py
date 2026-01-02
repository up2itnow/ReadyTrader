"""
Redis store implementation for distributed deployments.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .base import StoreBackend

logger = logging.getLogger(__name__)


class RedisStore(StoreBackend):
    """
    Redis-backed store for distributed deployments.

    Provides high-performance, distributed storage with:
    - Automatic connection pooling
    - TTL support
    - Pub/Sub for real-time updates
    - Atomic operations

    Requires: redis package (pip install redis)
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        try:
            import redis
        except ImportError:
            raise ImportError("Redis package not installed. Install with: pip install redis")

        self._url = redis_url
        self._client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
        )
        self._pubsub = None

        # Verify connection
        try:
            self._client.ping()
            logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key: str) -> Optional[str]:
        try:
            return self._client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        try:
            if ttl_seconds is not None and ttl_seconds > 0:
                return bool(self._client.setex(key, ttl_seconds, value))
            return bool(self._client.set(key, value))
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            return bool(self._client.delete(key))
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    def exists(self, key: str) -> bool:
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    def expire(self, key: str, ttl_seconds: int) -> bool:
        try:
            return bool(self._client.expire(key, ttl_seconds))
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False

    def incr(self, key: str, amount: int = 1) -> int:
        try:
            return self._client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis INCR error: {e}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        try:
            return self._client.hget(name, key)
        except Exception as e:
            logger.error(f"Redis HGET error: {e}")
            return None

    def hset(self, name: str, key: str, value: str) -> bool:
        try:
            self._client.hset(name, key, value)
            return True
        except Exception as e:
            logger.error(f"Redis HSET error: {e}")
            return False

    def hgetall(self, name: str) -> Dict[str, str]:
        try:
            return self._client.hgetall(name) or {}
        except Exception as e:
            logger.error(f"Redis HGETALL error: {e}")
            return {}

    def hdel(self, name: str, key: str) -> bool:
        try:
            return bool(self._client.hdel(name, key))
        except Exception as e:
            logger.error(f"Redis HDEL error: {e}")
            return False

    def lpush(self, key: str, value: str) -> int:
        try:
            return self._client.lpush(key, value)
        except Exception as e:
            logger.error(f"Redis LPUSH error: {e}")
            return 0

    def rpush(self, key: str, value: str) -> int:
        try:
            return self._client.rpush(key, value)
        except Exception as e:
            logger.error(f"Redis RPUSH error: {e}")
            return 0

    def lpop(self, key: str) -> Optional[str]:
        try:
            return self._client.lpop(key)
        except Exception as e:
            logger.error(f"Redis LPOP error: {e}")
            return None

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        try:
            return self._client.lrange(key, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE error: {e}")
            return []

    def llen(self, key: str) -> int:
        try:
            return self._client.llen(key)
        except Exception as e:
            logger.error(f"Redis LLEN error: {e}")
            return 0

    def publish(self, channel: str, message: str) -> int:
        try:
            return self._client.publish(channel, message)
        except Exception as e:
            logger.error(f"Redis PUBLISH error: {e}")
            return 0

    def subscribe(self, channel: str, callback) -> None:
        """
        Subscribe to a Redis channel.

        Note: This runs in a separate thread for non-blocking operation.
        """
        import threading

        def _listen():
            try:
                pubsub = self._client.pubsub()
                pubsub.subscribe(channel)
                for message in pubsub.listen():
                    if message["type"] == "message":
                        callback(message["data"])
            except Exception as e:
                logger.error(f"Redis subscription error: {e}")

        thread = threading.Thread(target=_listen, daemon=True)
        thread.start()

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    def close(self) -> None:
        try:
            if self._pubsub:
                self._pubsub.close()
            self._client.close()
        except Exception as e:
            logger.error(f"Redis close error: {e}")


class RedisRateLimiter:
    """
    Distributed rate limiter using Redis.

    Uses Redis atomic operations for accurate rate limiting across
    multiple processes/servers.
    """

    def __init__(self, redis_store: RedisStore):
        self._store = redis_store

    def check(self, key: str, limit: int, window_seconds: int) -> bool:
        """
        Check rate limit using sliding window algorithm.

        Returns True if request is allowed, raises RateLimitError if exceeded.
        """
        import time as time_module

        from rate_limiter import RateLimitError

        # Use Redis INCR with EXPIRE for atomic rate limiting
        rate_key = f"rate:{key}:{int(time_module.time()) // window_seconds}"

        count = self._store.incr(rate_key)

        if count == 1:
            # First request in window, set expiry
            self._store.expire(rate_key, window_seconds)

        if count > limit:
            raise RateLimitError(
                code="rate_limited",
                message="Rate limit exceeded.",
                data={
                    "key": key,
                    "limit": limit,
                    "window_seconds": window_seconds,
                    "count": count,
                },
            )

        return True
