"""
Compatibility layer for missing omnibase_core components.

This module provides local implementations for omnibase_core
components that are not yet available in the installed version.
These should be removed once omnibase_core is updated.
"""

from .node_result import NodeResult
from .onex_error import OnexError, BaseOnexError
from .model_onex_container import ModelOnexContainer

__all__ = ["NodeResult", "OnexError", "BaseOnexError", "ModelOnexContainer"]
