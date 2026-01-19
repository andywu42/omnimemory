"""
ONEX-compliant enums for omnimemory system.

All enums are centralized here for better maintainability and ONEX compliance.
"""

from .enum_error_code import OmniMemoryErrorCode
from .enum_intelligence_operation_type import (  # noqa: E402
    EnumIntelligenceOperationType,
)
from .enum_memory_operation_type import EnumMemoryOperationType  # noqa: E402
from .enum_memory_storage_type import EnumMemoryStorageType  # noqa: E402
from .enum_migration_status import (  # noqa: E402
    FileProcessingStatus,
    MigrationPriority,
    MigrationStatus,
)
from .enum_priority_level import EnumPriorityLevel  # noqa: E402
from .enum_trust_level import EnumDecayFunction, EnumTrustLevel  # noqa: E402

# Keep backward compatibility during migration
EnumErrorCode = OmniMemoryErrorCode

__all__ = [
    "OmniMemoryErrorCode",
    "EnumErrorCode",  # Backward compatibility alias
    "EnumIntelligenceOperationType",
    "EnumMemoryOperationType",
    "EnumMemoryStorageType",
    "MigrationStatus",
    "MigrationPriority",
    "FileProcessingStatus",
    "EnumTrustLevel",
    "EnumDecayFunction",
    "EnumPriorityLevel",
]
