# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Tests for P1C observability hooks.

Tests for in-process metrics (Counter, Histogram, Gauge), MetricsRegistry,
and HandlerObservabilityWrapper.
"""

import asyncio
import threading
import uuid

import pytest

from omnimemory.utils.observability import (
    Counter,
    Gauge,
    HandlerMetrics,
    HandlerObservabilityWrapper,
    Histogram,
    MetricsRegistry,
    _get_safe_content_metadata,
)


class TestCounter:
    """Tests for Counter metric."""

    def test_counter_initialization(self) -> None:
        """Test counter initializes with correct name and labels."""
        counter = Counter("test_counter", ["label1", "label2"])
        assert counter.name == "test_counter"
        assert counter.label_names == ["label1", "label2"]

    def test_counter_increment_default(self) -> None:
        """Test counter increments by 1 by default."""
        counter = Counter("test_counter", ["operation"])
        counter.inc(operation="store")
        assert counter.get(operation="store") == 1

    def test_counter_increment_custom_amount(self) -> None:
        """Test counter increments by custom amount."""
        counter = Counter("test_counter", ["operation"])
        counter.inc(5, operation="store")
        assert counter.get(operation="store") == 5

    def test_counter_multiple_labels(self) -> None:
        """Test counter tracks different label combinations separately."""
        counter = Counter("test_counter", ["operation", "status"])
        counter.inc(operation="store", status="success")
        counter.inc(operation="store", status="failure")
        counter.inc(operation="retrieve", status="success")

        assert counter.get(operation="store", status="success") == 1
        assert counter.get(operation="store", status="failure") == 1
        assert counter.get(operation="retrieve", status="success") == 1
        assert counter.get(operation="retrieve", status="failure") == 0

    def test_counter_get_all(self) -> None:
        """Test get_all returns all counter values."""
        counter = Counter("test_counter", ["operation"])
        counter.inc(operation="store")
        counter.inc(operation="retrieve")
        counter.inc(operation="store")

        all_values = counter.get_all()
        assert len(all_values) == 2
        assert all_values[("store",)] == 2
        assert all_values[("retrieve",)] == 1

    def test_counter_labels_from_key(self) -> None:
        """Test converting key tuple back to labels dict."""
        counter = Counter("test_counter", ["operation", "status"])
        key = ("store", "success")
        labels = counter.labels_from_key(key)
        assert labels == {"operation": "store", "status": "success"}

    def test_counter_thread_safety(self) -> None:
        """Test counter is thread-safe."""
        counter = Counter("test_counter", ["operation"])
        num_threads = 10
        increments_per_thread = 100

        def increment_counter() -> None:
            for _ in range(increments_per_thread):
                counter.inc(operation="concurrent")

        threads = [
            threading.Thread(target=increment_counter) for _ in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert (
            counter.get(operation="concurrent") == num_threads * increments_per_thread
        )


class TestHistogram:
    """Tests for Histogram metric."""

    def test_histogram_initialization(self) -> None:
        """Test histogram initializes with correct name and labels."""
        hist = Histogram("test_hist", ["operation"])
        assert hist.name == "test_hist"
        assert hist.label_names == ["operation"]
        assert len(hist.buckets) > 0  # Default buckets

    def test_histogram_custom_buckets(self) -> None:
        """Test histogram with custom buckets."""
        custom_buckets = (1.0, 5.0, 10.0)
        hist = Histogram("test_hist", ["operation"], buckets=custom_buckets)
        assert hist.buckets == custom_buckets

    def test_histogram_observe(self) -> None:
        """Test histogram observation."""
        hist = Histogram("test_hist", ["operation"], buckets=(10.0, 50.0, 100.0))
        hist.observe(25.0, operation="store")
        hist.observe(75.0, operation="store")
        hist.observe(5.0, operation="store")

        snapshot = hist.get(operation="store")
        assert snapshot["count"] == 3
        assert snapshot["sum"] == 105.0
        # Bucket counts: [1 for <=10, 2 for <=50, 3 for <=100, 3 for +Inf]
        assert snapshot["buckets"] == [1, 2, 3, 3]

    def test_histogram_multiple_labels(self) -> None:
        """Test histogram tracks different label combinations separately."""
        hist = Histogram("test_hist", ["operation", "handler"], buckets=(10.0, 50.0))
        hist.observe(25.0, operation="store", handler="fs")
        hist.observe(5.0, operation="retrieve", handler="fs")

        store_snapshot = hist.get(operation="store", handler="fs")
        retrieve_snapshot = hist.get(operation="retrieve", handler="fs")

        assert store_snapshot["count"] == 1
        assert retrieve_snapshot["count"] == 1

    def test_histogram_get_empty(self) -> None:
        """Test get returns empty snapshot for non-existent labels."""
        hist = Histogram("test_hist", ["operation"])
        snapshot = hist.get(operation="nonexistent")
        assert snapshot["count"] == 0
        assert snapshot["sum"] == 0.0

    def test_histogram_get_all(self) -> None:
        """Test get_all returns all histogram values."""
        hist = Histogram("test_hist", ["operation"], buckets=(10.0,))
        hist.observe(5.0, operation="store")
        hist.observe(15.0, operation="retrieve")

        all_values = hist.get_all()
        assert len(all_values) == 2


class TestGauge:
    """Tests for Gauge metric."""

    def test_gauge_initialization(self) -> None:
        """Test gauge initializes with correct name and labels."""
        gauge = Gauge("test_gauge", ["handler"])
        assert gauge.name == "test_gauge"
        assert gauge.label_names == ["handler"]

    def test_gauge_set_and_get(self) -> None:
        """Test gauge set and get operations."""
        gauge = Gauge("test_gauge", ["handler"])
        gauge.set(1.0, handler="filesystem")
        assert gauge.get(handler="filesystem") == 1.0

        gauge.set(0.0, handler="filesystem")
        assert gauge.get(handler="filesystem") == 0.0

    def test_gauge_multiple_labels(self) -> None:
        """Test gauge tracks different handlers separately."""
        gauge = Gauge("test_gauge", ["handler"])
        gauge.set(1.0, handler="filesystem")
        gauge.set(0.0, handler="postgresql")

        assert gauge.get(handler="filesystem") == 1.0
        assert gauge.get(handler="postgresql") == 0.0

    def test_gauge_get_default(self) -> None:
        """Test get returns 0.0 for non-existent labels."""
        gauge = Gauge("test_gauge", ["handler"])
        assert gauge.get(handler="nonexistent") == 0.0

    def test_gauge_get_all(self) -> None:
        """Test get_all returns all gauge values."""
        gauge = Gauge("test_gauge", ["handler"])
        gauge.set(1.0, handler="fs")
        gauge.set(0.5, handler="redis")

        all_values = gauge.get_all()
        assert len(all_values) == 2
        assert all_values[("fs",)] == 1.0
        assert all_values[("redis",)] == 0.5


class TestMetricsRegistry:
    """Tests for MetricsRegistry."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        MetricsRegistry.reset()

    def teardown_method(self) -> None:
        """Reset registry after each test."""
        MetricsRegistry.reset()

    def test_registry_singleton(self) -> None:
        """Test registry is a singleton."""
        registry1 = MetricsRegistry()
        registry2 = MetricsRegistry()
        assert registry1 is registry2

    def test_registry_has_required_metrics(self) -> None:
        """Test registry has all required P1C metrics."""
        registry = MetricsRegistry()

        assert hasattr(registry, "memory_operation_total")
        assert hasattr(registry, "memory_storage_latency_ms")
        assert hasattr(registry, "memory_retrieval_latency_ms")
        assert hasattr(registry, "handler_health_status")

    def test_registry_metrics_work(self) -> None:
        """Test registry metrics can be used."""
        registry = MetricsRegistry()

        registry.memory_operation_total.inc(
            operation="store", status="success", handler="fs"
        )
        assert (
            registry.memory_operation_total.get(
                operation="store", status="success", handler="fs"
            )
            == 1
        )

        registry.memory_storage_latency_ms.observe(
            45.0, operation="store", handler="fs"
        )
        snapshot = registry.memory_storage_latency_ms.get(
            operation="store", handler="fs"
        )
        assert snapshot["count"] == 1

        registry.handler_health_status.set(1.0, handler="fs")
        assert registry.handler_health_status.get(handler="fs") == 1.0

    def test_registry_get_all_metrics(self) -> None:
        """Test get_all_metrics returns all metrics."""
        registry = MetricsRegistry()
        registry.memory_operation_total.inc(
            operation="store", status="success", handler="fs"
        )

        all_metrics = registry.get_all_metrics()

        assert "memory_operation_total" in all_metrics
        assert "memory_storage_latency_ms" in all_metrics
        assert "memory_retrieval_latency_ms" in all_metrics
        assert "handler_health_status" in all_metrics


