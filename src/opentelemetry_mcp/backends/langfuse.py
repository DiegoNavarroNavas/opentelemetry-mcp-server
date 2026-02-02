"""Langfuse backend implementation for querying OpenTelemetry traces.

This backend uses the Langfuse Python SDK to query traces and observations
from Langfuse, transforming them into the OpenTelemetry trace format expected
by the MCP server.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Literal

from langfuse import Langfuse
from opentelemetry_mcp.attributes import HealthCheckResponse, SpanAttributes, SpanEvent
from opentelemetry_mcp.backends.base import BaseBackend
from opentelemetry_mcp.backends.filter_engine import FilterEngine
from opentelemetry_mcp.constants import Fields, GenAI, Service
from opentelemetry_mcp.models import (
    Filter,
    FilterOperator,
    FilterType,
    SpanData,
    SpanQuery,
    TraceData,
    TraceQuery,
)

logger = logging.getLogger(__name__)


class LangfuseBackend(BaseBackend):
    """Langfuse backend implementation.

    Uses the Langfuse Python SDK to query traces and observations,
    transforming them into OpenTelemetry-compatible TraceData format.
    """

    def __init__(
        self,
        url: str,
        public_key: str | None = None,
        secret_key: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize Langfuse backend.

        Args:
            url: Langfuse API URL (e.g., https://cloud.langfuse.com)
            public_key: Langfuse public key (pk-lf-...)
            secret_key: Langfuse secret key (sk-lf-...)
            timeout: Request timeout in seconds
        """
        # Store credentials
        self.public_key = public_key
        self.secret_key = secret_key
        self.timeout = timeout

        if not self.public_key or not self.secret_key:
            raise ValueError("Langfuse backend requires both public_key and secret_key")

        # Initialize BaseBackend without calling super().__init__()
        # to avoid conflicts with Langfuse's client management
        self.url = url.rstrip("/")
        self.api_key = secret_key  # For compatibility with BaseBackend interface
        self._langfuse_client = None  # Will be lazy-loaded

        # Initialize Langfuse client separately
        self._langfuse_client = Langfuse(
            public_key=self.public_key,
            secret_key=self.secret_key,
            host=self.url,
        )

    @property
    def langfuse_client(self) -> Langfuse:
        """Get the Langfuse client instance.

        Returns:
            Langfuse SDK client
        """
        return self._langfuse_client

    def _create_headers(self) -> dict[str, str]:
        """Create headers for Langfuse API requests.

        Langfuse SDK handles authentication internally, so this is not used directly.
        However, we implement it for the BaseBackend interface.

        Returns:
            Dictionary with Basic auth headers (not used by SDK)
        """
        # The Langfuse SDK handles auth internally
        return {
            "Content-Type": "application/json",
        }

    def get_supported_operators(self) -> set[FilterOperator]:
        """Get natively supported operators via Langfuse API.

        Langfuse SDK has limited filtering support, so most filters
        will be applied client-side.

        Returns:
            Set of supported FilterOperator values
        """
        return {
            FilterOperator.EQUALS,
            FilterOperator.NOT_EQUALS,
            FilterOperator.CONTAINS,
        }

    async def search_traces(self, query: TraceQuery) -> list[TraceData]:
        """Search for traces using Langfuse SDK with client-side filtering.

        Args:
            query: Trace query parameters

        Returns:
            List of matching traces

        Raises:
            Exception: If the SDK query fails
        """
        logger.debug(f"Searching traces with query: {query}")

        # Build Langfuse SDK query parameters
        params: dict[str, Any] = {}

        # Map query parameters to Langfuse API parameters
        if query.service_name:
            params["name"] = query.service_name

        if query.operation_name:
            params["session_id"] = query.operation_name

        # Time range filtering - Langfuse expects datetime objects, not strings
        if query.start_time:
            params["from_timestamp"] = query.start_time
        else:
            # Default to last 24 hours
            params["from_timestamp"] = datetime.now() - timedelta(days=1)

        if query.end_time:
            params["to_timestamp"] = query.end_time

        # Set limit (max 100 for Langfuse)
        params["limit"] = min(query.limit, 100)

        # Tag filtering
        if query.tags:
            # Langfuse supports filtering by a single tag
            # We'll use the first tag for server-side filtering
            tags = list(query.tags.keys())
            if tags:
                params["tag"] = tags[0]

        # Query Langfuse for traces
        try:
            response = self._langfuse_client.api.trace.list(**params)
            traces_data = response.data or []
        except Exception as e:
            logger.error(f"Error querying Langfuse: {e}")
            raise

        logger.debug(f"Found {len(traces_data)} traces from Langfuse")

        # Convert to TraceData
        traces = []
        for trace_item in traces_data:
            trace = self._convert_langfuse_trace_to_trace(trace_item)
            if trace:
                traces.append(trace)

        # Apply client-side filters for unsupported operators
        all_filters = query.get_all_filters()
        supported_operators = self.get_supported_operators()
        client_filters = [f for f in all_filters if f.operator not in supported_operators]

        if client_filters:
            logger.info(
                f"Applying {len(client_filters)} filters client-side: "
                f"{[(f.field, f.operator.value) for f in client_filters]}"
            )
            traces = FilterEngine.apply_filters(traces, client_filters)

        return traces

    async def search_spans(self, query: SpanQuery) -> list[SpanData]:
        """Search for individual spans using Langfuse SDK.

        Langfuse calls spans "observations". We query all observations
        and filter them.

        Args:
            query: Span query parameters

        Returns:
            List of matching spans

        Raises:
            Exception: If the SDK query fails
        """
        logger.debug(f"Searching spans with query: {query}")

        # Langfuse doesn't have a dedicated span search API
        # We need to fetch traces and extract spans
        traces = await self.search_traces(
            TraceQuery(
                service_name=query.service_name,
                operation_name=query.operation_name,
                start_time=query.start_time,
                end_time=query.end_time,
                limit=query.limit,
            )
        )

        # Flatten all spans from all traces
        all_spans = []
        for trace in traces:
            all_spans.extend(trace.spans)

        # Apply span-specific filters
        all_filters = query.get_all_filters()
        if all_filters:
            all_spans = FilterEngine.apply_filters(all_spans, all_filters)

        return all_spans

    async def get_trace(self, trace_id: str) -> TraceData:
        """Get a specific trace by ID with all spans.

        Args:
            trace_id: Langfuse trace ID

        Returns:
            Complete trace data with all spans

        Raises:
            Exception: If trace not found or query fails
        """
        logger.debug(f"Fetching trace: {trace_id}")

        try:
            # Fetch trace from Langfuse
            trace_item = self._langfuse_client.api.trace.get(trace_id)

            # Fetch all observations (spans) for this trace
            observations_response = self._langfuse_client.api.observations.get_many(trace_id=trace_id)
            observations = observations_response.data or []

            # Convert to TraceData with full span details
            return self._convert_langfuse_trace_to_trace(trace_item, observations)

        except Exception as e:
            logger.error(f"Error fetching trace {trace_id}: {e}")
            raise

    async def list_services(self) -> list[str]:
        """List all available services.

        In Langfuse, services map to unique trace names.

        Returns:
            List of service names (trace names)
        """
        logger.debug("Listing services (trace names)")

        try:
            # Query recent traces to get unique names
            # Langfuse API limits to 100 per query
            response = self._langfuse_client.api.trace.list(limit=100)
            traces = response.data or []

            # Extract unique trace names
            service_names = set()
            for trace in traces:
                if trace.name:
                    service_names.add(trace.name)

            return sorted(list(service_names))

        except Exception as e:
            logger.error(f"Error listing services: {e}")
            raise

    async def get_service_operations(self, service_name: str) -> list[str]:
        """Get all operations for a specific service.

        In Langfuse, operations map to unique session IDs for traces
        with the given name.

        Args:
            service_name: Service name (trace name in Langfuse)

        Returns:
            List of operation names (session IDs)
        """
        logger.debug(f"Getting operations for service: {service_name}")

        try:
            # Query traces with this name
            # Langfuse API limits to 100 per query
            response = self._langfuse_client.api.trace.list(
                name=service_name,
                limit=100,
            )
            traces = response.data or []

            # Extract unique session IDs
            operations = set()
            for trace in traces:
                if trace.session_id:
                    operations.add(trace.session_id)

            return sorted(list(operations))

        except Exception as e:
            logger.error(f"Error getting operations for {service_name}: {e}")
            raise

    async def health_check(self) -> HealthCheckResponse:
        """Check Langfuse backend health and connectivity.

        Returns:
            Health status information
        """
        try:
            # Try to fetch a single trace to verify connectivity
            # Use a very small limit to minimize data transfer
            response = self._langfuse_client.api.trace.list(limit=1)

            return HealthCheckResponse(
                status="healthy",
                backend="langfuse",
                url=self.url,
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthCheckResponse(
                status="unhealthy",
                backend="langfuse",
                url=self.url,
                error=str(e),
            )

    def _convert_langfuse_trace_to_trace(
        self,
        trace_item: Any,
        observations: list[Any] | None = None,
    ) -> TraceData | None:
        """Convert Langfuse trace to TraceData.

        Args:
            trace_item: Langfuse trace object
            observations: Optional list of observations (spans) for this trace

        Returns:
            TraceData or None if parsing fails
        """
        try:
            # If observations not provided, fetch minimal span info from trace metadata
            if not observations:
                # Create a minimal span from trace metadata
                # This is used for search results where we don't fetch all observations
                spans = [self._create_span_from_trace_metadata(trace_item)]
            else:
                # Convert all observations to spans
                spans = []
                for obs in observations:
                    span = self._convert_langfuse_observation_to_span(
                        trace_item.id,
                        obs,
                    )
                    if span:
                        spans.append(span)

                # Also create a root span from trace metadata if no spans found
                if not spans:
                    spans = [self._create_span_from_trace_metadata(trace_item)]

            # Determine trace status
            status = self._determine_trace_status(trace_item, spans)

            # Create TraceData
            # Handle different attribute names in Langfuse SDK versions
            latency_ms = 0
            if hasattr(trace_item, 'latency_ms'):
                latency_ms = trace_item.latency_ms or 0
            elif hasattr(trace_item, 'latency'):
                latency_ms = (trace_item.latency or 0) * 1000 if trace_item.latency else 0
            elif hasattr(trace_item, 'duration'):
                latency_ms = (trace_item.duration or 0) * 1000 if trace_item.duration else 0

            return TraceData(
                trace_id=trace_item.id,
                spans=spans,
                start_time=self._parse_timestamp(trace_item.timestamp),
                duration_ms=float(latency_ms),
                service_name=trace_item.name or "unknown",
                root_operation=trace_item.session_id or trace_item.name or "unknown",
                status=status,
            )

        except Exception as e:
            logger.error(f"Error converting Langfuse trace to TraceData: {e}")
            return None

    def _create_span_from_trace_metadata(self, trace_item: Any) -> SpanData:
        """Create a SpanData from trace metadata when observations aren't available.

        Args:
            trace_item: Langfuse trace object

        Returns:
            SpanData with trace-level information
        """
        # Extract metadata for attributes
        raw_attrs = {
            Service.NAME: trace_item.name or "",
            "langfuse.trace.id": trace_item.id,
            "langfuse.trace.user_id": trace_item.user_id or "",
            "langfuse.trace.session_id": trace_item.session_id or "",
            "langfuse.trace.version": trace_item.version or "",
        }

        # Add metadata if available
        if trace_item.metadata:
            raw_attrs.update(trace_item.metadata)

        # Add tags if available
        if trace_item.tags:
            for tag in trace_item.tags:
                raw_attrs[f"tag.{tag}"] = "true"

        # Create SpanAttributes
        span_attributes = SpanAttributes(**raw_attrs)

        return SpanData(
            trace_id=trace_item.id,
            span_id=trace_item.id,  # Use trace ID as span ID for root span
            parent_span_id=None,  # Root span has no parent
            operation_name=trace_item.name or "unknown",
            service_name=trace_item.name or "unknown",
            start_time=self._parse_timestamp(trace_item.timestamp),
            duration_ms=float(trace_item.latency_ms or 0),
            status=self._langfuse_level_to_status(trace_item.level),
            attributes=span_attributes,
        )

    def _convert_langfuse_observation_to_span(
        self,
        trace_id: str,
        obs: Any,
    ) -> SpanData | None:
        """Convert Langfuse observation to SpanData.

        Args:
            trace_id: Parent trace ID
            obs: Langfuse observation object

        Returns:
            SpanData or None if parsing fails
        """
        try:
            # Extract metadata for attributes
            raw_attrs = {
                Service.NAME: obs.metadata.get("service.name") if obs.metadata else "",
                "langfuse.observation.id": obs.id,
                "langfuse.observation.type": obs.type,
                "langfuse.observation.name": obs.name,
            }

            # Add metadata if available
            if obs.metadata:
                raw_attrs.update(obs.metadata)

            # Extract LLM-specific attributes if this is an LLM call
            if obs.type == "generation" and obs.usage_details:
                # Map Langfuse usage to gen_ai semantic conventions
                raw_attrs[GenAI.SYSTEM] = obs.model or obs.metadata.get("gen_ai.system", "")
                raw_attrs[GenAI.REQUEST_MODEL] = obs.model
                raw_attrs[GenAI.RESPONSE_MODEL] = obs.model
                raw_attrs["gen_ai.usage.prompt_tokens"] = obs.usage_details.get("prompt_tokens")
                raw_attrs["gen_ai.usage.completion_tokens"] = obs.usage_details.get(
                    "completion_tokens"
                )
                raw_attrs["gen_ai.usage.total_tokens"] = obs.usage_details.get("total_tokens")

            # Create SpanAttributes
            span_attributes = SpanAttributes(**raw_attrs)

            return SpanData(
                trace_id=trace_id,
                span_id=obs.id,
                parent_span_id=obs.parent_observation_id,
                operation_name=obs.name,
                service_name=raw_attrs.get(Service.NAME, ""),
                start_time=self._parse_timestamp(obs.start_time),
                duration_ms=float(obs.latency_ms or 0),
                status=self._langfuse_level_to_status(obs.level),
                attributes=span_attributes,
            )

        except Exception as e:
            logger.error(f"Error converting Langfuse observation to SpanData: {e}")
            return None

    def _determine_trace_status(self, trace_item: Any, spans: list[SpanData]) -> str:
        """Determine overall trace status from trace metadata and spans.

        Args:
            trace_item: Langfuse trace object
            spans: List of spans in the trace

        Returns:
            Status: "OK", "ERROR", or "UNSET"
        """
        # Check trace level
        if trace_item.level == "ERROR":
            return "ERROR"
        elif trace_item.level == "WARNING":
            # Check if any spans have errors
            if any(span.status == "ERROR" for span in spans):
                return "ERROR"
            return "OK"
        elif trace_item.level == "DEFAULT":
            # Check spans for errors
            if any(span.status == "ERROR" for span in spans):
                return "ERROR"
            return "OK"
        else:
            return "UNSET"

    def _langfuse_level_to_status(self, level: str | None) -> str:
        """Convert Langfuse log level to OpenTelemetry status.

        Args:
            level: Langfuse log level (DEFAULT, WARNING, ERROR)

        Returns:
            OpenTelemetry status: OK, ERROR, or UNSET
        """
        if level == "ERROR":
            return "ERROR"
        elif level in ("DEFAULT", "WARNING"):
            return "OK"
        else:
            return "UNSET"

    def _format_timestamp(self, dt: datetime) -> str:
        """Format datetime for Langfuse API.

        Args:
            dt: Datetime to format

        Returns:
            ISO format timestamp string
        """
        return dt.isoformat() + "Z"

    async def close(self) -> None:
        """Close Langfuse client connections.

        Langfuse SDK handles its own connection management, so this is a no-op.
        """
        # Langfuse SDK manages its own connections
        pass

    def _parse_timestamp(self, timestamp: str | datetime | None) -> datetime:
        """Parse timestamp from Langfuse API.

        Args:
            timestamp: ISO format timestamp string or datetime object

        Returns:
            Datetime object
        """
        if not timestamp:
            return datetime.now()

        # If already a datetime object, return it
        if isinstance(timestamp, datetime):
            return timestamp

        # Otherwise parse from string
        try:
            # Langfuse returns timestamps in ISO format
            # Handle both 'Z' and timezone formats
            if isinstance(timestamp, str) and timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            return datetime.fromisoformat(timestamp)
        except Exception as e:
            logger.warning(f"Error parsing timestamp '{timestamp}': {e}")
            return datetime.now()
