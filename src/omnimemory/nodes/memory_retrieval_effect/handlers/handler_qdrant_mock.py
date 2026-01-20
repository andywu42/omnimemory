# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Mock Qdrant Handler for semantic search operations.

This module provides a mock handler that simulates `HandlerQdrant` behavior
for semantic similarity search. It allows development and testing of the
memory_retrieval_effect node without requiring a running Qdrant instance.

The mock uses simple text matching to simulate similarity scores, making it
suitable for unit tests and local development. When the real Qdrant service
is available, this can be swapped for the real HandlerQdrant.

Example::

    import asyncio
    from omnimemory.nodes.memory_retrieval_effect.handlers import (
        HandlerQdrantMock,
        HandlerQdrantMockConfig,
    )

    async def example():
        config = HandlerQdrantMockConfig()
        handler = HandlerQdrantMock(config)
        await handler.initialize()

        # Seed with test data
        handler.seed_snapshots([snapshot1, snapshot2])

        # Search
        request = ModelMemoryRetrievalRequest(
            operation="search",
            query_text="authentication decision",
            limit=5,
        )
        response = await handler.execute(request)

    asyncio.run(example())

.. versionadded:: 0.1.0
    Initial implementation for OMN-1387.
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
from collections.abc import Sequence

from omnibase_core.models.omnimemory import ModelMemorySnapshot
from pydantic import BaseModel, Field

from ..models import (
    ModelMemoryRetrievalRequest,
    ModelMemoryRetrievalResponse,
    ModelSearchResult,
)

logger = logging.getLogger(__name__)

__all__ = [
    "HandlerQdrantMock",
    "HandlerQdrantMockConfig",
]


class HandlerQdrantMockConfig(BaseModel):
    """Configuration for the mock Qdrant handler.

    Attributes:
        embedding_dimension: Dimension of embedding vectors. Defaults to 1536
            (OpenAI text-embedding-3-small compatible).
        simulate_latency_ms: Simulated latency for operations in milliseconds.
            Set to 0 for instant responses.
        embedding_endpoint: URL for embedding service (for future use when
            real embeddings are available).
    """

    embedding_dimension: int = Field(
        default=1536,
        description="Dimension of embedding vectors",
    )
    simulate_latency_ms: int = Field(
        default=0,
        ge=0,
        description="Simulated latency in milliseconds",
    )
    embedding_endpoint: str | None = Field(
        default=None,
        description="URL for embedding service (optional)",
    )


