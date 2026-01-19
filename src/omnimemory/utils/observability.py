"""
Observability utilities for OmniMemory ONEX architecture.

This module provides:
- ContextVar integration for correlation ID tracking
- Distributed tracing support
- Enhanced logging with correlation context
- Performance monitoring and metrics collection
- In-process metrics: Counter, Histogram, Gauge
- Handler observability wrapper for "one wrapper, one log line, no payload" pattern

Structured Log Schema (for downstream ingestion - ELK, Datadog, etc.):
------------------------------------------------------------------------
All handler operation log events follow this consistent schema:

Required fields:
    - correlation_id (str): Unique request correlation identifier
    - operation (str): Operation name (e.g., "store", "retrieve", "delete")
    - handler (str): Handler name (e.g., "filesystem", "postgresql")
    - status (str): Operation status, one of "success" or "failure"
    - latency_ms (float): Operation latency in milliseconds
    - timestamp (str): ISO8601 timestamp when the event was logged

Optional fields (only present on failure):
    - error_type (str): Exception class name (e.g., "ValueError", "IOError")
    - error_message (str): Sanitized error message (PII-safe)

Example log event (success):
    {
        "correlation_id": "abc123-def456",
        "operation": "store",
        "handler": "filesystem",
        "status": "success",
        "latency_ms": 45.23,
        "timestamp": "2025-01-19T12:34:56.789Z"
    }

Example log event (failure):
    {
        "correlation_id": "abc123-def456",
        "operation": "store",
        "handler": "filesystem",
        "status": "failure",
        "latency_ms": 102.5,
        "timestamp": "2025-01-19T12:34:56.789Z",
        "error_type": "IOError",
        "error_message": "Permission denied"
    }
"""

from __future__ import annotations

import functools
import re
import threading
import time
import uuid
from collections import OrderedDict, defaultdict
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

# Type variable for generic function types
F = TypeVar("F", bound=Callable[..., object])

# Type alias for metadata values - supports common serializable types
# This replaces Any with explicit types for type safety
MetadataValue = Union[str, int, float, bool, None]

import structlog
from pydantic import BaseModel, Field

from ..models.foundation.model_typed_collections import ModelMetadata

# Optional psutil import for memory tracking - gracefully degrade if unavailable
_PSUTIL_AVAILABLE = False
try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore[assignment]
from .error_sanitizer import SanitizationLevel
from .error_sanitizer import sanitize_error as _base_sanitize_error

# === SECURITY VALIDATION FUNCTIONS ===


