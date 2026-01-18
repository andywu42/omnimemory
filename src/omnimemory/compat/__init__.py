"""
Compatibility layer for missing omnibase_core components.

This module provides local implementations for omnibase_core
components that are not yet available in the installed version.
These should be removed once omnibase_core is updated.

Technical Debt Notes:
- NodeResult: Local stub until omnibase_core.core.monadic.model_node_result is available
- OnexError/BaseOnexError: Local stub until omnibase_core.core.errors.core_errors is available
- ModelOnexContainer/ModelONEXContainer: Local stub until omnibase_core.core.model_onex_container is available

Removal Criteria:
- When omnibase_core exposes these components, update imports throughout omnimemory
- Run tests to ensure compatibility
- Remove the local stubs
"""

from .node_result import NodeResult
from .onex_error import OnexError, BaseOnexError
from .model_onex_container import ModelOnexContainer, ModelONEXContainer

__all__ = [
    "NodeResult",
    "OnexError",
    "BaseOnexError",
    "ModelOnexContainer",
    "ModelONEXContainer",  # Alias for upstream compatibility
]
