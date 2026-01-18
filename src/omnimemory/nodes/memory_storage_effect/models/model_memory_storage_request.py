# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Memory Storage Request model for memory storage CRUD operations.

This module defines the request envelope used by the memory_storage_effect node
to perform storage operations (store, retrieve, delete, update, list) on memory
snapshots across PostgreSQL, Redis, and Pinecone backends.

Example:
    >>> from omnimemory.nodes.memory_storage_effect.models import (
    ...     ModelMemoryStorageRequest,
    ... )
    >>> request = ModelMemoryStorageRequest(
    ...     operation="store",
    ...     snapshot=my_snapshot,
    ...     tags=["agent", "decision"],
    ... )

.. versionadded:: 0.1.0
    Initial implementation for OMN-1384.
"""

from typing import Literal

from pydantic import BaseModel, Field

from omnibase_core.models.omnimemory import ModelMemorySnapshot

__all__ = ["ModelMemoryStorageRequest"]


class ModelMemoryStorageRequest(BaseModel):
    """Request envelope for memory storage operations.

    This model encapsulates all parameters needed to perform CRUD operations
    on memory snapshots. The operation field determines which action to take,
    and other fields provide context-specific data for that operation.

    Attributes:
        operation: The storage operation to perform. One of:
            - "store": Create a new snapshot in storage
            - "retrieve": Fetch an existing snapshot by ID
            - "delete": Remove a snapshot from storage
            - "update": Modify an existing snapshot
            - "list": Query snapshots with optional filtering
        snapshot_id: Unique identifier of the snapshot. Required for
            retrieve, delete, and update operations.
        snapshot: The memory snapshot data. Required for store and update
            operations.
        metadata: Additional key-value metadata to attach to the operation
            or filter by during list operations.
        tags: List of tags for categorization and filtering. Used during
            store/update to tag snapshots, or during list to filter results.

    Example:
        >>> # Store a new snapshot
        >>> store_request = ModelMemoryStorageRequest(
        ...     operation="store",
        ...     snapshot=my_snapshot,
        ...     metadata={"source": "agent_alpha"},
        ...     tags=["important", "decision"],
        ... )
        >>>
        >>> # Retrieve an existing snapshot
        >>> retrieve_request = ModelMemoryStorageRequest(
        ...     operation="retrieve",
        ...     snapshot_id="snap_abc123",
        ... )
        >>>
        >>> # List snapshots with tag filter
        >>> list_request = ModelMemoryStorageRequest(
        ...     operation="list",
        ...     tags=["decision"],
        ... )
    """

    operation: Literal["store", "retrieve", "delete", "update", "list"] = Field(
        ...,
        description="The storage operation to perform",
    )

    snapshot_id: str | None = Field(
        default=None,
        description="Snapshot ID (required for retrieve/delete/update)",
    )

    snapshot: ModelMemorySnapshot | None = Field(
        default=None,
        description="Snapshot data (for store/update operations)",
    )

    metadata: dict[str, str] | None = Field(
        default=None,
        description="Additional metadata for the operation or filtering",
    )

    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorization and filtering",
    )