def validate_correlation_id(correlation_id: str) -> bool:
    """
    Validate correlation ID format to prevent injection attacks.

    Args:
        correlation_id: Correlation ID to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not correlation_id or not isinstance(correlation_id, str):
        return False

    # Allow UUIDs (with or without hyphens) and alphanumeric strings up to 64 chars
    # This prevents injection while allowing reasonable correlation ID formats
    pattern = r"^[a-zA-Z0-9\-_]{1,64}$"
    return re.match(pattern, correlation_id) is not None


def sanitize_metadata_value(value: object) -> MetadataValue:
    """
    Sanitize metadata values to prevent injection attacks.

    Converts arbitrary objects to safe serializable types (str, int, float, bool, None).

    Args:
        value: Value to sanitize (accepts any object for flexibility)

    Returns:
        Sanitized value as one of the safe MetadataValue types
    """
    if isinstance(value, str):
        # Remove potential injection patterns and limit length
        sanitized = re.sub(r'[<>"\'\\\n\r\t]', "", value)
        return sanitized[:1000]  # Limit string length
    elif isinstance(value, bool):
        # Check bool before int since bool is a subclass of int
        return value
    elif isinstance(value, int):
        return value
    elif isinstance(value, float):
        return value
    elif value is None:
        return None
    else:
        # Convert to string and sanitize
        return sanitize_metadata_value(str(value))


def _sanitize_error(error: Exception) -> str:
    """
    Sanitize error messages to prevent information disclosure in logs.

    Uses the centralized error sanitizer for consistent security handling.

    Args:
        error: Exception to sanitize

    Returns:
        Safe error message without sensitive information
    """
    return _base_sanitize_error(
        error, context="observability", level=SanitizationLevel.STANDARD
    )


# Context variables for correlation tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
operation_var: ContextVar[Optional[str]] = ContextVar("operation", default=None)

logger = structlog.get_logger(__name__)


# === IN-PROCESS METRICS ===
# Minimal implementation for P1C observability - no external dependencies


# Default histogram buckets for latency measurements (in milliseconds)
DEFAULT_LATENCY_BUCKETS: Tuple[float, ...] = (
    1.0,
    5.0,
    10.0,
    25.0,
    50.0,
    100.0,
    250.0,
    500.0,
    1000.0,
    2500.0,
    5000.0,
    10000.0,
)

# Default maximum number of unique label combinations per metric
# This prevents unbounded memory growth from high-cardinality labels
DEFAULT_MAX_METRIC_ENTRIES: int = 10000


@dataclass
class CounterValue:
    """Thread-safe counter value with labels."""

    value: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, amount: int = 1) -> None:
        """Increment the counter."""
        with self._lock:
            self.value += amount

    def get(self) -> int:
        """Get current counter value."""
        with self._lock:
            return self.value


class Counter:
    """In-process counter metric for tracking totals.

    Thread-safe counter that tracks total operations by labels.
    Uses bounded storage with LRU eviction to prevent unbounded memory growth.

    Example:
        counter = Counter("memory_operation_total", ["operation", "status", "handler"])
        counter.inc(operation="store", status="success", handler="filesystem")

        # With strict label validation:
        counter = Counter("ops", ["operation", "status"], strict_labels=True)
        counter.inc(operation="store", status="ok")  # OK
        counter.inc(operation="store")  # Raises ValueError (missing "status")
        counter.inc(operation="store", status="ok", extra="bad")  # Raises ValueError
    """

    def __init__(
        self,
        name: str,
        label_names: List[str],
        max_entries: int = DEFAULT_MAX_METRIC_ENTRIES,
        strict_labels: bool = False,
    ) -> None:
        """Initialize counter with name and label names.

        Args:
            name: Metric name (e.g., "memory_operation_total")
            label_names: List of label names (e.g., ["operation", "status", "handler"])
            max_entries: Maximum number of unique label combinations (default 10000).
                         Oldest entries are evicted when limit is exceeded.
            strict_labels: If True, validate that all required labels are provided
                          and no extra labels are passed. Raises ValueError on mismatch.
                          Default is False for backwards compatibility.
        """
        self.name = name
        self.label_names = label_names
        self.max_entries = max_entries
        self.strict_labels = strict_labels
        self._label_names_set = frozenset(label_names)
        # Use OrderedDict for LRU eviction (oldest entries evicted first)
        self._values: "OrderedDict[Tuple[str, ...], CounterValue]" = OrderedDict()
        self._lock = threading.Lock()

    def _validate_labels(self, labels: Dict[str, str]) -> None:
        """Validate labels against expected label names.

        Args:
            labels: Label key-value pairs to validate

        Raises:
            ValueError: If strict_labels is True and labels don't match expected names
        """
        if not self.strict_labels:
            return

        provided = set(labels.keys())
        expected = self._label_names_set

        missing = expected - provided
        extra = provided - expected

        errors = []
        if missing:
            errors.append(f"missing labels: {sorted(missing)}")
        if extra:
            errors.append(f"extra labels: {sorted(extra)}")

        if errors:
            raise ValueError(
                f"Label validation failed for metric '{self.name}': {'; '.join(errors)}. "
                f"Expected labels: {sorted(expected)}, got: {sorted(provided)}"
            )

    def inc(self, amount: int = 1, **labels: str) -> None:
        """Increment the counter with given labels.

        Args:
            amount: Amount to increment by (default 1)
            **labels: Label key-value pairs

        Raises:
            ValueError: If strict_labels is True and labels don't match expected names
        """
        self._validate_labels(labels)
        key = self._labels_to_key(labels)
        with self._lock:
            if key not in self._values:
                # Evict oldest entries if at capacity
                while len(self._values) >= self.max_entries:
                    self._values.popitem(last=False)  # Remove oldest (FIFO)
                self._values[key] = CounterValue()
            else:
                # Move to end to mark as recently used
                self._values.move_to_end(key)
        self._values[key].inc(amount)

    def get(self, **labels: str) -> int:
        """Get counter value for given labels."""
        key = self._labels_to_key(labels)
        with self._lock:
            if key not in self._values:
                return 0
            # Move to end to mark as recently used
            self._values.move_to_end(key)
            return self._values[key].get()

    def get_all(self) -> Dict[Tuple[str, ...], int]:
        """Get all counter values with their labels."""
        with self._lock:
            return {k: v.get() for k, v in self._values.items()}

    def _labels_to_key(self, labels: Dict[str, str]) -> Tuple[str, ...]:
        """Convert labels dict to hashable key tuple."""
        return tuple(labels.get(name, "") for name in self.label_names)

    def labels_from_key(self, key: Tuple[str, ...]) -> Dict[str, str]:
        """Convert key tuple back to labels dict."""
        return dict(zip(self.label_names, key))


@dataclass
class HistogramValue:
    """Thread-safe histogram value with buckets."""

    buckets: Tuple[float, ...]
    bucket_counts: List[int] = field(default_factory=list)
    sum_value: float = 0.0
    count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        """Initialize bucket counts."""
        if not self.bucket_counts:
            self.bucket_counts = [0] * (len(self.buckets) + 1)  # +1 for +Inf

    def observe(self, value: float) -> None:
        """Record an observation."""
        with self._lock:
            self.sum_value += value
            self.count += 1
            for i, bucket in enumerate(self.buckets):
                if value <= bucket:
                    self.bucket_counts[i] += 1
            # Always increment +Inf bucket
            self.bucket_counts[-1] += 1

    def get_snapshot(self) -> Dict[str, Union[float, int, List[int]]]:
        """Get a snapshot of histogram values."""
        with self._lock:
            return {
                "sum": self.sum_value,
                "count": self.count,
                "buckets": list(self.bucket_counts),
                "bucket_bounds": list(self.buckets) + [float("inf")],
            }


class Histogram:
    """In-process histogram metric for tracking distributions.

    Thread-safe histogram that tracks value distributions with configurable buckets.
    Uses bounded storage with LRU eviction to prevent unbounded memory growth.

    Example:
        hist = Histogram("memory_storage_latency_ms", ["operation", "handler"])
        hist.observe(45.2, operation="store", handler="filesystem")

        # With strict label validation:
        hist = Histogram("latency", ["operation", "handler"], strict_labels=True)
        hist.observe(45.2, operation="store", handler="fs")  # OK
        hist.observe(45.2, operation="store")  # Raises ValueError (missing "handler")
    """

    def __init__(
        self,
        name: str,
        label_names: List[str],
        buckets: Tuple[float, ...] = DEFAULT_LATENCY_BUCKETS,
        max_entries: int = DEFAULT_MAX_METRIC_ENTRIES,
        strict_labels: bool = False,
    ) -> None:
        """Initialize histogram with name, labels, and buckets.

        Args:
            name: Metric name (e.g., "memory_storage_latency_ms")
            label_names: List of label names
            buckets: Tuple of bucket boundaries (default: latency buckets)
            max_entries: Maximum number of unique label combinations (default 10000).
                         Oldest entries are evicted when limit is exceeded.
            strict_labels: If True, validate that all required labels are provided
                          and no extra labels are passed. Raises ValueError on mismatch.
                          Default is False for backwards compatibility.

        Raises:
            ValueError: If buckets tuple is empty, contains non-positive values,
                       or is not in strictly ascending order.
        """
        # Validate buckets
        if not buckets:
            raise ValueError("Histogram buckets tuple must not be empty")

        for i, bucket in enumerate(buckets):
            if bucket <= 0:
                raise ValueError(
                    f"Histogram bucket values must be positive (> 0), "
                    f"got {bucket} at index {i}"
                )

        for i in range(1, len(buckets)):
            if buckets[i] <= buckets[i - 1]:
                raise ValueError(
                    f"Histogram buckets must be in strictly ascending order, "
                    f"but bucket[{i}]={buckets[i]} <= bucket[{i-1}]={buckets[i-1]}"
                )

        self.name = name
        self.label_names = label_names
        self.buckets = buckets
        self.max_entries = max_entries
        self.strict_labels = strict_labels
        self._label_names_set = frozenset(label_names)
        # Use OrderedDict for LRU eviction (oldest entries evicted first)
        self._values: "OrderedDict[Tuple[str, ...], HistogramValue]" = OrderedDict()
        self._lock = threading.Lock()

    def _validate_labels(self, labels: Dict[str, str]) -> None:
        """Validate labels against expected label names.

        Args:
            labels: Label key-value pairs to validate

        Raises:
            ValueError: If strict_labels is True and labels don't match expected names
        """
        if not self.strict_labels:
            return

        provided = set(labels.keys())
        expected = self._label_names_set

        missing = expected - provided
        extra = provided - expected

        errors = []
        if missing:
            errors.append(f"missing labels: {sorted(missing)}")
        if extra:
            errors.append(f"extra labels: {sorted(extra)}")

        if errors:
            raise ValueError(
                f"Label validation failed for metric '{self.name}': {'; '.join(errors)}. "
                f"Expected labels: {sorted(expected)}, got: {sorted(provided)}"
            )

    def observe(self, value: float, **labels: str) -> None:
        """Record an observation with given labels.

        Args:
            value: Value to observe
            **labels: Label key-value pairs

        Raises:
            ValueError: If strict_labels is True and labels don't match expected names
        """
        self._validate_labels(labels)
        key = self._labels_to_key(labels)
        with self._lock:
            if key not in self._values:
                # Evict oldest entries if at capacity
                while len(self._values) >= self.max_entries:
                    self._values.popitem(last=False)  # Remove oldest (FIFO)
                self._values[key] = HistogramValue(buckets=self.buckets)
            else:
                # Move to end to mark as recently used
                self._values.move_to_end(key)
        self._values[key].observe(value)

    def get(self, **labels: str) -> Dict[str, Union[float, int, List[int]]]:
        """Get histogram snapshot for given labels."""
        key = self._labels_to_key(labels)
        with self._lock:
            if key not in self._values:
                return {"sum": 0.0, "count": 0, "buckets": [], "bucket_bounds": []}
            # Move to end to mark as recently used
            self._values.move_to_end(key)
            return self._values[key].get_snapshot()

    def get_all(self) -> Dict[Tuple[str, ...], Dict[str, Union[float, int, List[int]]]]:
        """Get all histogram values with their labels."""
        with self._lock:
            return {k: v.get_snapshot() for k, v in self._values.items()}

    def _labels_to_key(self, labels: Dict[str, str]) -> Tuple[str, ...]:
        """Convert labels dict to hashable key tuple."""
        return tuple(labels.get(name, "") for name in self.label_names)

    def labels_from_key(self, key: Tuple[str, ...]) -> Dict[str, str]:
        """Convert key tuple back to labels dict."""
        return dict(zip(self.label_names, key))


@dataclass
class GaugeValue:
    """Thread-safe gauge value."""

    value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def set(self, value: float) -> None:
        """Set the gauge value."""
        with self._lock:
            self.value = value

    def get(self) -> float:
        """Get current gauge value."""
        with self._lock:
            return self.value


class Gauge:
    """In-process gauge metric for tracking current values.

    Thread-safe gauge that tracks current state values.
    Uses bounded storage with LRU eviction to prevent unbounded memory growth.

    Example:
        gauge = Gauge("handler_health_status", ["handler"])
        gauge.set(1.0, handler="filesystem")  # healthy
        gauge.set(0.0, handler="filesystem")  # unhealthy

        # With strict label validation:
        gauge = Gauge("health", ["handler", "region"], strict_labels=True)
        gauge.set(1.0, handler="fs", region="us-east")  # OK
        gauge.set(1.0, handler="fs")  # Raises ValueError (missing "region")
    """

    def __init__(
        self,
        name: str,
        label_names: List[str],
        max_entries: int = DEFAULT_MAX_METRIC_ENTRIES,
        strict_labels: bool = False,
    ) -> None:
        """Initialize gauge with name and label names.

        Args:
            name: Metric name (e.g., "handler_health_status")
            label_names: List of label names
            max_entries: Maximum number of unique label combinations (default 10000).
                         Oldest entries are evicted when limit is exceeded.
            strict_labels: If True, validate that all required labels are provided
                          and no extra labels are passed. Raises ValueError on mismatch.
                          Default is False for backwards compatibility.
        """
        self.name = name
        self.label_names = label_names
        self.max_entries = max_entries
        self.strict_labels = strict_labels
        self._label_names_set = frozenset(label_names)
        # Use OrderedDict for LRU eviction (oldest entries evicted first)
        self._values: "OrderedDict[Tuple[str, ...], GaugeValue]" = OrderedDict()
        self._lock = threading.Lock()

    def _validate_labels(self, labels: Dict[str, str]) -> None:
        """Validate labels against expected label names.

        Args:
            labels: Label key-value pairs to validate

        Raises:
            ValueError: If strict_labels is True and labels don't match expected names
        """
        if not self.strict_labels:
            return

        provided = set(labels.keys())
        expected = self._label_names_set

        missing = expected - provided
        extra = provided - expected

        errors = []
        if missing:
            errors.append(f"missing labels: {sorted(missing)}")
        if extra:
            errors.append(f"extra labels: {sorted(extra)}")

        if errors:
            raise ValueError(
                f"Label validation failed for metric '{self.name}': {'; '.join(errors)}. "
                f"Expected labels: {sorted(expected)}, got: {sorted(provided)}"
            )

    def set(self, value: float, **labels: str) -> None:
        """Set the gauge value with given labels.

        Args:
            value: Value to set
            **labels: Label key-value pairs

        Raises:
            ValueError: If strict_labels is True and labels don't match expected names
        """
        self._validate_labels(labels)
        key = self._labels_to_key(labels)
        with self._lock:
            if key not in self._values:
                # Evict oldest entries if at capacity
                while len(self._values) >= self.max_entries:
                    self._values.popitem(last=False)  # Remove oldest (FIFO)
                self._values[key] = GaugeValue()
            else:
                # Move to end to mark as recently used
                self._values.move_to_end(key)
        self._values[key].set(value)

    def get(self, **labels: str) -> float:
        """Get gauge value for given labels."""
        key = self._labels_to_key(labels)
        with self._lock:
            if key not in self._values:
                return 0.0
            # Move to end to mark as recently used
            self._values.move_to_end(key)
            return self._values[key].get()

    def get_all(self) -> Dict[Tuple[str, ...], float]:
        """Get all gauge values with their labels."""
        with self._lock:
            return {k: v.get() for k, v in self._values.items()}

    def _labels_to_key(self, labels: Dict[str, str]) -> Tuple[str, ...]:
        """Convert labels dict to hashable key tuple."""
        return tuple(labels.get(name, "") for name in self.label_names)

    def labels_from_key(self, key: Tuple[str, ...]) -> Dict[str, str]:
        """Convert key tuple back to labels dict."""
        return dict(zip(self.label_names, key))


class MetricsRegistry:
    """Registry for in-process metrics.

    Provides a central place to access all metrics for the OmniMemory system.
    This is a singleton-like registry that holds all metrics instances.

    Thread-safety: Uses double-checked locking pattern to ensure safe initialization
    across multiple threads. The _initialized flag is checked inside the lock to
    prevent race conditions during first access.

    Example:
        registry = MetricsRegistry()
        registry.memory_operation_total.inc(operation="store", status="success")
        registry.memory_storage_latency_ms.observe(45.2, operation="store")
    """

    _instance: Optional["MetricsRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MetricsRegistry":
        """Singleton pattern for metrics registry with double-checked locking.

        Thread-safety is achieved by:
        1. Quick check outside lock (fast path for already-initialized case)
        2. Lock acquisition for creation
        3. Re-check inside lock (handles race between check and lock acquisition)
        4. Full initialization inside lock (prevents concurrent initialization)
        """
        # Fast path: instance already exists and is initialized
        if cls._instance is not None and getattr(cls._instance, "_initialized", False):
            return cls._instance

        # Slow path: need to create or initialize
        with cls._lock:
            # Double-check after acquiring lock
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False

            # Initialize inside the lock to prevent concurrent initialization
            if not cls._instance._initialized:
                cls._instance._do_initialize()

            return cls._instance

    def __init__(self) -> None:
        """No-op init - all initialization done in __new__ under lock."""
        # Initialization is done in __new__ to ensure thread safety
        pass

    def _do_initialize(self) -> None:
        """Perform actual initialization (called under lock from __new__).

        This method is only called once, under the class lock, ensuring
        thread-safe initialization of all metrics.
        """
        # Counter: Total operations by type and status
        self.memory_operation_total = Counter(
            name="memory_operation_total",
            label_names=["operation", "status", "handler"],
        )

        # Histogram: Storage operation latency
        self.memory_storage_latency_ms = Histogram(
            name="memory_storage_latency_ms",
            label_names=["operation", "handler"],
        )

        # Histogram: Retrieval operation latency
        self.memory_retrieval_latency_ms = Histogram(
            name="memory_retrieval_latency_ms",
            label_names=["operation", "handler"],
        )

        # Gauge: Handler health status (1=healthy, 0=unhealthy)
        self.handler_health_status = Gauge(
            name="handler_health_status",
            label_names=["handler"],
        )

        # Mark as initialized AFTER all metrics are created
        self._initialized = True

    def get_all_metrics(self) -> Dict[str, Dict[str, object]]:
        """Get snapshot of all metrics for reporting."""
        return {
            "memory_operation_total": {
                "type": "counter",
                "values": {
                    str(k): v for k, v in self.memory_operation_total.get_all().items()
                },
            },
            "memory_storage_latency_ms": {
                "type": "histogram",
                "values": {
                    str(k): v
                    for k, v in self.memory_storage_latency_ms.get_all().items()
                },
            },
            "memory_retrieval_latency_ms": {
                "type": "histogram",
                "values": {
                    str(k): v
                    for k, v in self.memory_retrieval_latency_ms.get_all().items()
                },
            },
            "handler_health_status": {
                "type": "gauge",
                "values": {
                    str(k): v for k, v in self.handler_health_status.get_all().items()
                },
            },
        }

    @classmethod
    def reset(cls) -> None:
        """Reset the registry by clearing all metrics data (primarily for testing).

        WARNING: This method should only be used in tests. Using it in production
        code may lead to inconsistent state if other code holds references to
        metric objects.

        This method clears all data from the existing instance rather than
        setting _instance to None, which prevents inconsistent state when
        other code holds references to the old instance.
        """
        # Warn if called outside tests (check for common test indicators)
        import sys
        import warnings

        in_test = any(
            "pytest" in module or "unittest" in module or "test" in module.lower()
            for module in sys.modules
        )
        if not in_test:
            warnings.warn(
                "MetricsRegistry.reset() called outside of tests. "
                "This may lead to inconsistent metrics state.",
                UserWarning,
                stacklevel=2,
            )

        with cls._lock:
            if cls._instance is not None and cls._instance._initialized:
                # Clear all metrics data from the existing instance
                # This preserves references while resetting state
                cls._instance._clear_all_metrics()

            # Also reset the instance for fresh initialization on next access
            cls._instance = None

    def _clear_all_metrics(self) -> None:
        """Clear all data from metrics (called by reset under lock)."""
        # Clear counter values
        with self.memory_operation_total._lock:
            self.memory_operation_total._values.clear()

        # Clear histogram values
        with self.memory_storage_latency_ms._lock:
            self.memory_storage_latency_ms._values.clear()
        with self.memory_retrieval_latency_ms._lock:
            self.memory_retrieval_latency_ms._values.clear()

        # Clear gauge values
        with self.handler_health_status._lock:
            self.handler_health_status._values.clear()


# Global metrics registry instance
metrics_registry = MetricsRegistry()


class TraceLevel(Enum):
    """Trace level enumeration for different types of operations."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class OperationType(Enum):
    """Operation type enumeration for categorizing operations."""

    MEMORY_STORE = "memory_store"
    MEMORY_RETRIEVE = "memory_retrieve"
    MEMORY_SEARCH = "memory_search"
    INTELLIGENCE_PROCESS = "intelligence_process"
    HEALTH_CHECK = "health_check"
    MIGRATION = "migration"
    CLEANUP = "cleanup"
    EXTERNAL_API = "external_api"


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""

    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_usage_start: Optional[float] = None
    memory_usage_end: Optional[float] = None
    memory_delta: Optional[float] = None
    success: Optional[bool] = None
    error_type: Optional[str] = None


