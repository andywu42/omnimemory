# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Base node classes for ONEX 4-Node Architecture.

This module provides the foundational base classes for all ONEX nodes
in omnimemory. Following ONEX patterns, the base class is minimal and
only provides container injection - all business logic lives in handlers.

Node Types:
- EFFECT: External I/O operations (storage, APIs, file system)
- COMPUTE: Pure transformations and algorithms
- REDUCER: Aggregation and state management
- ORCHESTRATOR: Workflow coordination and routing
"""
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.nodes.base import NodeContainer


class BaseNode(ABC):
    """Abstract base class for all ONEX nodes.

    This base class provides the minimal foundation for ONEX nodes,
    following the declarative pattern where:
    - Node classes are purely declarative (only __init__)
    - Business logic is defined in handlers
    - Contracts specify inputs, outputs, and behavior

    Attributes:
        _container: The ONEX node container for dependency injection
                   and handler registration.

    Example:
        ```python
        class NodeMyEffect(BaseNode):
            def __init__(self, container: "NodeContainer") -> None:
                super().__init__(container)
        ```
    """

    def __init__(self, container: "NodeContainer") -> None:
        """Initialize the base node with container injection.

        Args:
            container: ONEX node container providing dependency injection
                      and handler registration capabilities.
        """
        self._container = container


class BaseEffectNode(BaseNode):
    """Base class for EFFECT nodes - external I/O operations.

    EFFECT nodes handle all external interactions:
    - Database CRUD operations
    - API calls
    - File system operations
    - Message queue operations
    """

    pass


class BaseComputeNode(BaseNode):
    """Base class for COMPUTE nodes - pure transformations.

    COMPUTE nodes perform:
    - Data transformations
    - Algorithm execution
    - Semantic analysis
    - Vector calculations
    """

    pass


class BaseReducerNode(BaseNode):
    """Base class for REDUCER nodes - aggregation and state.

    REDUCER nodes handle:
    - Data aggregation
    - State consolidation
    - Statistics generation
    - Memory merging
    """

    pass


class BaseOrchestratorNode(BaseNode):
    """Base class for ORCHESTRATOR nodes - workflow coordination.

    ORCHESTRATOR nodes manage:
    - Workflow orchestration
    - Cross-node coordination
    - Routing decisions
    - Lifecycle management
    """

    pass


__all__ = [
    "BaseNode",
    "BaseEffectNode",
    "BaseComputeNode",
    "BaseReducerNode",
    "BaseOrchestratorNode",
]
