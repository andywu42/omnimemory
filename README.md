# OmniMemory - Advanced Memory Management System

An advanced memory management and retrieval system designed for AI applications, providing comprehensive memory capabilities including persistent storage, vector-based semantic memory, temporal patterns, and cross-modal integration.

## Overview

OmniMemory provides a sophisticated memory architecture that mirrors human-like memory systems, enabling AI applications to store, retrieve, and consolidate information across multiple modalities and time scales. The system supports both short-term and long-term memory patterns with intelligent decay and consolidation mechanisms.

## 🚀 Quick Start

### Installation

**Option 1: User Directory Installation (Global)**
```bash
# Clone the repository
git clone https://github.com/your-org/omnimemory.git
cd omnimemory

# Install poetry dependencies
poetry install

# Initialize memory storage
poetry run python scripts/init_memory.py
```

**Option 2: Project-Specific Integration**
```bash
# Install as dependency in your project
poetry add git+https://github.com/your-org/omnimemory.git
```

### Basic Usage
```python
from omnimemory import MemoryManager, VectorMemory, TemporalMemory

# Initialize memory systems
memory_manager = MemoryManager()
vector_memory = VectorMemory()
temporal_memory = TemporalMemory()

# Store and retrieve memories
memory_manager.store("context", "This is important information")
result = memory_manager.retrieve("context", similarity_threshold=0.8)
```

## 🧠 Memory Architecture

### Core Memory Systems

**4 Primary Memory Types** covering comprehensive memory management:

### 💾 Persistent Memory
- `PersistentMemory` - Long-term storage with database persistence
- `VersionedMemory` - Memory with version control and history tracking
- `EncryptedMemory` - Secure memory storage with encryption at rest

### 🔍 Semantic Memory
- `VectorMemory` - Vector-based semantic similarity and retrieval
- `EmbeddingMemory` - High-dimensional embedding storage and search
- `SemanticGraph` - Knowledge graph representation for complex relationships

### ⏰ Temporal Memory
- `TemporalMemory` - Time-aware memory with decay patterns
- `ScheduledMemory` - Memory with scheduled retrieval and updates
- `ContextualMemory` - Memory that adapts based on contextual patterns

### 🔄 Memory Consolidation
- `ConsolidationEngine` - Automatic memory consolidation and optimization
- `MemoryCompressor` - Intelligent memory compression and archival
- `PatternExtractor` - Extract recurring patterns for optimization

## 🏗️ Architecture

### Core Architecture
```
omnimemory/
├── src/omnimemory/           # Core application code
│   ├── core/                 # Core memory interfaces and abstractions
│   ├── storage/             # Storage backends (PostgreSQL, Redis, Vector DBs)
│   ├── engines/             # Memory processing and retrieval engines
│   ├── consolidation/       # Memory consolidation and optimization
│   ├── security/           # Encryption and access control
│   ├── monitoring/         # Memory usage and performance monitoring
│   └── utils/              # Shared utilities and helpers
├── config/                  # Environment-specific configurations
├── scripts/                 # Setup and management scripts
└── tests/                  # Comprehensive test suites
```

### Memory Storage Stack
```
Storage Backends:
├── PostgreSQL (Persistent Memory & Metadata)
├── Redis (Ephemeral Memory & Caching)
├── Pinecone (Vector Memory & Semantic Search)
└── SQLAlchemy (ORM & Database Management)

Processing Engines:
├── Consolidation Engine (Memory Optimization)
├── Retrieval Engine (Smart Memory Access)
├── Similarity Engine (Semantic Matching)
└── Temporal Engine (Time-based Memory Management)
```

## 🐳 Docker Deployment

### Quick Start
```bash
# Development environment
cp .env.example .env
docker-compose --profile development up -d

# Production environment
export OMNIMEMORY_ENVIRONMENT=production
export PINECONE_API_KEY=your-api-key
docker-compose up -d

# Validate deployment
python scripts/validate_memory_systems.py --environment production
```

### Service Ports
- **8000**: OmniMemory API
- **5432**: PostgreSQL (Memory Storage)
- **6379**: Redis (Cache & Sessions)
- **5000**: Memory Management Dashboard

## 🧪 Testing & Quality

OmniMemory includes comprehensive test coverage with modern testing practices:

### Test Coverage
- **100% coverage** on critical modules (Core Memory, Vector Storage, Temporal Processing)
- **1,200+ lines** of high-quality test code with async patterns
- **Comprehensive edge case testing** including memory leak detection and performance validation

### Test Infrastructure
- **Async test patterns** using pytest-asyncio for realistic memory operations
- **Memory leak detection** with memory-profiler integration
- **Performance benchmarks** for memory retrieval and storage operations
- **Integration tests** for cross-system memory operations

