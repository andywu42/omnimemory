# Handler Reuse Matrix - Core 8 Nodes

## Overview

This document maps existing handlers from `omnibase_infra` to the Core 8 memory nodes in OmniMemory. The goal is to maximize reuse and minimize new code by leveraging proven infrastructure patterns.

## Existing Handlers in omnibase_infra

### Core Infrastructure Handlers (`handlers/`)

| Handler | Purpose | Key Operations | Reuse Potential |
|---------|---------|----------------|-----------------|
| `handler_db.py` | PostgreSQL database | query, execute | HIGH - storage/retrieval |
| `handler_qdrant.py` | Vector store | store_embedding, query_similar, batch operations | HIGH - semantic search |
| `handler_filesystem.py` | Secure file I/O | read_file, write_file, list_directory | MEDIUM - persistent storage |
| `handler_graph.py` | Graph database (Neo4j/Memgraph) | execute_query, create_node, traverse | HIGH - relationship memory |
| `handler_http.py` | HTTP REST client | GET, POST | MEDIUM - external LLM calls |
| `handler_consul.py` | Service discovery | register, deregister, health | LOW - infrastructure only |
| `handler_vault.py` | Secrets management | read, write secrets | LOW - security only |
| `handler_mcp.py` | MCP protocol | MCP operations | LOW - agent communication |
| `handler_manifest_persistence.py` | Manifest storage | persist manifests | LOW - specialized |

### Registration Storage Handlers (`handlers/registration_storage/`)

| Handler | Purpose | Reuse Potential |
|---------|---------|-----------------|
| `handler_registration_storage_postgres.py` | PostgreSQL registration | MEDIUM - storage patterns |
| `handler_registration_storage_mock.py` | Mock for testing | HIGH - testing patterns |

### Service Discovery Handlers (`handlers/service_discovery/`)

| Handler | Purpose | Reuse Potential |
|---------|---------|-----------------|
| `handler_service_discovery_consul.py` | Consul discovery | LOW - infrastructure |
| `handler_service_discovery_mock.py` | Mock discovery | HIGH - testing patterns |

### Node-Specific Handlers (`nodes/node_registration_orchestrator/handlers/`)

| Handler | Purpose | Reuse Potential |
|---------|---------|-----------------|
| `handler_runtime_tick.py` | Timeout detection, lifecycle ticks | HIGH - lifecycle patterns |
| `handler_node_heartbeat.py` | Heartbeat processing | MEDIUM - health patterns |
| `handler_node_introspected.py` | Node introspection | LOW - specialized |
| `handler_node_registration_acked.py` | Registration acknowledgment | LOW - specialized |

### Registry Effect Handlers (`nodes/node_registry_effect/handlers/`)

| Handler | Purpose | Reuse Potential |
|---------|---------|-----------------|
| `handler_postgres_upsert.py` | PostgreSQL upsert | HIGH - storage patterns |
| `handler_postgres_deactivate.py` | PostgreSQL deactivation | MEDIUM - lifecycle |
| `handler_consul_register.py` | Consul registration | LOW - infrastructure |
| `handler_consul_deregister.py` | Consul deregistration | LOW - infrastructure |
| `handler_partial_retry.py` | Retry logic | HIGH - resilience patterns |

### Runtime Handlers (`runtime/`)

| Handler | Purpose | Reuse Potential |
|---------|---------|-----------------|
| `handler_registry.py` | Handler registry | HIGH - registry patterns |
| `handler_routing_loader.py` | Route loading | MEDIUM - routing |
| `handler_contract_source.py` | Contract loading | MEDIUM - contracts |
| `handler_plugin_loader.py` | Plugin loading | LOW - specialized |

---

## Core 8 Node Handler Mapping

### EFFECT Nodes

