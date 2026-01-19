"""
OmniMemory - Advanced memory management and retrieval system for AI applications.

This package provides comprehensive memory management capabilities including:
- Persistent memory storage with ONEX 4-node architecture
- Vector-based semantic memory with similarity search
- Temporal memory with decay patterns and lifecycle management
- Memory consolidation, aggregation, and optimization
- Cross-modal memory integration and intelligence processing
- Contract-driven development with strong typing and validation
- Monadic error handling with NodeResult composition
- Event-driven architecture with observability patterns

Architecture:
    - Effect Nodes: Memory storage, retrieval, and persistence operations
    - Compute Nodes: Intelligence processing, semantic analysis, pattern recognition
    - Reducer Nodes: Memory consolidation, aggregation, and optimization
    - Orchestrator Nodes: Workflow coordination, agent coordination, system orchestration

Bootstrap:
    OmniMemory requires explicit initialization via the bootstrap() function:

    >>> from omnimemory import bootstrap, BootstrapResult
    >>> from omnimemory.models.config import ModelMemoryServiceConfig, ModelFilesystemConfig
    >>> from pathlib import Path
    >>>
    >>> config = ModelMemoryServiceConfig(
    ...     filesystem=ModelFilesystemConfig(base_path=Path("/data/memory"))
    ... )
    >>> result = await bootstrap(config)
    >>> if result.success:
    ...     print(f"Initialized: {result.initialized_backends}")

Usage:
    >>> from omnimemory.models import core, memory, intelligence
    >>> # Use domain-specific models for memory operations
"""

__version__ = "0.1.0"
__author__ = "OmniNode-ai"
__email__ = "contact@omninode.ai"

# Import bootstrap functions
from .bootstrap import (
    BootstrapError,
    BootstrapResult,
    bootstrap,
    get_bootstrap_result,
    is_bootstrapped,
    shutdown,
)

# Import ONEX-compliant model domains
from .models import core, foundation, intelligence, memory, service

# Import protocol definitions
from .protocols import (  # Base protocols; Effect node protocols (memory storage, retrieval, persistence); Compute node protocols (intelligence processing, semantic analysis); Reducer node protocols (consolidation, aggregation, optimization); Orchestrator node protocols (workflow, agent, memory coordination); Data models; Enums; Error handling
    AccessLevel,
    BaseMemoryRequest,
    BaseMemoryResponse,
    ContentType,
    MemoryPriority,
    MemoryRecord,
    MemoryStoreRequest,
    MemoryStoreResponse,
    OmniMemoryError,
    OmniMemoryErrorCode,
    OperationStatus,
    ProtocolAgentCoordinator,
    ProtocolIntelligenceProcessor,
    ProtocolMemoryAggregator,
    ProtocolMemoryBase,
    ProtocolMemoryConsolidator,
    ProtocolMemoryOperations,
    ProtocolMemoryOptimizer,
    ProtocolMemoryOrchestrator,
    ProtocolMemoryPersistence,
    ProtocolMemoryRetrieval,
    ProtocolMemoryStorage,
    ProtocolPatternRecognition,
    ProtocolSemanticAnalyzer,
    ProtocolWorkflowCoordinator,
    SystemError,
    ValidationError,
)

# Import settings for environment-based configuration
from .settings import (
    FilesystemSettings,
    PostgresSettings,
    QdrantSettings,
    SettingsMemoryService,
    load_settings,
)

__all__ = [
    # Version and metadata
    "__version__",
    "__author__",
    "__email__",
    # Bootstrap functions
    "bootstrap",
    "shutdown",
    "is_bootstrapped",
    "get_bootstrap_result",
    "BootstrapResult",
    "BootstrapError",
    # ONEX model domains
    "core",
    "memory",
    "intelligence",
    "service",
    "foundation",
    # Base protocols
    "ProtocolMemoryBase",
    "ProtocolMemoryOperations",
    # Effect node protocols
    "ProtocolMemoryStorage",
    "ProtocolMemoryRetrieval",
    "ProtocolMemoryPersistence",
    # Compute node protocols
    "ProtocolIntelligenceProcessor",
    "ProtocolSemanticAnalyzer",
    "ProtocolPatternRecognition",
    # Reducer node protocols
    "ProtocolMemoryConsolidator",
    "ProtocolMemoryAggregator",
    "ProtocolMemoryOptimizer",
    # Orchestrator node protocols
    "ProtocolWorkflowCoordinator",
    "ProtocolAgentCoordinator",
    "ProtocolMemoryOrchestrator",
    # Data models
    "BaseMemoryRequest",
    "BaseMemoryResponse",
    "MemoryRecord",
    "MemoryStoreRequest",
    "MemoryStoreResponse",
    # Enums
    "OperationStatus",
    "ContentType",
    "MemoryPriority",
    "AccessLevel",
    # Error handling
    "OmniMemoryError",
    "OmniMemoryErrorCode",
    "ValidationError",
    "SystemError",
    # Settings for environment-based configuration
    "load_settings",
    "SettingsMemoryService",
    "FilesystemSettings",
    "PostgresSettings",
    "QdrantSettings",
]
