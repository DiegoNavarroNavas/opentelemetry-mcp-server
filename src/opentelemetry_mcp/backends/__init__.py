"""Backend implementations for different OpenTelemetry trace storage systems."""

from opentelemetry_mcp.backends.base import BaseBackend
from opentelemetry_mcp.backends.jaeger import JaegerBackend
from opentelemetry_mcp.backends.langfuse import LangfuseBackend
from opentelemetry_mcp.backends.tempo import TempoBackend
from opentelemetry_mcp.backends.traceloop import TraceloopBackend

__all__ = [
    "BaseBackend",
    "JaegerBackend",
    "LangfuseBackend",
    "TempoBackend",
    "TraceloopBackend",
]