class CorrelationContext(BaseModel):
    """Context information for correlation tracking."""

    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    operation: Optional[str] = Field(default=None)
    parent_correlation_id: Optional[str] = Field(default=None)
    trace_level: TraceLevel = Field(default=TraceLevel.INFO)
    metadata: ModelMetadata = Field(default_factory=ModelMetadata)
    created_at: datetime = Field(default_factory=datetime.now)


class ObservabilityManager:
    """
    Comprehensive observability manager for OmniMemory.

    Provides:
    - Correlation ID management and propagation
    - Distributed tracing support
    - Performance monitoring
    - Enhanced logging with context
    """

    def __init__(self):
        self._active_traces: Dict[str, PerformanceMetrics] = {}
        self._logger = structlog.get_logger(__name__)

    @asynccontextmanager
    async def correlation_context(
        self,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        trace_level: TraceLevel = TraceLevel.INFO,
        **metadata,
    ) -> AsyncGenerator[CorrelationContext, None]:
        """
        Async context manager for correlation tracking.

        Args:
            correlation_id: Unique correlation identifier
            request_id: Request identifier
            user_id: User identifier
            operation: Operation name
            trace_level: Tracing level
            **metadata: Additional metadata
        """
        # Validate correlation ID if provided
        if correlation_id and not validate_correlation_id(correlation_id):
            raise ValueError(f"Invalid correlation ID format: {correlation_id}")

        # Sanitize metadata values
        sanitized_metadata = {
            key: sanitize_metadata_value(value) for key, value in metadata.items()
        }

        # Create context
        context = CorrelationContext(
            correlation_id=correlation_id or str(uuid.uuid4()),
            request_id=request_id,
            user_id=user_id,
            operation=operation,
            parent_correlation_id=correlation_id_var.get(),
            trace_level=trace_level,
            metadata=sanitized_metadata,
        )

        # Set context variables
        correlation_token = correlation_id_var.set(context.correlation_id)
        request_token = request_id_var.set(context.request_id)
        user_token = user_id_var.set(context.user_id)
        operation_token = operation_var.set(context.operation)

        try:
            self._logger.info(
                "correlation_context_started",
                correlation_id=context.correlation_id,
                request_id=context.request_id,
                user_id=context.user_id,
                operation=context.operation,
                trace_level=context.trace_level.value,
                metadata=context.metadata,
            )

            yield context

        except Exception as e:
            self._logger.error(
                "correlation_context_error",
                correlation_id=context.correlation_id,
                error=_sanitize_error(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            # Reset context variables
            correlation_id_var.reset(correlation_token)
            request_id_var.reset(request_token)
            user_id_var.reset(user_token)
            operation_var.reset(operation_token)

            self._logger.info(
                "correlation_context_ended",
                correlation_id=context.correlation_id,
                operation=context.operation,
            )

    @asynccontextmanager
    async def trace_operation(
        self,
        operation_name: str,
        operation_type: OperationType,
        trace_performance: bool = True,
        **additional_context,
    ) -> AsyncGenerator[str, None]:
        """
        Async context manager for operation tracing.

        Args:
            operation_name: Name of the operation being traced
            operation_type: Type of operation
            trace_performance: Whether to track performance metrics
            **additional_context: Additional context for tracing
        """
        trace_id = str(uuid.uuid4())
        correlation_id = correlation_id_var.get()

        # Initialize performance metrics if requested
        start_memory: Optional[float] = None
        if trace_performance:
            # Only track memory if psutil is available
            if _PSUTIL_AVAILABLE and psutil is not None:
                try:
                    process = psutil.Process()
                    start_memory = process.memory_info().rss / 1024 / 1024  # MB
                except (psutil.Error, OSError):
                    # Gracefully handle psutil errors (e.g., permission issues)
                    start_memory = None

            metrics = PerformanceMetrics(
                start_time=time.time(), memory_usage_start=start_memory
            )
            self._active_traces[trace_id] = metrics

        try:
            self._logger.info(
                "operation_started",
                trace_id=trace_id,
                correlation_id=correlation_id,
                operation_name=operation_name,
                operation_type=operation_type.value,
                **additional_context,
            )

            yield trace_id

            # Mark as successful
            if trace_performance and trace_id in self._active_traces:
                self._active_traces[trace_id].success = True

        except Exception as e:
            # Mark as failed and log error
            if trace_performance and trace_id in self._active_traces:
                self._active_traces[trace_id].success = False
                self._active_traces[trace_id].error_type = type(e).__name__

            self._logger.error(
                "operation_failed",
                trace_id=trace_id,
                correlation_id=correlation_id,
                operation_name=operation_name,
                operation_type=operation_type.value,
                error=_sanitize_error(e),
                error_type=type(e).__name__,
                **additional_context,
            )
            raise
        finally:
            # Complete performance metrics if requested
            if trace_performance and trace_id in self._active_traces:
                metrics = self._active_traces[trace_id]
                metrics.end_time = time.time()
                metrics.duration = metrics.end_time - metrics.start_time

                if metrics.memory_usage_start is not None:
                    # Only track memory delta if psutil is available
                    if _PSUTIL_AVAILABLE and psutil is not None:
                        try:
                            process = psutil.Process()
                            end_memory = process.memory_info().rss / 1024 / 1024  # MB
                            metrics.memory_usage_end = end_memory
                            metrics.memory_delta = (
                                end_memory - metrics.memory_usage_start
                            )
                        except (psutil.Error, OSError):
                            # Gracefully handle psutil errors
                            pass

                self._logger.info(
                    "operation_completed",
                    trace_id=trace_id,
                    correlation_id=correlation_id,
                    operation_name=operation_name,
                    operation_type=operation_type.value,
                    duration=metrics.duration,
                    memory_delta=metrics.memory_delta,
                    success=metrics.success,
                    error_type=metrics.error_type,
                    **additional_context,
                )

                # Clean up completed trace
                del self._active_traces[trace_id]

    def get_current_context(self) -> Dict[str, Optional[str]]:
        """Get current correlation context."""
        return {
            "correlation_id": correlation_id_var.get(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "operation": operation_var.get(),
        }

    def get_performance_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get current performance metrics for active traces."""
        return self._active_traces.copy()

    def log_with_context(self, level: str, message: str, **additional_fields):
        """Log a message with current correlation context."""
        context = self.get_current_context()

        log_method = getattr(self._logger, level.lower(), self._logger.info)
        log_method(message, **context, **additional_fields)


# Global observability manager instance
observability_manager = ObservabilityManager()


# Convenience functions for common patterns
@asynccontextmanager
async def correlation_context(
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    operation: Optional[str] = None,
    **metadata,
):
    """Convenience function for correlation context management."""
    async with observability_manager.correlation_context(
        correlation_id=correlation_id,
        request_id=request_id,
        user_id=user_id,
        operation=operation,
        **metadata,
    ) as ctx:
        yield ctx


@asynccontextmanager
async def trace_operation(
    operation_name: str, operation_type: OperationType | str, **context
):
    """Convenience function for operation tracing."""
    if isinstance(operation_type, str):
        # Try to convert string to OperationType
        try:
            operation_type = OperationType(operation_type)
        except ValueError:
            # Default to external API if unknown
            operation_type = OperationType.EXTERNAL_API

    async with observability_manager.trace_operation(
        operation_name=operation_name, operation_type=operation_type, **context
    ) as trace_id:
        yield trace_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_var.get()


def log_with_correlation(level: str, message: str, **fields):
    """Log a message with correlation context."""
    observability_manager.log_with_context(level, message, **fields)


def inject_correlation_context(func: F) -> F:
    """Decorator to inject correlation context into function logs."""

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> object:
        context = observability_manager.get_current_context()
        logger.info(
            f"function_called_{func.__name__}",
            **context,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys()),
        )
        try:
            result = func(*args, **kwargs)
            logger.info(f"function_completed_{func.__name__}", **context, success=True)
            return result
        except Exception as e:
            logger.error(
                f"function_failed_{func.__name__}",
                **context,
                error=_sanitize_error(e),
                error_type=type(e).__name__,
            )
            raise

    return wrapper  # type: ignore[return-value]


def inject_correlation_context_async(func: F) -> F:
    """Async decorator to inject correlation context into function logs."""

    @functools.wraps(func)
    async def wrapper(*args: object, **kwargs: object) -> object:
        context = observability_manager.get_current_context()
        logger.info(
            f"async_function_called_{func.__name__}",
            **context,
            args_count=len(args),
            kwargs_keys=list(kwargs.keys()),
        )
        try:
            result = await func(*args, **kwargs)
            logger.info(
                f"async_function_completed_{func.__name__}", **context, success=True
            )
            return result
        except Exception as e:
            logger.error(
                f"async_function_failed_{func.__name__}",
                **context,
                error=_sanitize_error(e),
                error_type=type(e).__name__,
            )
            raise

    return wrapper  # type: ignore[return-value]


# === HANDLER OBSERVABILITY WRAPPER ===
# "One wrapper, one log line, no payload" pattern for P1C observability


@dataclass
class HandlerMetrics:
    """Metrics captured during handler execution.

    This dataclass holds all metrics collected during a single handler operation,
    ready to be logged and recorded.
    """

    correlation_id: str
    operation: str
    handler: str
    status: Literal["success", "failure"]
    latency_ms: float
    error_type: Optional[str] = None
    error_message: Optional[str] = None


def _get_safe_content_metadata(
    content: Optional[str],
    field_name: str = "content",
) -> Dict[str, Union[str, int, bool]]:
    """Extract safe metadata from content without logging PII.

    Instead of logging raw content, we log:
    - Length of content
    - Hash prefix (first 8 chars of SHA-256)
    - Whether content exists

    Args:
        content: Raw content string (may contain PII)
        field_name: Name prefix for the metadata fields

    Returns:
        Dict with safe metadata about the content
    """
    if content is None:
        return {
            f"{field_name}_exists": False,
            f"{field_name}_len": 0,
        }

    import hashlib

    content_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    return {
        f"{field_name}_exists": True,
        f"{field_name}_len": len(content),
        f"{field_name}_hash": content_hash,
    }


class HandlerObservabilityWrapper:
    """Wrapper for handler operations providing observability.

    Implements the "one wrapper, one log line, no payload" pattern:
    - Wraps handler execution with timing
    - Records metrics (latency histogram, operation counter, health gauge)
    - Emits single structured log event per operation
    - Ensures no PII in log output

    Example usage:
        ```python
        wrapper = HandlerObservabilityWrapper(handler_name="filesystem")

        async def store_memory(request: MemoryStoreRequest) -> MemoryStoreResponse:
            async with wrapper.observe_operation(
                operation="store",
                correlation_id=str(request.correlation_id),
            ) as ctx:
                # ... perform actual storage operation ...
                result = await do_storage(request)
                return result
        ```
    """

    # Pattern for valid handler names: alphanumeric, underscore, hyphen, max 64 chars
    _HANDLER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

    def __init__(
        self,
        handler_name: str,
        registry: Optional[MetricsRegistry] = None,
    ) -> None:
        """Initialize the wrapper.

        Args:
            handler_name: Name of the handler (e.g., "filesystem", "postgresql").
                         Must be a non-empty string containing only alphanumeric
                         characters, underscores, and hyphens (max 64 characters).
            registry: Optional metrics registry (defaults to current singleton)

        Raises:
            ValueError: If handler_name is not a valid string or doesn't match
                       the required pattern.
        """
        # Validate handler_name is a non-empty string
        if not isinstance(handler_name, str):
            raise ValueError(
                f"handler_name must be a string, got {type(handler_name).__name__}"
            )

        if not handler_name:
            raise ValueError("handler_name must be a non-empty string")

        # Validate handler_name matches safe pattern
        if not self._HANDLER_NAME_PATTERN.match(handler_name):
            raise ValueError(
                f"handler_name must contain only alphanumeric characters, "
                f"underscores, and hyphens (max 64 characters), got: {handler_name!r}"
            )

        self.handler_name = handler_name
        self._custom_registry = registry
        self._logger = structlog.get_logger(f"omnimemory.handler.{handler_name}")

        # Set initial health status to healthy
        self.registry.handler_health_status.set(1.0, handler=handler_name)

    @property
    def registry(self) -> MetricsRegistry:
        """Get the metrics registry (always returns current singleton if not custom)."""
        if self._custom_registry is not None:
            return self._custom_registry
        return MetricsRegistry()

    @asynccontextmanager
    async def observe_operation(
        self,
        operation: str,
        correlation_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, str], None]:
        """Context manager for observing handler operations.

        Implements the core observability pattern:
        1. Start timer
        2. Execute operation in try/except
        3. Record histogram for latency
        4. Increment counter for operation/status
        5. Update health gauge
        6. Emit single structured log event

        Args:
            operation: Operation name (e.g., "store", "retrieve", "delete")
            correlation_id: Request correlation ID (generated if not provided)

        Yields:
            Dict with context info (correlation_id, operation, handler)
        """
        # Generate correlation ID if not provided
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        # Validate correlation ID format
        if not validate_correlation_id(correlation_id):
            correlation_id = str(uuid.uuid4())

        # Set correlation context
        token = correlation_id_var.set(correlation_id)

        # Context to yield
        ctx = {
            "correlation_id": correlation_id,
            "operation": operation,
            "handler": self.handler_name,
        }

        # Start timing
        start_time = time.perf_counter()
        status: Literal["success", "failure"] = "success"
        error_type: Optional[str] = None
        error_message: Optional[str] = None

        try:
            yield ctx

        except Exception as e:
            status = "failure"
            error_type = type(e).__name__
            error_message = _sanitize_error(e)
            raise

        finally:
            # Calculate latency
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000

            # Record metrics
            self._record_metrics(
                operation=operation,
                status=status,
                latency_ms=latency_ms,
            )

            # Emit single structured log event
            self._emit_log_event(
                HandlerMetrics(
                    correlation_id=correlation_id,
                    operation=operation,
                    handler=self.handler_name,
                    status=status,
                    latency_ms=latency_ms,
                    error_type=error_type,
                    error_message=error_message,
                )
            )

            # Reset correlation context
            correlation_id_var.reset(token)

    def _record_metrics(
        self,
        operation: str,
        status: Literal["success", "failure"],
        latency_ms: float,
    ) -> None:
        """Record all metrics for the operation.

        Args:
            operation: Operation name
            status: Operation status (success/failure)
            latency_ms: Operation latency in milliseconds
        """
        # Increment operation counter
        self.registry.memory_operation_total.inc(
            operation=operation,
            status=status,
            handler=self.handler_name,
        )

        # Record latency histogram
        # Use appropriate histogram based on operation type
        if operation in ("store", "update", "delete"):
            self.registry.memory_storage_latency_ms.observe(
                latency_ms,
                operation=operation,
                handler=self.handler_name,
            )
        elif operation in ("retrieve", "list", "search"):
            self.registry.memory_retrieval_latency_ms.observe(
                latency_ms,
                operation=operation,
                handler=self.handler_name,
            )
        else:
            # Default to storage histogram for unknown operations
            self.registry.memory_storage_latency_ms.observe(
                latency_ms,
                operation=operation,
                handler=self.handler_name,
            )

        # Update health gauge based on status
        # Simple policy: success = healthy (1.0), failure = unhealthy (0.0)
        # In production, you might use a sliding window or circuit breaker
        if status == "success":
            self.registry.handler_health_status.set(1.0, handler=self.handler_name)
        else:
            self.registry.handler_health_status.set(0.0, handler=self.handler_name)

    def _emit_log_event(self, metrics: HandlerMetrics) -> None:
        """Emit a single structured log event for the operation.

        This implements the "one log line" part of the pattern.
        All relevant metrics and context are included in a single event.

        Log Schema (consistent with module-level documentation):
            Required fields:
                - correlation_id (str): Unique request correlation identifier
                - operation (str): Operation name (e.g., "store", "retrieve")
                - handler (str): Handler name (e.g., "filesystem", "postgresql")
                - status (str): "success" or "failure"
                - latency_ms (float): Operation latency in milliseconds
                - timestamp (str): ISO8601 timestamp (e.g., "2025-01-19T12:34:56.789Z")

            Optional fields (only on failure):
                - error_type (str): Exception class name
                - error_message (str): Sanitized error message (PII-safe)

        Args:
            metrics: Captured metrics for the operation
        """
        # Generate ISO8601 timestamp for explicit time tracking
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        log_data: Dict[str, Union[str, float, None]] = {
            "correlation_id": metrics.correlation_id,
            "operation": metrics.operation,
            "handler": metrics.handler,
            "status": metrics.status,
            "latency_ms": round(metrics.latency_ms, 2),
            "timestamp": timestamp,
        }

        if metrics.error_type:
            log_data["error_type"] = metrics.error_type
        if metrics.error_message:
            log_data["error_message"] = metrics.error_message

        # Log at appropriate level based on status
        if metrics.status == "success":
            self._logger.info("omnimemory.handler.operation", **log_data)
        else:
            self._logger.error("omnimemory.handler.operation", **log_data)

    def mark_healthy(self) -> None:
        """Explicitly mark handler as healthy."""
        self.registry.handler_health_status.set(1.0, handler=self.handler_name)

    def mark_unhealthy(self) -> None:
        """Explicitly mark handler as unhealthy."""
        self.registry.handler_health_status.set(0.0, handler=self.handler_name)

    def get_handler_stats(self) -> Dict[str, object]:
        """Get statistics for this handler.

        Returns:
            Dict containing counter totals, histogram stats, and health status
        """
        # Get all counter values for this handler
        # Counter label_names are ["operation", "status", "handler"], so handler is at index 2
        all_counters = self.registry.memory_operation_total.get_all()
        handler_counters = {
            k: v
            for k, v in all_counters.items()
            if len(k) > 2 and k[2] == self.handler_name  # Exact match at position 2
        }

        # Get histogram stats for this handler
        # Histogram label_names are ["operation", "handler"], so handler is at index 1
        storage_histograms = self.registry.memory_storage_latency_ms.get_all()
        retrieval_histograms = self.registry.memory_retrieval_latency_ms.get_all()

        handler_storage = {
            k: v
            for k, v in storage_histograms.items()
            if len(k) > 1 and k[1] == self.handler_name  # Exact match at position 1
        }
        handler_retrieval = {
            k: v
            for k, v in retrieval_histograms.items()
            if len(k) > 1 and k[1] == self.handler_name  # Exact match at position 1
        }

        # Get health status
        health = self.registry.handler_health_status.get(handler=self.handler_name)

        return {
            "handler": self.handler_name,
            "health_status": health,
            "operation_counts": handler_counters,
            "storage_latency": handler_storage,
            "retrieval_latency": handler_retrieval,
        }
