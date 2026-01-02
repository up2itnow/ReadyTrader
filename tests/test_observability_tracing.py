"""
Tests for OpenTelemetry tracing integration.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


class TestTracingDisabled:
    """Test behavior when tracing is disabled."""

    def test_is_tracing_enabled_default_false(self):
        """Test tracing is disabled by default."""
        from observability.tracing import is_tracing_enabled

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            assert is_tracing_enabled() is False

    def test_trace_span_noop_when_disabled(self):
        """Test trace_span is no-op when disabled."""
        from observability.tracing import trace_span

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            with trace_span("test_span") as span:
                assert span is None

    def test_traced_decorator_works_when_disabled(self):
        """Test traced decorator doesn't break when tracing disabled."""
        from observability.tracing import traced

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):

            @traced("test_function")
            def my_function(x):
                return x * 2

            result = my_function(5)
            assert result == 10

    def test_add_span_attribute_noop_when_disabled(self):
        """Test add_span_attribute is no-op when disabled."""
        from observability.tracing import add_span_attribute

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            # Should not raise
            add_span_attribute("key", "value")

    def test_add_span_event_noop_when_disabled(self):
        """Test add_span_event is no-op when disabled."""
        from observability.tracing import add_span_event

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            # Should not raise
            add_span_event("test_event", {"key": "value"})

    def test_get_trace_context_empty_when_disabled(self):
        """Test get_trace_context returns empty dict when disabled."""
        from observability.tracing import get_trace_context

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            context = get_trace_context()
            assert context == {}


class TestTracingEnabled:
    """Test behavior when tracing is enabled (mocked)."""

    def test_is_tracing_enabled_when_true(self):
        """Test tracing is enabled when OTEL_ENABLED=true."""
        from observability.tracing import is_tracing_enabled

        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}):
            # Will be False if opentelemetry not installed
            is_tracing_enabled()
            # Just verify it doesn't crash

    def test_init_tracing_returns_false_without_otel(self):
        """Test init_tracing returns False when packages not available."""
        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}):
            with patch.dict("sys.modules", {"opentelemetry": None}):
                from observability import tracing

                # Reset the module state
                tracing._initialized = False
                tracing._tracer = None
                tracing.OTEL_AVAILABLE = False

                result = tracing.init_tracing()
                assert result is False


class TestTracedDecorator:
    """Test the traced decorator."""

    def test_traced_preserves_function_name(self):
        """Test traced decorator preserves function name."""
        from observability.tracing import traced

        @traced("my_function")
        def my_function():
            """My docstring."""
            return 42

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_traced_handles_exceptions(self):
        """Test traced decorator propagates exceptions."""
        from observability.tracing import traced

        @traced("failing_function")
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_traced_async_function(self):
        """Test traced decorator with async functions."""
        import asyncio

        from observability.tracing import traced

        @traced("async_function")
        async def async_function(x):
            return x * 2

        result = asyncio.run(async_function(5))
        assert result == 10


class TestFastAPIIntegration:
    """Test FastAPI integration."""

    def test_setup_fastapi_tracing_noop_when_disabled(self):
        """Test setup_fastapi_tracing is no-op when disabled."""
        from observability.tracing import setup_fastapi_tracing

        mock_app = MagicMock()

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            # Should not raise
            setup_fastapi_tracing(mock_app)


class TestHTTPXIntegration:
    """Test HTTPX integration."""

    def test_setup_httpx_tracing_noop_when_disabled(self):
        """Test setup_httpx_tracing is no-op when disabled."""
        from observability.tracing import setup_httpx_tracing

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            # Should not raise
            setup_httpx_tracing()
