# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""FileSystem Handler Adapter for memory storage operations.

This module provides an adapter that wraps `HandlerFileSystem` from omnibase_infra
to implement memory CRUD operations for storing, retrieving, and managing memory
snapshots as JSON files on the filesystem.

The adapter translates between the memory storage request/response models and
the underlying filesystem handler's envelope-based protocol.

Example:
    >>> from omnimemory.nodes.memory_storage_effect.handlers import (
    ...     HandlerFileSystemAdapter,
    ...     HandlerFileSystemAdapterConfig,
    ... )
    >>> from pathlib import Path
    >>>
    >>> config = HandlerFileSystemAdapterConfig(base_path=Path("/data/memory"))
    >>> adapter = HandlerFileSystemAdapter(config)
    >>> await adapter.initialize()
    >>>
    >>> # Store a snapshot
    >>> request = ModelMemoryStorageRequest(operation="store", snapshot=my_snapshot)
    >>> response = await adapter.execute(request)

.. versionadded:: 0.1.0
    Initial implementation for OMN-1384.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from omnibase_infra.handlers.handler_filesystem import HandlerFileSystem
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from omnibase_core.models.omnimemory import ModelMemorySnapshot

from ..models import ModelMemoryStorageRequest, ModelMemoryStorageResponse

__all__ = [
    "HandlerFileSystemAdapter",
    "HandlerFileSystemAdapterConfig",
]


class HandlerFileSystemAdapterConfig(BaseModel):
    """Configuration for FileSystem adapter.

    Attributes:
        base_path: Base path for memory storage. All snapshots will be stored
            under this directory.
        snapshots_dir: Subdirectory name for storing snapshot JSON files.
            Defaults to "snapshots".
        max_file_size: Maximum file size in bytes for read/write operations.
            Defaults to 10MB.
    """

    base_path: Path = Field(
        ...,
        description="Base path for memory storage",
    )
    snapshots_dir: str = Field(
        default="snapshots",
        description="Subdirectory for snapshots",
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum file size in bytes (default 10MB)",
    )


