# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Memory Storage Effect Node - ONEX 4-Node Architecture.

This module implements the declarative ONEX node pattern for memory storage
operations. Following ONEX architecture, all business logic is defined in
handlers and contracts - the node class itself is purely declarative.

Node Type: EFFECT
Purpose: CRUD operations to storage backends (PostgreSQL, Redis, Pinecone)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.nodes.base import NodeContainer


class NodeMemoryStorageEffect:
    """Memory storage effect node for CRUD operations.

    This node handles memory storage operations following the ONEX EFFECT
    pattern - all external I/O operations for storing, retrieving, updating,
    and deleting memory records across storage backends.

    Note:
        This class follows the ONEX declarative pattern. All business logic
        is defined in handlers and the contract.yaml specification. The node
        class itself only initializes the container dependency.
    """

    def __init__(self, container: "NodeContainer") -> None:
        """Initialize memory storage effect node.

        Args:
            container: ONEX node container providing dependency injection
                      and handler registration capabilities.
        """
        super().__init__(container)
