"""
Compatibility imports for ONEX type definitions.

This module provides type aliases that work correctly with mypy by using
simple type definitions that avoid conditional type alias issues.
"""

from typing import TypeAlias

# Always import our local types
from omnimemory.enums.enum_error_code import OmniMemoryErrorCode
from omnimemory.enums.enum_severity import EnumSeverity

# Define type aliases using the local types
# This avoids conditional type alias issues with mypy
# At runtime, these work with omnibase_core types via duck typing
ErrorCodeType: TypeAlias = OmniMemoryErrorCode | str
SeverityType: TypeAlias = EnumSeverity

__all__ = ["ErrorCodeType", "SeverityType", "OmniMemoryErrorCode", "EnumSeverity"]
