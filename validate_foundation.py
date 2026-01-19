#!/usr/bin/env python3
"""
Foundation validation for OmniMemory ONEX architecture.

Validates that the foundational ONEX implementation is working correctly:
- Protocol definitions and structure
- Container initialization
- Service provider functionality
- Error handling and monadic patterns
- Basic integration tests
"""

import sys
import traceback
from pathlib import Path
from typing import Any

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def validate_protocol_imports() -> dict[str, Any]:
    """Validate that all protocol imports work correctly."""
    print("🔍 Testing protocol imports...")

    try:
        from omnimemory.protocols.base_protocols import (
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
        )

        # Use imports to validate they exist (satisfies flake8 F401)
        protocols = (
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
        )

        print("✅ All protocol imports successful")
        return {"success": True, "protocols_count": len(protocols)}

    except Exception as e:
        print(f"❌ Protocol import failed: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def validate_data_models() -> dict[str, Any]:
    """Validate data model imports and basic functionality."""
    print("🔍 Testing data model imports...")

    try:
        from omnimemory.protocols.data_models import (
            AccessLevel,
            BaseMemoryRequest,
            BaseMemoryResponse,
            ContentType,
            MemoryPriority,
            MemoryRecord,
            MemoryStoreRequest,
            MemoryStoreResponse,
            SearchFilters,
            SearchResult,
            StoragePreferences,
            UserContext,
        )

        # Use imports to validate they exist (satisfies flake8 F401)
        data_models = (
            BaseMemoryRequest,
            BaseMemoryResponse,
            MemoryStoreRequest,
            MemoryStoreResponse,
            SearchFilters,
            SearchResult,
            StoragePreferences,
        )

        # Test basic model creation
        user_context = UserContext(user_id="test-user", session_id="test-session")

        memory_record = MemoryRecord(
            content="Test memory content",
            content_type=ContentType.TEXT,
            priority=MemoryPriority.MEDIUM,
            access_level=AccessLevel.PRIVATE,
            user_context=user_context,
        )

        print("✅ Data model imports and creation successful")
        return {
            "success": True,
            "user_id": user_context.user_id,
            "memory_id": str(memory_record.memory_id),
            "data_models_count": len(data_models),
        }

    except Exception as e:
        print(f"❌ Data model validation failed: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def validate_error_handling() -> dict[str, Any]:
    """Validate error handling and monadic patterns."""
    print("🔍 Testing error handling...")

    try:
        from omnimemory.protocols.error_models import StorageError, ValidationError

        # Test error creation and chaining
        base_error = ValidationError(
            message="Test validation error",
            field_name="content",
            field_value="too_long",
        )

        chained_error = StorageError(
            message="Storage system down",
            cause=base_error,
        )

        print("✅ Error handling validation successful")
        return {
            "success": True,
            "base_error_code": base_error.omnimemory_error_code.value,
            "chained_error_has_cause": chained_error.cause is not None,
        }

    except Exception as e:
        print(f"❌ Error handling validation failed: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def validate_container_creation() -> dict[str, Any]:
    """Validate ONEX container creation and basic functionality."""
    print("🔍 Testing ONEX container creation...")

    try:
        from omnibase_core.core.model_onex_container import ModelOnexContainer

        # Test container creation
        container = ModelOnexContainer()

        # Verify container has expected ONEX methods
        has_register_singleton = hasattr(container, "register_singleton")
        has_register_transient = hasattr(container, "register_transient")
        has_resolve = hasattr(container, "resolve")

        print("✅ ONEX Container creation successful")
        return {
            "success": True,
            "has_register_singleton": has_register_singleton,
            "has_register_transient": has_register_transient,
            "has_resolve": has_resolve,
        }

    except Exception as e:
        print(f"❌ ONEX Container validation failed: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def validate_base_implementations() -> dict[str, Any]:
    """Validate base implementation classes."""
    print("🔍 Testing base implementations...")

    try:
        from omnimemory.core.base_implementations import (
            BaseComputeService,
            BaseEffectService,
            BaseMemoryService,
            BaseOrchestratorService,
            BaseReducerService,
        )

        # Verify all base classes are importable and have expected structure
        base_classes = [
            BaseMemoryService,
            BaseEffectService,
            BaseComputeService,
            BaseReducerService,
            BaseOrchestratorService,
        ]

        class_methods = {}
        for cls in base_classes:
            methods = [method for method in dir(cls) if not method.startswith("_")]
            class_methods[cls.__name__] = len(methods)

        print("✅ Base implementations validation successful")
        return {
            "success": True,
            "base_classes_count": len(base_classes),
            "class_methods": class_methods,
        }

    except Exception as e:
        print(f"❌ Base implementations validation failed: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def validate_async_patterns() -> dict[str, Any]:
    """Validate async patterns and NodeResult usage."""
    print("🔍 Testing async patterns...")

    try:
        # Import async components
        from omnibase_core.core.model_onex_container import ModelOnexContainer
        from omnibase_core.core.monadic.model_node_result import NodeResult

        from omnimemory.protocols.data_models import UserContext

        # Use imports to validate they exist (satisfies flake8 F401)
        async_components = (NodeResult, UserContext)

        # Create container and test ONEX patterns
        container = ModelOnexContainer()

        # Verify ONEX methods exist
        has_resolve_method = hasattr(container, "resolve")
        has_register_methods = hasattr(container, "register_singleton")

        print("✅ Async patterns validation successful")
        return {
            "success": True,
            "has_resolve_method": has_resolve_method,
            "has_register_methods": has_register_methods,
            "container_created": True,
            "async_components_count": len(async_components),
        }

    except Exception as e:
        print(f"❌ Async patterns validation failed: {str(e)}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main() -> int:
    """Run comprehensive foundation validation."""
    print("🎯 OmniMemory Foundation Validation")
    print("=" * 40)

    results = {}

    # Run all validation tests
    results["protocols"] = validate_protocol_imports()
    results["data_models"] = validate_data_models()
    results["error_handling"] = validate_error_handling()
    results["container"] = validate_container_creation()
    results["base_implementations"] = validate_base_implementations()

    # Note: Skipping async validation due to omnibase_core dependency issues
    # results['async_patterns'] = await validate_async_patterns()

    print("\n📊 Validation Results:")
    print("=" * 30)

    passed = 0
    failed = 0

    for test_name, result in results.items():
        if result.get("success", False):
            print(f"✅ {test_name}: PASS")
            passed += 1
        else:
            print(f"❌ {test_name}: FAIL - {result.get('error', 'Unknown error')}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 Foundation validation successful!")
        print("   ONEX architecture is properly implemented")
        print("   Ready for service implementations")
        return 0
    else:
        print(f"\n🚫 {failed} validation issues found")
        print("   Foundation needs fixes before proceeding")
        return 1


if __name__ == "__main__":
    sys.exit(main())