class HandlerQdrantMock:
    """Mock handler that simulates HandlerQdrant for semantic search.

    This handler provides a development-friendly interface for testing
    semantic search functionality without requiring a real Qdrant instance.
    It uses simple text similarity (word overlap) to simulate vector similarity.

    The handler maintains an in-memory store of snapshots and can be seeded
    with test data for reproducible testing.

    Attributes:
        config: The handler configuration.

    Example::

        async def example():
            handler = HandlerQdrantMock(HandlerQdrantMockConfig())
            await handler.initialize()

            # Seed test data
            handler.seed_snapshots([snapshot1, snapshot2])

            # Execute search
            request = ModelMemoryRetrievalRequest(
                operation="search",
                query_text="authentication",
            )
            response = await handler.execute(request)
    """

    def __init__(self, config: HandlerQdrantMockConfig) -> None:
        """Initialize the mock handler with configuration.

        Args:
            config: The handler configuration.
        """
        self._config = config
        self._snapshots: dict[str, ModelMemorySnapshot] = {}
        self._embeddings: dict[str, list[float]] = {}
        self._initialized = False
        self._init_lock = asyncio.Lock()

    @property
    def config(self) -> HandlerQdrantMockConfig:
        """Get the handler configuration."""
        return self._config

    @property
    def is_initialized(self) -> bool:
        """Check if the handler has been initialized."""
        return self._initialized

    @property
    def snapshot_count(self) -> int:
        """Get the number of stored snapshots."""
        return len(self._snapshots)

    async def initialize(self) -> None:
        """Initialize the mock handler.

        Thread-safe: Uses asyncio.Lock to prevent concurrent initialization.
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            logger.info(
                "Mock Qdrant handler initialized with embedding dim=%d",
                self._config.embedding_dimension,
            )
            self._initialized = True

    def seed_snapshots(
        self,
        snapshots: Sequence[ModelMemorySnapshot],
        embeddings: dict[str, list[float]] | None = None,
    ) -> None:
        """Seed the mock store with test snapshots.

        Args:
            snapshots: List of snapshots to add to the mock store.
            embeddings: Optional pre-computed embeddings keyed by snapshot_id.
                If not provided, mock embeddings will be generated.
        """
        for snapshot in snapshots:
            snapshot_id = str(snapshot.snapshot_id)
            self._snapshots[snapshot_id] = snapshot

            # Use provided embedding or generate mock
            if embeddings and snapshot_id in embeddings:
                self._embeddings[snapshot_id] = embeddings[snapshot_id]
            else:
                self._embeddings[snapshot_id] = self._generate_mock_embedding(snapshot)

        logger.debug("Seeded %d snapshots into mock store", len(snapshots))

    def clear(self) -> None:
        """Clear all snapshots from the mock store."""
        self._snapshots.clear()
        self._embeddings.clear()

    async def execute(
        self, request: ModelMemoryRetrievalRequest
    ) -> ModelMemoryRetrievalResponse:
        """Execute a semantic search operation.

        Args:
            request: The retrieval request (must have operation="search").

        Returns:
            Response with search results ordered by similarity.

        Raises:
            ValueError: If operation is not "search".
        """
        if not self._initialized:
            await self.initialize()

        if request.operation != "search":
            return ModelMemoryRetrievalResponse(
                status="error",
                error_message=f"HandlerQdrantMock only supports 'search', "
                f"got '{request.operation}'",
            )

        # Simulate latency if configured
        if self._config.simulate_latency_ms > 0:
            await asyncio.sleep(self._config.simulate_latency_ms / 1000)

        # Get or generate query embedding
        if request.query_embedding is not None:
            query_embedding = request.query_embedding
        elif request.query_text is not None:
            query_embedding = self._text_to_mock_embedding(request.query_text)
        else:
            return ModelMemoryRetrievalResponse(
                status="error",
                error_message="Either query_text or query_embedding required",
            )

        # Score all snapshots
        scored_results: list[tuple[str, float]] = []
        for snapshot_id, embedding in self._embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            if similarity >= request.similarity_threshold:
                scored_results.append((snapshot_id, similarity))

        # Sort by similarity (highest first) and limit
        scored_results.sort(key=lambda x: x[1], reverse=True)
        scored_results = scored_results[: request.limit]

        # Build response
        if not scored_results:
            return ModelMemoryRetrievalResponse(
                status="no_results",
                results=[],
                total_count=0,
                query_embedding_used=query_embedding,
            )

        results = [
            ModelSearchResult(
                snapshot=self._snapshots[snapshot_id],
                score=score,
                distance=1.0 - score,  # Convert similarity to distance
            )
            for snapshot_id, score in scored_results
        ]

        return ModelMemoryRetrievalResponse(
            status="success",
            results=results,
            total_count=len(results),
            query_embedding_used=query_embedding,
        )

    def _generate_mock_embedding(self, snapshot: ModelMemorySnapshot) -> list[float]:
        """Generate a mock embedding from snapshot content.

        This creates a deterministic pseudo-embedding based on the snapshot's
        text content, allowing consistent similarity matching in tests.

        Args:
            snapshot: The snapshot to embed.

        Returns:
            A mock embedding vector of the configured dimension.
        """
        # Combine text fields for embedding - extract subject_key for searchable text
        text_parts = []
        if snapshot.subject:
            if (
                hasattr(snapshot.subject, "subject_key")
                and snapshot.subject.subject_key
            ):
                text_parts.append(snapshot.subject.subject_key)
        if snapshot.tags:
            text_parts.extend(snapshot.tags)

        text = " ".join(text_parts).lower()
        return self._text_to_mock_embedding(text)

    def _text_to_mock_embedding(self, text: str) -> list[float]:
        """Convert text to a mock embedding vector.

        This creates a deterministic embedding based on word hashes,
        simulating the behavior of a real embedding model for testing.

        Args:
            text: The text to embed.

        Returns:
            A mock embedding vector.
        """
        # Initialize with zeros
        dim = self._config.embedding_dimension
        embedding = [0.0] * dim

        # Hash words into embedding dimensions
        words = text.lower().split()
        for word in words:
            # Use hash to distribute word across dimensions
            word_hash = hash(word)
            for i in range(min(10, len(word))):
                idx = (word_hash + i * 31) % dim
                embedding[idx] += 1.0 / (i + 1)

        # Normalize to unit vector
        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        else:
            # Random unit vector for empty text
            embedding = [random.gauss(0, 1) for _ in range(dim)]
            magnitude = math.sqrt(sum(x * x for x in embedding))
            embedding = [x / magnitude for x in embedding]

        return embedding

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            a: First vector.
            b: Second vector.

        Returns:
            Cosine similarity in range [-1, 1], clamped to [0, 1].
        """
        if len(a) != len(b):
            # Truncate or pad to match
            min_len = min(len(a), len(b))
            a = a[:min_len]
            b = b[:min_len]

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        similarity = dot_product / (magnitude_a * magnitude_b)
        # Clamp to [0, 1] for our use case
        return max(0.0, min(1.0, similarity))

    async def shutdown(self) -> None:
        """Shutdown the handler and release resources."""
        if self._initialized:
            self._snapshots.clear()
            self._embeddings.clear()
            self._initialized = False
            logger.debug("Mock Qdrant handler shutdown complete")
