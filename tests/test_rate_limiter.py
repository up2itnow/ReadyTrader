"""
Comprehensive tests for rate limiting functionality.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from rate_limiter import FixedWindowRateLimiter, RateLimitError


@pytest.fixture
def rate_limiter():
    return FixedWindowRateLimiter()


class TestFixedWindowRateLimiter:
    """Test fixed window rate limiting."""

    def test_allows_requests_under_limit(self, rate_limiter):
        """Test requests under limit pass through."""
        for _ in range(5):
            rate_limiter.check(key="test_key", limit=10, window_seconds=60)
        # Should not raise

    def test_blocks_requests_over_limit(self, rate_limiter):
        """Test requests over limit are blocked."""
        for _ in range(10):
            rate_limiter.check(key="test_key", limit=10, window_seconds=60)

        with pytest.raises(RateLimitError) as exc_info:
            rate_limiter.check(key="test_key", limit=10, window_seconds=60)

        assert exc_info.value.code == "rate_limited"
        assert exc_info.value.data["count"] > 10

    def test_different_keys_independent(self, rate_limiter):
        """Test different keys have independent limits."""
        for _ in range(10):
            rate_limiter.check(key="key1", limit=10, window_seconds=60)

        # Key2 should still work
        rate_limiter.check(key="key2", limit=10, window_seconds=60)

    def test_window_resets_after_period(self, rate_limiter):
        """Test rate limit resets after window period."""
        # Use a short window for testing
        for _ in range(5):
            rate_limiter.check(key="test_key", limit=5, window_seconds=1)

        # Should be blocked
        with pytest.raises(RateLimitError):
            rate_limiter.check(key="test_key", limit=5, window_seconds=1)

        # Wait for window to reset
        time.sleep(1.1)

        # Should work again
        rate_limiter.check(key="test_key", limit=5, window_seconds=1)

    def test_zero_limit_allows_all(self, rate_limiter):
        """Test zero limit allows all requests."""
        for _ in range(100):
            rate_limiter.check(key="test_key", limit=0, window_seconds=60)
        # Should not raise

    def test_thread_safety(self, rate_limiter):
        """Test rate limiter is thread-safe."""
        errors = []
        successes = [0]

        def make_request():
            try:
                rate_limiter.check(key="concurrent_key", limit=50, window_seconds=60)
                successes[0] += 1
            except RateLimitError:
                errors.append(True)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            for f in futures:
                f.result()

        # Should have exactly 50 successes (limit)
        assert successes[0] <= 50
        # The rest should be errors
        assert len(errors) >= 50


class TestRateLimitError:
    """Test RateLimitError structure."""

    def test_error_contains_details(self, rate_limiter):
        """Test error contains all relevant details."""
        for _ in range(5):
            rate_limiter.check(key="detail_key", limit=5, window_seconds=60)

        with pytest.raises(RateLimitError) as exc_info:
            rate_limiter.check(key="detail_key", limit=5, window_seconds=60)

        error = exc_info.value
        assert error.code == "rate_limited"
        assert "Rate limit exceeded" in error.message
        assert error.data["key"] == "detail_key"
        assert error.data["limit"] == 5
        assert error.data["window_seconds"] == 60
        assert error.data["count"] > 5
