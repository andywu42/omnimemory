"""
PostgreSQL storage configuration model following ONEX standards.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, PostgresDsn, SecretStr, field_validator


class ModelPostgresConfig(BaseModel):
    """Configuration for PostgreSQL memory storage.

    This config defines connection parameters for PostgreSQL-based
    persistent memory storage. Optional for Phase 1.
    """

    # Connection configuration
    dsn: PostgresDsn = Field(
        description="PostgreSQL connection DSN (e.g., postgresql://user@host:port/db)",
    )
    password: SecretStr = Field(
        description="Database password (stored securely, never logged)",
        exclude=True,
    )

    # Connection pool settings
    pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Connection pool size (1-50)",
    )
    pool_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Pool connection acquisition timeout in seconds",
    )
    pool_recycle_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Connection recycle time in seconds (default 1 hour)",
    )

    # Query settings
    statement_timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Maximum query execution time in seconds",
    )
    lock_timeout_seconds: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Maximum time to wait for locks in seconds",
    )

    # SSL configuration
    ssl_mode: str = Field(
        default="prefer",
        description="SSL mode (disable, allow, prefer, require, verify-ca, verify-full)",
    )

    # Schema configuration
    schema_name: str = Field(
        default="omnimemory",
        description="PostgreSQL schema name for memory tables",
    )

    @field_validator("ssl_mode")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        """Validate SSL mode is a valid PostgreSQL SSL mode."""
        valid_modes = {
            "disable",
            "allow",
            "prefer",
            "require",
            "verify-ca",
            "verify-full",
        }
        if v not in valid_modes:
            raise ValueError(
                f"ssl_mode must be one of: {', '.join(sorted(valid_modes))}"
            )
        return v

    @field_validator("schema_name")
    @classmethod
    def validate_schema_name(cls, v: str) -> str:
        """Validate schema name is a valid PostgreSQL identifier."""
        if not v.isidentifier():
            raise ValueError("schema_name must be a valid identifier")
        if len(v) > 63:
            raise ValueError("schema_name cannot exceed 63 characters")
        return v
