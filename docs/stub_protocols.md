# Stub Protocols and Compatibility Layer

## Overview

OmniMemory includes a compatibility layer (`src/omnimemory/compat/`) that provides local implementations for `omnibase_core` components that are not yet available in the installed package version. This document tracks these stubs and their migration path.

**Location**: `src/omnimemory/compat/`

---

## Current Stub Implementations

### 1. NodeResult (Monadic Pattern)

**File**: `src/omnimemory/compat/node_result.py`

**Purpose**: Provides the monadic result pattern for node operations, enabling clean error handling without exceptions.

**Upstream Target**: `omnibase_core.core.monadic.model_node_result.NodeResult`

**Status**: Local stub - awaiting upstream availability

**Usage**:
```python
from omnimemory.compat import NodeResult

# Create success result
result = NodeResult.success(data={"key": "value"})

# Create failure result
result = NodeResult.failure(error="Operation failed", code="ERR_001")

# Pattern matching
if result.is_success:
    process(result.data)
else:
    handle_error(result.error)
```

---

### 2. OnexError / BaseOnexError

**File**: `src/omnimemory/compat/onex_error.py`

**Purpose**: Structured error types for ONEX-compliant error handling with correlation IDs and error codes.

**Upstream Target**: `omnibase_core.core.errors.core_errors.OnexError`

**Status**: Local stub - awaiting upstream availability

**Usage**:
```python
from omnimemory.compat import OnexError, BaseOnexError

# Raise structured error
raise OnexError(
    message="Memory storage failed",
    error_code="MEM_001",
    correlation_id="abc-123",
    details={"operation": "store"}
)
```

---

### 3. ModelOnexContainer / ModelONEXContainer

**File**: `src/omnimemory/compat/model_onex_container.py`

**Purpose**: Dependency injection container for ONEX nodes, providing service registration and resolution.

**Upstream Target**: `omnibase_core.core.model_onex_container.ModelONEXContainer`

**Status**: Local stub - awaiting upstream availability

**Usage**:
```python
from omnimemory.compat import ModelOnexContainer

container = ModelOnexContainer()
container.register("db_handler", HandlerDb())
db = container.resolve("db_handler")
```

---

## Migration Path

### Phase 1: Monitoring (Current)

Monitor `omnibase_core` releases for availability of:
- `omnibase_core.core.monadic.model_node_result`
- `omnibase_core.core.errors.core_errors`
- `omnibase_core.core.model_onex_container`

### Phase 2: Migration

When upstream components become available:

1. **Update Imports**:
   ```python
   # Before (using stub)
   from omnimemory.compat import NodeResult

   # After (using upstream)
   from omnibase_core.core.monadic.model_node_result import NodeResult
   ```

2. **Run Test Suite**:
   ```bash
   pytest tests/ -v
   ```

3. **Verify API Compatibility**:
   - Ensure upstream API matches local stub
   - Update any incompatible usages

4. **Remove Stubs**:
   - Delete files from `src/omnimemory/compat/`
   - Remove exports from `__init__.py`
   - Update `docs/stub_protocols.md`

### Phase 3: Cleanup

- Remove `src/omnimemory/compat/` directory
- Update this documentation
- Remove migration notes from code

---

## Other Incomplete Features

The following features are defined but not fully implemented:

### PII Detection - Partial Implementation

**File**: `src/omnimemory/utils/pii_detector.py`

The following `PIIType` values are defined but do not have detection patterns:

| Type | Status | Required Work |
|------|--------|---------------|
| `URL` | Not Implemented | Add URL validation regex patterns |
| `PERSON_NAME` | Not Implemented | Add dictionary-based + NLP name detection |
| `ADDRESS` | Not Implemented | Add geocoding or NLP integration |

See [PII Handling Guide](./pii_handling.md) for details.

### Health Manager - Placeholder

**File**: `src/omnimemory/utils/health_manager.py`

Contains a placeholder for health check aggregation logic that returns healthy status. Full implementation pending:

```python
# Current placeholder (line 646)
# For now, return healthy as a placeholder
```

---

## Dependency on omnibase_infra

The handler reuse matrix (`docs/handler_reuse_matrix.md`) references handlers from `omnibase_infra`. This package should be added as a dependency when it becomes available on PyPI.

**Current Status**: Commented in `pyproject.toml` dev dependencies

**Add when available**:
```bash
poetry add --group dev omnibase-infra
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-18 | Initial documentation |
