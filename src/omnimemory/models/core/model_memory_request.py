"""
Memory request model following ONEX standards.
"""

from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_memory_operation_type import EnumMemoryOperationType
from .model_memory_context import ModelMemoryContext
from .model_memory_parameters import ModelMemoryParameters, ModelMemoryOptions
from ..foundation.model_memory_data import ModelMemoryRequestData
from ..foundation.model_contract_version import DEFAULT_CONTRACT_VERSION


class ModelMemoryRequest(BaseModel):
    """Base memory request model following ONEX standards."""

    # Contract version for schema tracking
    contract_version: str = Field(
        default=DEFAULT_CONTRACT_VERSION,
        description="Schema version for this request contract (semver format)",
    )

    # Request identification
    request_id: UUID = Field(
        description="Unique identifier for this request",
    )
    operation_type: EnumMemoryOperationType = Field(
        description="Type of memory operation requested",
    )

    # Context information
    context: ModelMemoryContext = Field(
        description="Context information for the request",
    )

    # Request payload
    data: ModelMemoryRequestData | None = Field(
        default=None,
        description="Structured request data payload following ONEX standards",
    )

    # Request parameters - using structured model instead of dict
    parameters: ModelMemoryParameters = Field(
        default_factory=ModelMemoryParameters,
        description="Structured operation parameters following ONEX standards",
    )

    # Request options - using structured model instead of dict
    options: ModelMemoryOptions = Field(
        default_factory=ModelMemoryOptions,
        description="Boolean options for the request following ONEX standards",
    )