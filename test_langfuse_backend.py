#!/usr/bin/env python3
"""Test script for Langfuse backend.

This script tests the LangfuseBackend implementation with your credentials
to verify it works correctly before configuring Claude Desktop.
"""

import asyncio
import os
from datetime import datetime, timedelta

from opentelemetry_mcp.backends.langfuse import LangfuseBackend


async def test_langfuse_backend():
    """Test Langfuse backend with real API calls."""

    # Load credentials from environment
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    url = os.getenv("BACKEND_URL", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        print("❌ Error: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set")
        print("\nSet them with:")
        print("export LANGFUSE_PUBLIC_KEY=pk-lf-your-key")
        print("export LANGFUSE_SECRET_KEY=sk-lf-your-key")
        return False

    print(f"🔑 Testing Langfuse backend")
    print(f"   URL: {url}")
    print(f"   Public Key: {public_key[:15]}...")
    print(f"   Secret Key: {secret_key[:15]}...")
    print()

    # Initialize backend
    try:
        backend = LangfuseBackend(
            url=url,
            public_key=public_key,
            secret_key=secret_key,
            timeout=30.0,
        )
        print("✅ Backend initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize backend: {e}")
        return False

    # Test 1: Health check
    print("\n📊 Test 1: Health Check")
    try:
        health = await backend.health_check()
        print(f"   Status: {health.status}")
        print(f"   Backend: {health.backend}")
        print(f"   URL: {health.url}")
        if health.error:
            print(f"   Error: {health.error}")
        if health.status != "healthy":
            print("⚠️  Warning: Backend health check did not return 'healthy'")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

    # Test 2: List services
    print("\n📋 Test 2: List Services")
    try:
        services = await backend.list_services()
        print(f"   Found {len(services)} services:")
        for service in services[:5]:  # Show first 5
            print(f"      - {service}")
        if len(services) > 5:
            print(f"      ... and {len(services) - 5} more")
    except Exception as e:
        print(f"❌ Failed to list services: {e}")
        return False

    # Test 3: Search traces
    print("\n🔍 Test 3: Search Traces (last 24 hours)")
    try:
        from opentelemetry_mcp.models import TraceQuery

        query = TraceQuery(
            start_time=datetime.now() - timedelta(hours=24),
            limit=5,
        )
        traces = await backend.search_traces(query)
        print(f"   Found {len(traces)} traces")
        if traces:
            print(f"   Sample trace:")
            trace = traces[0]
            print(f"      ID: {trace.trace_id}")
            print(f"      Service: {trace.service_name}")
            print(f"      Duration: {trace.duration_ms:.2f}ms")
            print(f"      Status: {trace.status}")
    except Exception as e:
        print(f"❌ Failed to search traces: {e}")
        return False

    # Test 4: Get specific trace (if any exist)
    if traces:
        print("\n📄 Test 4: Get Specific Trace")
        try:
            trace_id = traces[0].trace_id
            full_trace = await backend.get_trace(trace_id)
            print(f"   Trace ID: {full_trace.trace_id}")
            print(f"   Spans: {len(full_trace.spans)}")
            print(f"   Duration: {full_trace.duration_ms:.2f}ms")
            print(f"   Status: {full_trace.status}")

            # Show LLM spans if any
            llm_spans = full_trace.llm_spans
            if llm_spans:
                print(f"   LLM calls: {len(llm_spans)}")
                for span in llm_spans[:3]:
                    print(f"      - {span.operation_name}")
        except Exception as e:
            print(f"❌ Failed to get trace: {e}")
            return False

    # Test 5: Service operations (if services exist)
    if services:
        print("\n🔧 Test 5: Get Service Operations")
        try:
            service_name = services[0]
            operations = await backend.get_service_operations(service_name)
            print(f"   Service: {service_name}")
            print(f"   Operations: {len(operations)}")
            for op in operations[:5]:
                print(f"      - {op}")
        except Exception as e:
            print(f"❌ Failed to get operations: {e}")
            return False

    print("\n✅ All tests passed!")
    print("\n🎉 Your Langfuse backend is working correctly!")
    print("\nNext steps:")
    print("1. Configure Claude Desktop with your credentials")
    print("2. See LANGFUSE_SETUP.md for detailed instructions")
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Langfuse Backend Test")
    print("=" * 60)
    print()

    success = asyncio.run(test_langfuse_backend())

    if not success:
        print("\n❌ Tests failed. Please check the error messages above.")
        exit(1)
    else:
        print("\n✅ All tests passed successfully!")
        exit(0)