### Running Tests
```bash
# Run all tests with coverage
poetry run pytest --cov=src --cov-report=term-missing

# Run memory-specific tests
poetry run pytest tests/test_vector_memory.py -v
poetry run pytest tests/test_temporal_memory.py -v
poetry run pytest tests/test_consolidation.py -v

# Run performance benchmarks
poetry run pytest tests/test_performance.py -v --benchmark
```

## 🎯 Memory Patterns

All memory systems follow advanced memory science principles:

- **Hierarchical Storage** - Multi-tier memory with automatic promotion/demotion
- **Temporal Decay** - Natural forgetting patterns with configurable decay rates
- **Consolidation** - Automatic memory consolidation during low-activity periods
- **Cross-Modal Integration** - Memory across text, embeddings, and structured data
- **Contextual Retrieval** - Context-aware memory retrieval with relevance scoring

## 🔧 Common Usage Patterns

### Memory Storage and Retrieval
```python
# Store complex memories with metadata
memory_manager.store_complex(
    content="Important technical decision",
    metadata={"project": "omnimemory", "importance": 0.9},
    embeddings=vector_embeddings,
    temporal_context={"created": datetime.now()}
)

# Retrieve with multi-modal search
results = memory_manager.search(
    query="technical decisions",
    include_semantic=True,
    include_temporal=True,
    max_results=10
)
```

### Temporal Memory Management
```python
# Set up temporal memory with decay
temporal_memory = TemporalMemory(
    decay_rate=0.1,          # 10% decay per day
    consolidation_threshold=0.5,
    max_age_days=365
)

# Store with temporal context
temporal_memory.store_with_context(
    "user_preference_change",
    context={"timestamp": now, "importance": 0.8}
)
```

### Memory Consolidation
```python
# Manual consolidation trigger
consolidation_engine = ConsolidationEngine()
consolidation_report = consolidation_engine.consolidate(
    memory_types=["vector", "temporal"],
    strategy="importance_based"
)

# Automatic consolidation scheduling
scheduler = MemoryScheduler()
scheduler.schedule_consolidation(
    frequency="daily",
    low_activity_hours=[2, 3, 4]  # 2-4 AM
)
```

## 📖 Documentation

### Core Documentation
- `MEMORY_ARCHITECTURE.md` - Memory system architecture and design principles
- `STORAGE_BACKENDS.md` - Storage backend configuration and optimization
- `CONSOLIDATION_STRATEGIES.md` - Memory consolidation algorithms and patterns
- `TEMPORAL_PATTERNS.md` - Time-based memory management and decay patterns
- `SECURITY_GUIDE.md` - Memory encryption and access control

### Integration Guides
- `INTEGRATION_GUIDE.md` - Integration with existing applications
- `PERFORMANCE_TUNING.md` - Memory system performance optimization
- `MONITORING_GUIDE.md` - Memory usage monitoring and alerting

## 🤝 Usage Examples

### Basic Memory Operations
```python
# Initialize memory manager
from omnimemory import MemoryManager
manager = MemoryManager()

# Store different types of memories
manager.store_text("Meeting notes from Q1 planning")
manager.store_structured({"decision": "use_postgres", "rationale": "scalability"})
manager.store_embedding(vector_data, metadata={"source": "user_feedback"})
```

### Advanced Memory Retrieval
```python
# Complex memory search
results = manager.advanced_search(
    query="database decisions",
    filters={
        "timeframe": "last_30_days",
        "importance": ">0.7",
        "project": "omnimemory"
    },
    ranking="hybrid",  # combine semantic + temporal + importance
    max_results=5
)

# Memory consolidation and cleanup
consolidation_results = manager.consolidate(
    strategy="pattern_based",
    preserve_important=True,
    compress_old=True
)
```

## 🛠️ Management Scripts

The `scripts/` directory contains:
- `init_memory.py` - Initialize memory storage systems
- `consolidate_memory.py` - Manual memory consolidation
- `export_memory.py` - Memory backup and export
- `import_memory.py` - Memory restoration and import
- `monitor_memory.py` - Memory usage monitoring

## 🚀 Future Development

This repository serves as the foundation for:
- **OmniMemory Cloud** - Hosted memory services for enterprise applications
- **Multi-Agent Memory** - Shared memory systems for agent collaboration
- **Memory Analytics** - Advanced analytics and insights from memory patterns
- **Federated Memory** - Distributed memory systems across multiple nodes

## 📄 License

[Add your license information here]

## 🤝 Contributing

When contributing to OmniMemory:

1. Follow memory system design patterns in `MEMORY_ARCHITECTURE.md`
2. Ensure proper test coverage for all memory operations
3. Include performance benchmarks for new memory features
4. Test memory leak scenarios and cleanup procedures

## 📞 Support

For issues, questions, or contributions:
- Open an issue in this repository
- Check the documentation in `docs/`
- Review memory architecture guides and troubleshooting

---

**Built with 🧠 for intelligent memory management**

*Enabling AI applications with human-like memory capabilities*