| Memory Node | Operation | Reuse Strategy | Source Handler | Notes |
|-------------|-----------|----------------|----------------|-------|
| **memory_storage_effect** | store | DIRECT | `handler_db.py` | PostgreSQL for persistent storage |
| memory_storage_effect | store_vector | DIRECT | `handler_qdrant.py` | Vector embeddings storage |
| memory_storage_effect | store_file | DIRECT | `handler_filesystem.py` | File-based persistence |
| memory_storage_effect | retrieve | DIRECT | `handler_db.py` | SQL queries for retrieval |
| memory_storage_effect | retrieve_vector | DIRECT | `handler_qdrant.py` | Vector retrieval by ID |
| **memory_retrieval_effect** | search | DIRECT | `handler_qdrant.py` | `query_similar()` for semantic search |
| memory_retrieval_effect | search_graph | ADAPTER | `handler_graph.py` | `traverse()` for relationship search |
| memory_retrieval_effect | search_text | ADAPTER | `handler_db.py` | Full-text SQL search |

### COMPUTE Nodes

| Memory Node | Operation | Reuse Strategy | Source Handler | Notes |
|-------------|-----------|----------------|----------------|-------|
| **semantic_analyzer_compute** | analyze | NEW | - | New handler for semantic analysis |
| semantic_analyzer_compute | embed | ADAPTER | `handler_http.py` | Call external embedding service |
| semantic_analyzer_compute | extract_entities | NEW | - | NLP entity extraction |
| **similarity_compute** | compare | ADAPTER | `handler_qdrant.py` | Leverage `query_similar()` logic |
| similarity_compute | cosine_distance | NEW | - | Pure compute - no I/O |
| similarity_compute | euclidean_distance | NEW | - | Pure compute - no I/O |

### REDUCER Nodes

| Memory Node | Operation | Reuse Strategy | Source Handler | Notes |
|-------------|-----------|----------------|----------------|-------|
| **memory_consolidator_reducer** | consolidate | ADAPTER | `handler_db.py` | SQL aggregations + custom logic |
| memory_consolidator_reducer | deduplicate | ADAPTER | `handler_qdrant.py` | Vector similarity for dedup |
| memory_consolidator_reducer | merge | NEW | - | Memory merging logic |
| **statistics_reducer** | aggregate | ADAPTER | `handler_db.py` | SQL aggregations (COUNT, SUM, AVG) |
| statistics_reducer | compute_metrics | NEW | - | Memory usage metrics |
| statistics_reducer | summarize | NEW | - | Statistical summaries |

### ORCHESTRATOR Nodes

| Memory Node | Operation | Reuse Strategy | Source Handler | Notes |
|-------------|-----------|----------------|----------------|-------|
| **memory_lifecycle_orchestrator** | coordinate | ADAPTER | `handler_runtime_tick.py` | Tick-based lifecycle events |
| memory_lifecycle_orchestrator | expire | ADAPTER | `handler_postgres_deactivate.py` | Deactivation patterns |
| memory_lifecycle_orchestrator | promote | NEW | - | Memory tier promotion |
| memory_lifecycle_orchestrator | archive | ADAPTER | `handler_filesystem.py` | Archive to cold storage |
| **agent_coordinator_orchestrator** | broadcast | ADAPTER | `handler_http.py` | HTTP broadcast to agents |
| agent_coordinator_orchestrator | subscribe | NEW | - | Subscription management |
| agent_coordinator_orchestrator | notify | ADAPTER | `handler_http.py` | Webhook notifications |

---

## Handler Reuse Strategy Summary

### Strategy Definitions

- **DIRECT**: Use handler as-is with minimal wrapping
- **ADAPTER**: Create thin adapter layer to transform inputs/outputs
- **NEW**: Implement new handler (no suitable existing handler)

### Reuse Statistics

| Strategy | Count | Percentage |
|----------|-------|------------|
| DIRECT | 10 | 40% |
| ADAPTER | 11 | 44% |
| NEW | 4 | 16% |

---

## Recommendations

### High-Priority Reuse (DIRECT)

