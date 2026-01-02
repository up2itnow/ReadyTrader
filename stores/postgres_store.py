"""
PostgreSQL store implementation for distributed deployments.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Dict, List, Optional

from .base import StoreBackend

logger = logging.getLogger(__name__)


class PostgresStore(StoreBackend):
    """
    PostgreSQL-backed store for distributed deployments.

    Provides ACID-compliant, distributed storage with:
    - Connection pooling via SQLAlchemy
    - TTL support via background cleanup
    - JSON storage for complex values
    - Transaction support

    Requires: psycopg2-binary and sqlalchemy packages
    """

    def __init__(self, database_url: str = "postgresql://localhost/readytrader"):
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.pool import QueuePool
        except ImportError:
            raise ImportError("SQLAlchemy not installed. Install with: pip install sqlalchemy psycopg2-binary")

        self._url = database_url
        self._engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
        )

        # Initialize schema
        self._init_schema()
        logger.info(f"Connected to PostgreSQL at {database_url}")

    def _init_schema(self):
        """Create necessary tables if they don't exist."""
        from sqlalchemy import text

        with self._engine.connect() as conn:
            # Key-value store table
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key VARCHAR(512) PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )

            # Hash store table
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS hash_store (
                    name VARCHAR(512) NOT NULL,
                    key VARCHAR(512) NOT NULL,
                    value TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    PRIMARY KEY (name, key)
                )
            """)
            )

            # List store table (using JSONB array)
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS list_store (
                    key VARCHAR(512) PRIMARY KEY,
                    items JSONB DEFAULT '[]'::jsonb,
                    expires_at TIMESTAMP
                )
            """)
            )

            # Counter store table
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS counter_store (
                    key VARCHAR(512) PRIMARY KEY,
                    value BIGINT DEFAULT 0,
                    expires_at TIMESTAMP
                )
            """)
            )

            # Create indexes
            conn.execute(
                text("""
                CREATE INDEX IF NOT EXISTS idx_kv_expires ON kv_store(expires_at)
                WHERE expires_at IS NOT NULL
            """)
            )

            conn.commit()

    def _now_timestamp(self) -> str:
        """Get current timestamp string."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    def get(self, key: str) -> Optional[str]:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT value FROM kv_store 
                        WHERE key = :key 
                        AND (expires_at IS NULL OR expires_at > NOW())
                    """),
                    {"key": key},
                ).fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"PostgreSQL GET error: {e}")
            return None

    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                expires_at = None
                if ttl_seconds is not None and ttl_seconds > 0:
                    expires_at = f"NOW() + INTERVAL '{ttl_seconds} seconds'"

                if expires_at:
                    conn.execute(
                        text(f"""
                            INSERT INTO kv_store (key, value, expires_at, updated_at)
                            VALUES (:key, :value, {expires_at}, NOW())
                            ON CONFLICT (key) DO UPDATE SET 
                                value = EXCLUDED.value,
                                expires_at = EXCLUDED.expires_at,
                                updated_at = NOW()
                        """),
                        {"key": key, "value": value},
                    )
                else:
                    conn.execute(
                        text("""
                            INSERT INTO kv_store (key, value, expires_at, updated_at)
                            VALUES (:key, :value, NULL, NOW())
                            ON CONFLICT (key) DO UPDATE SET 
                                value = EXCLUDED.value,
                                expires_at = NULL,
                                updated_at = NOW()
                        """),
                        {"key": key, "value": value},
                    )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"PostgreSQL SET error: {e}")
            return False

    def delete(self, key: str) -> bool:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("DELETE FROM kv_store WHERE key = :key"), {"key": key})
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"PostgreSQL DELETE error: {e}")
            return False

    def exists(self, key: str) -> bool:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT 1 FROM kv_store 
                        WHERE key = :key 
                        AND (expires_at IS NULL OR expires_at > NOW())
                    """),
                    {"key": key},
                ).fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"PostgreSQL EXISTS error: {e}")
            return False

    def expire(self, key: str, ttl_seconds: int) -> bool:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(
                    text(f"""
                        UPDATE kv_store 
                        SET expires_at = NOW() + INTERVAL '{ttl_seconds} seconds'
                        WHERE key = :key
                    """),
                    {"key": key},
                )
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"PostgreSQL EXPIRE error: {e}")
            return False

    def incr(self, key: str, amount: int = 1) -> int:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(
                    text("""
                        INSERT INTO counter_store (key, value)
                        VALUES (:key, :amount)
                        ON CONFLICT (key) DO UPDATE SET value = counter_store.value + :amount
                        RETURNING value
                    """),
                    {"key": key, "amount": amount},
                ).fetchone()
                conn.commit()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"PostgreSQL INCR error: {e}")
            return 0

    def hget(self, name: str, key: str) -> Optional[str]:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT value FROM hash_store 
                        WHERE name = :name AND key = :key
                        AND (expires_at IS NULL OR expires_at > NOW())
                    """),
                    {"name": name, "key": key},
                ).fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"PostgreSQL HGET error: {e}")
            return None

    def hset(self, name: str, key: str, value: str) -> bool:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO hash_store (name, key, value)
                        VALUES (:name, :key, :value)
                        ON CONFLICT (name, key) DO UPDATE SET value = EXCLUDED.value
                    """),
                    {"name": name, "key": key, "value": value},
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"PostgreSQL HSET error: {e}")
            return False

    def hgetall(self, name: str) -> Dict[str, str]:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                results = conn.execute(
                    text("""
                        SELECT key, value FROM hash_store 
                        WHERE name = :name
                        AND (expires_at IS NULL OR expires_at > NOW())
                    """),
                    {"name": name},
                ).fetchall()
                return {row[0]: row[1] for row in results}
        except Exception as e:
            logger.error(f"PostgreSQL HGETALL error: {e}")
            return {}

    def hdel(self, name: str, key: str) -> bool:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("DELETE FROM hash_store WHERE name = :name AND key = :key"), {"name": name, "key": key})
                conn.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"PostgreSQL HDEL error: {e}")
            return False

    def lpush(self, key: str, value: str) -> int:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                # Insert at beginning of array
                conn.execute(
                    text("""
                        INSERT INTO list_store (key, items)
                        VALUES (:key, jsonb_build_array(:value))
                        ON CONFLICT (key) DO UPDATE SET 
                            items = jsonb_build_array(:value) || list_store.items
                    """),
                    {"key": key, "value": value},
                )
                result = conn.execute(text("SELECT jsonb_array_length(items) FROM list_store WHERE key = :key"), {"key": key}).fetchone()
                conn.commit()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"PostgreSQL LPUSH error: {e}")
            return 0

    def rpush(self, key: str, value: str) -> int:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                # Append to end of array
                conn.execute(
                    text("""
                        INSERT INTO list_store (key, items)
                        VALUES (:key, jsonb_build_array(:value))
                        ON CONFLICT (key) DO UPDATE SET 
                            items = list_store.items || jsonb_build_array(:value)
                    """),
                    {"key": key, "value": value},
                )
                result = conn.execute(text("SELECT jsonb_array_length(items) FROM list_store WHERE key = :key"), {"key": key}).fetchone()
                conn.commit()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"PostgreSQL RPUSH error: {e}")
            return 0

    def lpop(self, key: str) -> Optional[str]:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(
                    text("""
                        UPDATE list_store
                        SET items = items - 0
                        WHERE key = :key AND jsonb_array_length(items) > 0
                        RETURNING items->0
                    """),
                    {"key": key},
                ).fetchone()
                conn.commit()
                if result and result[0]:
                    return json.loads(result[0]) if isinstance(result[0], str) else result[0]
                return None
        except Exception as e:
            logger.error(f"PostgreSQL LPOP error: {e}")
            return None

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT items FROM list_store WHERE key = :key"), {"key": key}).fetchone()
                if not result:
                    return []
                items = result[0] if isinstance(result[0], list) else json.loads(result[0])
                if end == -1:
                    return items[start:]
                return items[start : end + 1]
        except Exception as e:
            logger.error(f"PostgreSQL LRANGE error: {e}")
            return []

    def llen(self, key: str) -> int:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT jsonb_array_length(items) FROM list_store WHERE key = :key"), {"key": key}).fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"PostgreSQL LLEN error: {e}")
            return 0

    def ping(self) -> bool:
        from sqlalchemy import text

        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception:
            return False

    def close(self) -> None:
        try:
            self._engine.dispose()
        except Exception as e:
            logger.error(f"PostgreSQL close error: {e}")

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from all tables.

        Should be called periodically (e.g., via cron or background task).
        Returns total number of rows deleted.
        """
        from sqlalchemy import text

        total = 0
        try:
            with self._engine.connect() as conn:
                for table in ["kv_store", "hash_store", "list_store", "counter_store"]:
                    result = conn.execute(text(f"DELETE FROM {table} WHERE expires_at IS NOT NULL AND expires_at < NOW()"))
                    total += result.rowcount
                conn.commit()
            logger.info(f"Cleaned up {total} expired entries")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        return total
