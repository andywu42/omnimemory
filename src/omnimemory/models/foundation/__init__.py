"""
Foundation domain models for OmniMemory following ONEX standards.

This module provides foundation models for base implementations,
error handling, migration progress tracking, and system-level operations.
"""

from ...enums.enum_error_code import OmniMemoryErrorCode
from ...enums.enum_severity import EnumSeverity  # noqa: E402
from .model_audit_metadata import (  # noqa: E402
    AuditEventDetails,
    PerformanceAuditDetails,
    ResourceUsageMetadata,
    SecurityAuditDetails,
)
from .model_configuration import (  # noqa: E402
    ModelCacheConfig,
    ModelDatabaseConfig,
    ModelObservabilityConfig,
    ModelPerformanceConfig,
    ModelSystemConfiguration,
)
from .model_connection_metadata import (  # noqa: E402
    ConnectionMetadata,
    ConnectionPoolStats,
    SemaphoreMetrics,
)
from .model_contract_version import (  # noqa: E402
    DEFAULT_CONTRACT_VERSION,
    ContractVersionMixin,
    ModelContractVersion,
)
from .model_error_details import ModelErrorDetails  # noqa: E402

# New metadata models for replacing Dict[str, Any]
from .model_health_metadata import (  # noqa: E402
    AggregateHealthMetadata,
    ConfigurationChangeMetadata,
    HealthCheckMetadata,
)
from .model_health_response import (  # noqa: E402
    ModelDependencyStatus,
    ModelHealthResponse,
    ModelResourceMetrics,
)
from .model_memory_data import (  # noqa: E402
    ModelMemoryDataContent,
    ModelMemoryDataValue,
    ModelMemoryRequestData,
    ModelMemoryResponseData,
)
from .model_metrics_response import (  # noqa: E402
    ModelMetricsResponse,
    ModelOperationCounts,
    ModelPerformanceMetrics,
    ModelResourceMetricsDetailed,
)
from .model_migration_progress import (  # noqa: E402
    BatchProcessingMetrics,
    FileProcessingInfo,
    FileProcessingStatus,
    MigrationPriority,
    MigrationProgressMetrics,
    MigrationProgressTracker,
    MigrationStatus,
)
from .model_notes import ModelNote, ModelNotesCollection  # noqa: E402
from .model_progress_summary import (  # noqa: E402
    ModelProgressPerformanceMetrics,
    ProgressSummaryResponse,
)
from .model_semver import ModelSemVer  # noqa: E402
from .model_success_metrics import (  # noqa: E402
    ModelConfidenceInterval,
    ModelConfidenceScore,
    ModelQualityMetrics,
    ModelSuccessRate,
)
from .model_system_health import ModelSystemHealth  # noqa: E402
from .model_typed_collections import (  # noqa: E402
    ModelConfiguration,
    ModelConfigurationOption,
    ModelEventCollection,
    ModelEventData,
    ModelKeyValuePair,
    ModelMetadata,
    ModelOptionalStringList,
    ModelResultCollection,
    ModelResultItem,
    ModelStringList,
    ModelStructuredData,
    ModelStructuredField,
    convert_dict_to_metadata,
    convert_list_of_dicts_to_structured_data,
    convert_list_to_string_list,
)

# Backward compatibility alias
EnumErrorCode = OmniMemoryErrorCode

__all__ = [
    "EnumErrorCode",
    "EnumSeverity",
    "ModelErrorDetails",
    "ModelSystemHealth",
    "ModelHealthResponse",
    "ModelDependencyStatus",
    "ModelResourceMetrics",
    "ModelMetricsResponse",
    "ModelOperationCounts",
    "ModelPerformanceMetrics",
    "ModelResourceMetricsDetailed",
    "ModelSystemConfiguration",
    "ModelDatabaseConfig",
    "ModelCacheConfig",
    "ModelPerformanceConfig",
    "ModelObservabilityConfig",
    # Migration progress tracking
    "MigrationStatus",
    "MigrationPriority",
    "FileProcessingStatus",
    "BatchProcessingMetrics",
    "FileProcessingInfo",
    "MigrationProgressMetrics",
    "MigrationProgressTracker",
    # Typed collections replacing generic types
    "ModelStringList",
    "ModelOptionalStringList",
    "ModelKeyValuePair",
    "ModelMetadata",
    "ModelStructuredField",
    "ModelStructuredData",
    "ModelConfigurationOption",
    "ModelConfiguration",
    "ModelEventData",
    "ModelEventCollection",
    "ModelResultItem",
    "ModelResultCollection",
    "convert_dict_to_metadata",
    "convert_list_to_string_list",
    "convert_list_of_dicts_to_structured_data",
    # New foundation models
    "ModelSemVer",
    "ModelSuccessRate",
    "ModelConfidenceInterval",
    "ModelConfidenceScore",
    "ModelQualityMetrics",
    "ModelNote",
    "ModelNotesCollection",
    "ModelMemoryDataValue",
    "ModelMemoryDataContent",
    "ModelMemoryRequestData",
    "ModelMemoryResponseData",
    # New typed metadata models
    "HealthCheckMetadata",
    "AggregateHealthMetadata",
    "ConfigurationChangeMetadata",
    "AuditEventDetails",
    "ResourceUsageMetadata",
    "SecurityAuditDetails",
    "PerformanceAuditDetails",
    "ConnectionMetadata",
    "ConnectionPoolStats",
    "SemaphoreMetrics",
    "ModelProgressPerformanceMetrics",
    "ProgressSummaryResponse",
    # Contract versioning support
    "ModelContractVersion",
    "ContractVersionMixin",
    "DEFAULT_CONTRACT_VERSION",
]