1. **handler_db.py** - Core storage operations
   - Proven asyncpg implementation with connection pooling
   - Circuit breaker pattern already implemented
   - Supports parameterized queries for security

2. **handler_qdrant.py** - Vector operations
   - Full ProtocolVectorStoreHandler implementation
   - Batch operations, metadata filtering, similarity search
   - Health check caching

3. **handler_filesystem.py** - File persistence
   - Path whitelisting for security
   - Size limits to prevent DoS
   - Symlink protection

### Medium-Priority Adapters (ADAPTER)

1. **handler_graph.py** - Relationship memory
   - Create memory-specific adapter for graph traversal
   - Useful for "memories related to X" queries

2. **handler_http.py** - External services
   - Wrap for LLM embedding calls
   - Wrap for agent broadcast

3. **handler_runtime_tick.py** - Lifecycle patterns
   - Adapt tick detection for memory expiration
   - Reuse projection query patterns

### New Handlers Required (NEW)

1. **handler_semantic_compute.py** - Pure semantic analysis
   - Entity extraction
   - Topic modeling
   - Sentiment analysis

2. **handler_similarity_compute.py** - Pure vector math
   - Distance calculations
   - Threshold comparisons

3. **handler_memory_merge.py** - Memory consolidation
   - Deduplication logic
   - Merge strategies

4. **handler_subscription.py** - Agent subscriptions
   - Topic-based subscriptions
   - Memory change notifications

---

## Implementation Priority

### Phase 1: Foundation (Week 1-2)
1. Import `handler_db.py` for storage
2. Import `handler_qdrant.py` for vectors
3. Import `handler_filesystem.py` for persistence
4. Create `memory_storage_effect` node using these handlers

### Phase 2: Search & Retrieval (Week 3-4)
1. Import `handler_graph.py` for relationships
2. Create `memory_retrieval_effect` with adapters
3. Implement basic similarity compute

### Phase 3: Intelligence (Week 5-6)
1. Create semantic analyzer compute
2. Adapt HTTP handler for LLM calls
3. Implement similarity compute handlers

### Phase 4: Lifecycle & Coordination (Week 7-8)
1. Adapt runtime tick for lifecycle
2. Create memory consolidator reducer
3. Implement agent coordinator orchestrator

---

## Pattern Reuse from omnibase_infra

### Mixins to Reuse
- `MixinAsyncCircuitBreaker` - Fault tolerance
- `MixinEnvelopeExtraction` - Envelope parsing

### Error Patterns to Reuse
- `ModelInfraErrorContext` - Structured error context
- `InfraConnectionError`, `InfraTimeoutError` - Typed errors

### Model Patterns to Reuse
- `ModelHandlerOutput` - Standardized output wrapping
- Health check caching patterns
- Correlation ID propagation

---

## File Locations

**Source Handlers**: `omnibase-infra` package (PyPI) - handlers module

**Target Nodes**: `src/omnimemory/nodes/` (this repository)

### Installation

The `omnibase-infra` package provides the infrastructure handlers. Due to dependency version
constraints (structlog ^23.2.0 vs ^24.4.0), it is installed separately:

```bash
# For local development (editable install):
pip install -e ../omnibase_infra3

# When published to PyPI:
poetry add --group dev omnibase-infra
```

**Recommended Import Strategy**:
```python
# Direct import from omnibase_infra module (installed from omnibase-infra package)
from omnibase_infra.handlers.handler_db import HandlerDb
from omnibase_infra.handlers.handler_qdrant import HandlerQdrant
from omnibase_infra.handlers.handler_filesystem import HandlerFileSystem

# Create memory-specific adapters
class MemoryStorageAdapter:
    def __init__(self, db_handler: HandlerDb, vector_handler: HandlerQdrant):
        self._db = db_handler
        self._vector = vector_handler
```

> **Note**: The PyPI package name uses hyphens (`omnibase-infra`) while Python imports
> use underscores (`omnibase_infra`). This is standard Python packaging convention.