class TestHandlerObservabilityWrapper:
    """Tests for HandlerObservabilityWrapper."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        MetricsRegistry.reset()

    def teardown_method(self) -> None:
        """Reset registry after each test."""
        MetricsRegistry.reset()

    @pytest.mark.asyncio
    async def test_wrapper_successful_operation(self) -> None:
        """Test wrapper records metrics for successful operation."""
        wrapper = HandlerObservabilityWrapper(handler_name="test_handler")

        async with wrapper.observe_operation(
            operation="store",
            correlation_id="test-correlation-id",
        ) as ctx:
            assert ctx["operation"] == "store"
            assert ctx["handler"] == "test_handler"
            assert ctx["correlation_id"] == "test-correlation-id"
            await asyncio.sleep(0.01)  # Simulate some work

        # Check counter was incremented
        registry = MetricsRegistry()
        count = registry.memory_operation_total.get(
            operation="store", status="success", handler="test_handler"
        )
        assert count == 1

        # Check histogram was recorded
        snapshot = registry.memory_storage_latency_ms.get(
            operation="store", handler="test_handler"
        )
        assert snapshot["count"] == 1
        assert snapshot["sum"] >= 10.0  # At least 10ms

        # Check health gauge is set to healthy
        health = registry.handler_health_status.get(handler="test_handler")
        assert health == 1.0

    @pytest.mark.asyncio
    async def test_wrapper_failed_operation(self) -> None:
        """Test wrapper records metrics for failed operation."""
        wrapper = HandlerObservabilityWrapper(handler_name="test_handler")

        with pytest.raises(ValueError):
            async with wrapper.observe_operation(
                operation="store",
                correlation_id="test-correlation-id",
            ):
                raise ValueError("Test error")

        # Check counter was incremented with failure status
        registry = MetricsRegistry()
        count = registry.memory_operation_total.get(
            operation="store", status="failure", handler="test_handler"
        )
        assert count == 1

        # Check health gauge is set to unhealthy
        health = registry.handler_health_status.get(handler="test_handler")
        assert health == 0.0

    @pytest.mark.asyncio
    async def test_wrapper_generates_correlation_id(self) -> None:
        """Test wrapper generates correlation ID if not provided."""
        wrapper = HandlerObservabilityWrapper(handler_name="test_handler")

        async with wrapper.observe_operation(operation="store") as ctx:
            assert ctx["correlation_id"] is not None
            # Should be a valid UUID
            uuid.UUID(ctx["correlation_id"])

    @pytest.mark.asyncio
    async def test_wrapper_retrieval_uses_correct_histogram(self) -> None:
        """Test retrieval operations use retrieval histogram."""
        wrapper = HandlerObservabilityWrapper(handler_name="test_handler")

        async with wrapper.observe_operation(operation="retrieve"):
            await asyncio.sleep(0.01)

        registry = MetricsRegistry()

        # Should NOT be in storage histogram
        storage_snapshot = registry.memory_storage_latency_ms.get(
            operation="retrieve", handler="test_handler"
        )
        assert storage_snapshot["count"] == 0

        # Should be in retrieval histogram
        retrieval_snapshot = registry.memory_retrieval_latency_ms.get(
            operation="retrieve", handler="test_handler"
        )
        assert retrieval_snapshot["count"] == 1

    @pytest.mark.asyncio
    async def test_wrapper_mark_healthy_unhealthy(self) -> None:
        """Test manual health status changes."""
        wrapper = HandlerObservabilityWrapper(handler_name="test_handler")

        # Initial state is healthy
        registry = MetricsRegistry()
        assert registry.handler_health_status.get(handler="test_handler") == 1.0

        wrapper.mark_unhealthy()
        assert registry.handler_health_status.get(handler="test_handler") == 0.0

        wrapper.mark_healthy()
        assert registry.handler_health_status.get(handler="test_handler") == 1.0

    @pytest.mark.asyncio
    async def test_wrapper_get_handler_stats(self) -> None:
        """Test get_handler_stats returns correct statistics."""
        wrapper = HandlerObservabilityWrapper(handler_name="test_handler")

        async with wrapper.observe_operation(operation="store"):
            pass

        async with wrapper.observe_operation(operation="retrieve"):
            pass

        stats = wrapper.get_handler_stats()

        assert stats["handler"] == "test_handler"
        assert stats["health_status"] == 1.0
        assert "operation_counts" in stats
        assert "storage_latency" in stats
        assert "retrieval_latency" in stats

    @pytest.mark.asyncio
    async def test_wrapper_invalid_correlation_id_replaced(self) -> None:
        """Test invalid correlation ID is replaced with valid UUID."""
        wrapper = HandlerObservabilityWrapper(handler_name="test_handler")

        # Invalid correlation ID with special characters
        async with wrapper.observe_operation(
            operation="store",
            correlation_id="invalid<script>id",
        ) as ctx:
            # Should be replaced with a valid UUID
            assert ctx["correlation_id"] != "invalid<script>id"
            uuid.UUID(ctx["correlation_id"])  # Should not raise


class TestSafeContentMetadata:
    """Tests for _get_safe_content_metadata helper."""

    def test_none_content(self) -> None:
        """Test handling of None content."""
        result = _get_safe_content_metadata(None)
        assert result["content_exists"] is False
        assert result["content_len"] == 0

    def test_valid_content(self) -> None:
        """Test extraction of safe metadata from content."""
        content = "This is test content with potentially sensitive data"
        result = _get_safe_content_metadata(content)

        assert result["content_exists"] is True
        assert result["content_len"] == len(content)
        assert "content_hash" in result
        assert len(result["content_hash"]) == 8  # First 8 chars of SHA-256

    def test_custom_field_name(self) -> None:
        """Test custom field name prefix."""
        result = _get_safe_content_metadata("test", field_name="body")
        assert "body_exists" in result
        assert "body_len" in result
        assert "body_hash" in result

    def test_deterministic_hash(self) -> None:
        """Test hash is deterministic for same content."""
        content = "same content"
        result1 = _get_safe_content_metadata(content)
        result2 = _get_safe_content_metadata(content)
        assert result1["content_hash"] == result2["content_hash"]

    def test_different_hash_for_different_content(self) -> None:
        """Test different content produces different hash."""
        result1 = _get_safe_content_metadata("content A")
        result2 = _get_safe_content_metadata("content B")
        assert result1["content_hash"] != result2["content_hash"]


class TestHandlerMetricsDataclass:
    """Tests for HandlerMetrics dataclass."""

    def test_handler_metrics_creation(self) -> None:
        """Test HandlerMetrics can be created with required fields."""
        metrics = HandlerMetrics(
            correlation_id="test-id",
            operation="store",
            handler="filesystem",
            status="success",
            latency_ms=45.5,
        )

        assert metrics.correlation_id == "test-id"
        assert metrics.operation == "store"
        assert metrics.handler == "filesystem"
        assert metrics.status == "success"
        assert metrics.latency_ms == 45.5
        assert metrics.error_type is None
        assert metrics.error_message is None

    def test_handler_metrics_with_error(self) -> None:
        """Test HandlerMetrics with error information."""
        metrics = HandlerMetrics(
            correlation_id="test-id",
            operation="store",
            handler="filesystem",
            status="failure",
            latency_ms=12.3,
            error_type="ValueError",
            error_message="Invalid input",
        )

        assert metrics.status == "failure"
        assert metrics.error_type == "ValueError"
        assert metrics.error_message == "Invalid input"
