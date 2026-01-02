"""
OpenTelemetry distributed tracing integration.

Provides request tracing across services for debugging and performance analysis.
Configure via environment variables:
- OTEL_ENABLED: "true" to enable (default: false)
- OTEL_SERVICE_NAME: Service name for traces (default: readytrader-crypto)
- OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
"""

from __future__ import annotations

import functools
import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Check if OpenTelemetry is available
OTEL_AVAILABLE = False
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.semconv.resource import ResourceAttributes

    OTEL_AVAILABLE = True
except ImportError:
    pass

# Global tracer instance
_tracer: Optional[Any] = None
_initialized = False


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled."""
    return os.getenv("OTEL_ENABLED", "false").lower() == "true" and OTEL_AVAILABLE


def init_tracing(
    service_name: str = None,
    endpoint: str = None,
    additional_attributes: Dict[str, str] = None,
) -> bool:
    """
    Initialize OpenTelemetry tracing.

    Should be called once at application startup.
    Returns True if tracing was successfully initialized.
    """
    global _tracer, _initialized

    if _initialized:
        return True

    if not is_tracing_enabled():
        logger.info("OpenTelemetry tracing is disabled")
        return False

    if not OTEL_AVAILABLE:
        logger.warning("OpenTelemetry packages not installed")
        return False

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        # Configure service name and attributes
        svc_name = service_name or os.getenv("OTEL_SERVICE_NAME", "readytrader-crypto")
        otlp_endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        # Build resource attributes
        attrs = {
            ResourceAttributes.SERVICE_NAME: svc_name,
            ResourceAttributes.SERVICE_VERSION: "0.2.0",
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "development"),
        }
        if additional_attributes:
            attrs.update(additional_attributes)

        resource = Resource(attributes=attrs)

        # Create and configure tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        span_processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(span_processor)

        # Set as global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer instance
        _tracer = trace.get_tracer(svc_name)
        _initialized = True

        logger.info(f"OpenTelemetry tracing initialized: service={svc_name}, endpoint={otlp_endpoint}")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry tracing: {e}")
        return False


def get_tracer() -> Optional[Any]:
    """Get the global tracer instance."""
    global _tracer

    if not _initialized:
        init_tracing()

    return _tracer


@contextmanager
def trace_span(
    name: str,
    attributes: Dict[str, Any] = None,
    record_exception: bool = True,
):
    """
    Context manager for creating trace spans.

    Usage:
        with trace_span("my_operation", {"user_id": "123"}):
            # ... do work ...

    If tracing is disabled, this is a no-op.
    """
    tracer = get_tracer()

    if tracer is None:
        yield None
        return

    try:
        with tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    if value is not None:
                        span.set_attribute(key, str(value) if not isinstance(value, (bool, int, float)) else value)
            try:
                yield span
            except Exception as e:
                if record_exception:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
    except Exception:
        yield None


def traced(
    name: str = None,
    attributes: Dict[str, Any] = None,
):
    """
    Decorator for tracing function execution.

    Usage:
        @traced("my_function")
        def my_function(arg1, arg2):
            # ... do work ...

        @traced(attributes={"component": "execution"})
        def execute_trade(...):
            # ... do work ...
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span_attrs = dict(attributes or {})
            span_attrs["function.name"] = func.__name__
            span_attrs["function.module"] = func.__module__

            with trace_span(span_name, span_attrs):
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_attrs = dict(attributes or {})
            span_attrs["function.name"] = func.__name__
            span_attrs["function.module"] = func.__module__

            with trace_span(span_name, span_attrs):
                return await func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def add_span_attribute(key: str, value: Any) -> None:
    """Add an attribute to the current span."""
    if not OTEL_AVAILABLE:
        return

    try:
        span = trace.get_current_span()
        if span and span.is_recording():
            if value is not None:
                span.set_attribute(key, str(value) if not isinstance(value, (bool, int, float)) else value)
    except Exception:
        pass


def add_span_event(name: str, attributes: Dict[str, Any] = None) -> None:
    """Add an event to the current span."""
    if not OTEL_AVAILABLE:
        return

    try:
        span = trace.get_current_span()
        if span and span.is_recording():
            event_attrs = {}
            if attributes:
                for k, v in attributes.items():
                    if v is not None:
                        event_attrs[k] = str(v) if not isinstance(v, (bool, int, float)) else v
            span.add_event(name, event_attrs)
    except Exception:
        pass


def set_span_error(error: Exception, message: str = None) -> None:
    """Mark the current span as errored."""
    if not OTEL_AVAILABLE:
        return

    try:
        span = trace.get_current_span()
        if span and span.is_recording():
            span.record_exception(error)
            span.set_status(trace.Status(trace.StatusCode.ERROR, message or str(error)))
    except Exception:
        pass


def get_trace_context() -> Dict[str, str]:
    """
    Get the current trace context for propagation.

    Returns a dict with trace_id and span_id that can be passed
    to other services for distributed tracing.
    """
    if not OTEL_AVAILABLE:
        return {}

    try:
        span = trace.get_current_span()
        if span:
            ctx = span.get_span_context()
            if ctx.is_valid:
                return {
                    "trace_id": format(ctx.trace_id, "032x"),
                    "span_id": format(ctx.span_id, "016x"),
                }
    except Exception:
        pass

    return {}


# FastAPI integration
def setup_fastapi_tracing(app) -> None:
    """
    Set up OpenTelemetry instrumentation for FastAPI.

    Call this after creating your FastAPI app:
        app = FastAPI()
        setup_fastapi_tracing(app)
    """
    if not is_tracing_enabled():
        return

    if not OTEL_AVAILABLE:
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        # Initialize tracing if not already done
        init_tracing()

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI OpenTelemetry instrumentation enabled")

    except ImportError:
        logger.warning("opentelemetry-instrumentation-fastapi not installed")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")


# HTTPX integration for outbound requests
def setup_httpx_tracing() -> None:
    """
    Set up OpenTelemetry instrumentation for HTTPX client.

    Call this at application startup to trace outbound HTTP requests.
    """
    if not is_tracing_enabled():
        return

    if not OTEL_AVAILABLE:
        return

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        init_tracing()
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX OpenTelemetry instrumentation enabled")

    except ImportError:
        logger.warning("opentelemetry-instrumentation-httpx not installed")
    except Exception as e:
        logger.error(f"Failed to instrument HTTPX: {e}")