class HandlerFileSystemAdapter:
    """Adapter that wraps HandlerFileSystem for memory storage operations.

    This adapter provides a high-level interface for memory CRUD operations
    on top of the low-level filesystem handler. It manages:

    - Directory structure creation and management
    - Snapshot serialization/deserialization to/from JSON
    - Translation between memory models and filesystem envelopes
    - Error handling and status reporting

    Directory structure:
        <base_path>/
        +-- snapshots/
            +-- <snapshot_id>.json
            +-- <snapshot_id>.json
            +-- ...

    Attributes:
        config: The adapter configuration.
        handler: The underlying HandlerFileSystem instance.

    Example:
        >>> config = HandlerFileSystemAdapterConfig(base_path=Path("/data"))
        >>> adapter = HandlerFileSystemAdapter(config)
        >>> await adapter.initialize()
        >>>
        >>> # Store operation
        >>> store_req = ModelMemoryStorageRequest(
        ...     operation="store",
        ...     snapshot=snapshot
        ... )
        >>> response = await adapter.execute(store_req)
        >>> assert response.status == "success"
    """

    def __init__(self, config: HandlerFileSystemAdapterConfig) -> None:
        """Initialize the adapter with configuration.

        Args:
            config: The adapter configuration specifying paths and limits.
        """
        self._config = config
        self._handler = HandlerFileSystem()
        self._snapshots_path = config.base_path / config.snapshots_dir
        self._initialized = False

    @property
    def config(self) -> HandlerFileSystemAdapterConfig:
        """Get the adapter configuration."""
        return self._config

    @property
    def handler(self) -> HandlerFileSystem:
        """Get the underlying filesystem handler."""
        return self._handler

    @property
    def snapshots_path(self) -> Path:
        """Get the path where snapshots are stored."""
        return self._snapshots_path

    @property
    def is_initialized(self) -> bool:
        """Check if the adapter has been initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """Initialize the handler and create directories.

        This method must be called before any execute operations. It:
        1. Initializes the underlying filesystem handler with allowed paths
        2. Creates the snapshots directory if it doesn't exist

        Raises:
            RuntimeError: If initialization fails.
        """
        if self._initialized:
            return

        # Initialize underlying handler with allowed paths
        await self._handler.initialize(
            {
                "allowed_paths": [str(self._config.base_path)],
                "max_read_size": self._config.max_file_size,
                "max_write_size": self._config.max_file_size,
            }
        )

        # Create snapshots directory using the handler
        envelope = self._build_envelope(
            operation="filesystem.ensure_directory",
            payload={"path": str(self._snapshots_path)},
        )
        await self._handler.execute(envelope)
        self._initialized = True

    async def execute(
        self, request: ModelMemoryStorageRequest
    ) -> ModelMemoryStorageResponse:
        """Execute a memory storage operation.

        This method routes the request to the appropriate handler method
        based on the operation type.

        Args:
            request: The storage operation request.

        Returns:
            Response with operation status and any retrieved data.

        Raises:
            RuntimeError: If the adapter is not initialized.
        """
        if not self._initialized:
            await self.initialize()

        match request.operation:
            case "store":
                return await self._store(request)
            case "retrieve":
                return await self._retrieve(request)
            case "delete":
                return await self._delete(request)
            case "update":
                return await self._update(request)
            case "list":
                return await self._list(request)
            case _:
                return ModelMemoryStorageResponse(
                    status="error",
                    error_message=f"Unknown operation: {request.operation}",
                )

    async def _store(
        self, request: ModelMemoryStorageRequest
    ) -> ModelMemoryStorageResponse:
        """Store a memory snapshot.

        Args:
            request: The store request containing the snapshot.

        Returns:
            Response with success status and stored snapshot, or error.
        """
        if request.snapshot is None:
            return ModelMemoryStorageResponse(
                status="error",
                error_message="snapshot is required for store operation",
            )

        snapshot_id = request.snapshot.snapshot_id
        file_path = self._snapshots_path / f"{snapshot_id}.json"

        envelope = self._build_envelope(
            operation="filesystem.write_file",
            payload={
                "path": str(file_path),
                "content": request.snapshot.model_dump_json(indent=2),
            },
        )

        try:
            result = await self._handler.execute(envelope)
            if result.result and result.result.get("status") == "success":
                return ModelMemoryStorageResponse(
                    status="success",
                    snapshot=request.snapshot,
                )
            return ModelMemoryStorageResponse(
                status="error",
                error_message="Write operation failed",
            )
        except Exception as e:
            return ModelMemoryStorageResponse(
                status="error",
                error_message=f"Store failed: {e}",
            )

    async def _retrieve(
        self, request: ModelMemoryStorageRequest
    ) -> ModelMemoryStorageResponse:
        """Retrieve a memory snapshot by ID.

        Args:
            request: The retrieve request containing the snapshot ID.

        Returns:
            Response with success status and retrieved snapshot, or not_found.
        """
        if request.snapshot_id is None:
            return ModelMemoryStorageResponse(
                status="error",
                error_message="snapshot_id is required for retrieve operation",
            )

        file_path = self._snapshots_path / f"{request.snapshot_id}.json"

        envelope = self._build_envelope(
            operation="filesystem.read_file",
            payload={"path": str(file_path)},
        )

        try:
            result = await self._handler.execute(envelope)
            if result.result and result.result.get("status") == "success":
                payload = result.result.get("payload", {})
                content = payload.get("content", "")

                # Import here to avoid circular imports
                from omnibase_core.models.omnimemory import ModelMemorySnapshot

                snapshot = ModelMemorySnapshot.model_validate_json(content)
                return ModelMemoryStorageResponse(
                    status="success",
                    snapshot=snapshot,
                )
            return ModelMemoryStorageResponse(
                status="not_found",
                error_message=f"Snapshot {request.snapshot_id} not found",
            )
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                return ModelMemoryStorageResponse(
                    status="not_found",
                    error_message=f"Snapshot {request.snapshot_id} not found",
                )
            return ModelMemoryStorageResponse(
                status="error",
                error_message=f"Retrieve failed: {e}",
            )

    async def _delete(
        self, request: ModelMemoryStorageRequest
    ) -> ModelMemoryStorageResponse:
        """Delete a memory snapshot by ID.

        Args:
            request: The delete request containing the snapshot ID.

        Returns:
            Response with success status, or not_found if snapshot doesn't exist.
        """
        if request.snapshot_id is None:
            return ModelMemoryStorageResponse(
                status="error",
                error_message="snapshot_id is required for delete operation",
            )

        file_path = self._snapshots_path / f"{request.snapshot_id}.json"

        envelope = self._build_envelope(
            operation="filesystem.delete_file",
            payload={"path": str(file_path)},
        )

        try:
            result = await self._handler.execute(envelope)
            if result.result and result.result.get("status") == "success":
                return ModelMemoryStorageResponse(status="success")
            return ModelMemoryStorageResponse(
                status="not_found",
                error_message=f"Snapshot {request.snapshot_id} not found",
            )
        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                return ModelMemoryStorageResponse(
                    status="not_found",
                    error_message=f"Snapshot {request.snapshot_id} not found",
                )
            return ModelMemoryStorageResponse(
                status="error",
                error_message=f"Delete failed: {e}",
            )

    async def _update(
        self, request: ModelMemoryStorageRequest
    ) -> ModelMemoryStorageResponse:
        """Update a memory snapshot (store with existing ID).

        For filesystem storage, update is equivalent to store since
        writing to the same path overwrites the existing file.

        Args:
            request: The update request containing the snapshot.

        Returns:
            Response with success status and updated snapshot, or error.
        """
        # For FileSystem, update is the same as store
        return await self._store(request)

    async def _list(
        self, request: ModelMemoryStorageRequest
    ) -> ModelMemoryStorageResponse:
        """List all snapshot IDs, optionally filtered by tags.

        Note: Tag filtering is not implemented for filesystem storage.
        All snapshot IDs are returned.

        Args:
            request: The list request (tags filter not currently used).

        Returns:
            Response with list of snapshot IDs.
        """
        envelope = self._build_envelope(
            operation="filesystem.list_directory",
            payload={"path": str(self._snapshots_path)},
        )

        try:
            result = await self._handler.execute(envelope)
            if result.result and result.result.get("status") == "success":
                payload = result.result.get("payload", {})
                entries = payload.get("entries", [])
                # Extract snapshot IDs from filenames
                snapshot_ids = [
                    Path(entry.get("name", "")).stem
                    for entry in entries
                    if entry.get("name", "").endswith(".json")
                ]
                return ModelMemoryStorageResponse(
                    status="success",
                    snapshot_ids=snapshot_ids,
                )
            return ModelMemoryStorageResponse(
                status="success",
                snapshot_ids=[],
            )
        except Exception as e:
            return ModelMemoryStorageResponse(
                status="error",
                error_message=f"List failed: {e}",
            )

    def _build_envelope(
        self,
        operation: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        """Build an envelope for the filesystem handler.

        Args:
            operation: The filesystem operation (e.g., "filesystem.write_file").
            payload: The operation-specific payload.

        Returns:
            A properly formatted envelope for the handler.
        """
        return {
            "envelope_id": str(uuid.uuid4()),
            "correlation_id": str(uuid.uuid4()),
            "operation": operation,
            "payload": payload,
        }

    async def shutdown(self) -> None:
        """Shutdown the handler and release resources."""
        if self._initialized:
            await self._handler.shutdown()
            self._initialized = False
