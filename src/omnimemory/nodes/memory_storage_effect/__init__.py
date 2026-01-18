# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Memory Storage Effect - ONEX Node (Core 8 Foundation).

CRUD operations to storage backends (PostgreSQL, Redis, Pinecone).

This module exports the declarative ONEX node class that follows the
EFFECT pattern for external I/O operations.
"""
from omnimemory.nodes.memory_storage_effect.node import NodeMemoryStorageEffect

__all__: list[str] = ["NodeMemoryStorageEffect"]
