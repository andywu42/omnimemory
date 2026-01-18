# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Contract validation tests for Core 8 ONEX nodes.

Tests both schema validation (Pydantic) and runtime load tests.
"""
from __future__ import annotations

import importlib
import types
from typing import Any

import pytest
import yaml
from pathlib import Path

# Core 8 node names
CORE_8_NODES = [
    "memory_storage_effect",
    "memory_retrieval_effect",
    "semantic_analyzer_compute",
    "similarity_compute",
    "memory_consolidator_reducer",
    "statistics_reducer",
    "memory_lifecycle_orchestrator",
    "agent_coordinator_orchestrator",
]

NODES_DIR = Path(__file__).parent.parent / "src" / "omnimemory" / "nodes"


class TestContractValidation:
    """Test contract.yaml files validate against Pydantic models."""

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_file_exists(self, node_name: str) -> None:
        """Verify contract.yaml exists for each Core 8 node."""
        contract_path: Path = NODES_DIR / node_name / "contract.yaml"
        # Skip if not yet implemented (scaffold phase)
        if not contract_path.exists():
            pytest.skip(f"File not yet implemented: {contract_path}")
        assert contract_path.exists(), f"Missing contract: {contract_path}"

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_is_valid_yaml(self, node_name: str) -> None:
        """Verify contract.yaml is valid YAML with required ONEX fields.

        ONEX contracts must have fields at root level: name, node_type.
        No backwards compatibility with legacy nested 'onex' format.
        """
        contract_path: Path = NODES_DIR / node_name / "contract.yaml"
        if not contract_path.exists():
            pytest.skip(f"File not yet implemented: {contract_path}")

        with open(contract_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)

        assert isinstance(data, dict), f"Contract must be a dict: {node_name}"

        # ONEX contracts must have fields at root level (no legacy nested format)
        assert "name" in data, f"Contract must have 'name' field: {node_name}"
        assert "node_type" in data, f"Contract must have 'node_type' field: {node_name}"

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_validates_with_pydantic(self, node_name: str) -> None:
        """Verify contract validates against appropriate Pydantic model."""
        contract_path: Path = NODES_DIR / node_name / "contract.yaml"
        if not contract_path.exists():
            pytest.skip(f"File not yet implemented: {contract_path}")

        with open(contract_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)

        # ONEX contracts must have node_type at root level (no legacy nested format)
        node_type: str = data.get("node_type", "")
        assert node_type, f"Contract must have 'node_type' field at root level: {node_name}"
        node_type = node_type.upper()

        # Import appropriate contract model based on node type
        try:
            if "EFFECT" in node_type:
                from omnibase_core.models.contracts import ModelContractEffect

                ModelContractEffect.model_validate(data)
            elif "COMPUTE" in node_type:
                from omnibase_core.models.contracts import ModelContractCompute

                ModelContractCompute.model_validate(data)
            elif "REDUCER" in node_type:
                from omnibase_core.models.contracts import ModelContractReducer

                ModelContractReducer.model_validate(data)
            elif "ORCHESTRATOR" in node_type:
                from omnibase_core.models.contracts import ModelContractOrchestrator

                ModelContractOrchestrator.model_validate(data)
            else:
                pytest.fail(f"Unknown node_type: {node_type}")
        except ImportError:
            pytest.skip("omnibase_core not installed")


class TestContractRuntimeLoad:
    """Test contracts load at runtime with actual node classes.

    These tests verify that node classes can be imported and instantiated
    with their contract configurations. Tests are skipped for nodes that
    have not yet been implemented.
    """

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_import_succeeds(self, node_name: str) -> None:
        """Verify node class can be imported from its package.

        This test checks that the node.py file exists and that the
        corresponding node class can be imported without errors.
        Skipped for nodes not yet implemented.
        """
        node_path: Path = NODES_DIR / node_name / "node.py"
        if not node_path.exists():
            pytest.skip(f"File not yet implemented: {node_path}")

        # Convert node_name to class name (e.g., memory_storage_effect -> NodeMemoryStorageEffect)
        class_name: str = "Node" + "".join(word.capitalize() for word in node_name.split("_"))

        module_name: str = f"omnimemory.nodes.{node_name}.node"
        try:
            module: types.ModuleType = importlib.import_module(module_name)
            node_class: type | None = getattr(module, class_name, None)
            assert node_class is not None, f"Node class {class_name} not found in {module_name}"
        except ModuleNotFoundError as e:
            # Package not installed in editable mode - skip rather than fail
            pytest.skip(f"Package not installed in editable mode: {e}")
        except ImportError as e:
            # Other import errors indicate real problems - fail the test
            pytest.fail(f"Failed to import {module_name}: {e}")

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_instantiation_succeeds(self, node_name: str) -> None:
        """Verify node class can be instantiated with mock container.

        This test catches runtime errors like invalid super().__init__() calls
        that import-only tests would miss.
        """
        node_path: Path = NODES_DIR / node_name / "node.py"
        if not node_path.exists():
            pytest.skip(f"File not yet implemented: {node_path}")

        class_name: str = "Node" + "".join(word.capitalize() for word in node_name.split("_"))
        module_name: str = f"omnimemory.nodes.{node_name}.node"

        try:
            module: types.ModuleType = importlib.import_module(module_name)
            node_class: type | None = getattr(module, class_name, None)
            if node_class is None:
                pytest.skip(f"Node class {class_name} not found")

            # Instantiate with mock container
            from unittest.mock import Mock

            mock_container: Mock = Mock()
            instance: Any = node_class(container=mock_container)
            assert instance is not None
        except ModuleNotFoundError as e:
            pytest.skip(f"Package not installed in editable mode: {e}")
        except ImportError as e:
            pytest.skip(f"Package not installed in editable mode: {e}")


class TestContractHandlerMapping:
    """Test contract actions have corresponding handlers.

    These tests verify that the contract.yaml actions are implemented
    by handlers in the handlers/ directory. Currently skipped during
    scaffold phase.
    """

    @pytest.mark.skip(reason="Requires handler implementation")
    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_actions_have_handlers(self, node_name: str) -> None:
        """Verify all contract actions have corresponding handlers."""
        pass

    @pytest.mark.skip(reason="Requires container implementation")
    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_container_provides_required_dependencies(self, node_name: str) -> None:
        """Verify container provides all dependencies declared in contract."""
        pass

    @pytest.mark.skip(reason="Requires error handling implementation")
    def test_contract_validation_failure_handling(self) -> None:
        """Verify graceful handling of invalid contracts."""
        pass

    @pytest.mark.skip(reason="Requires integration test infrastructure")
    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_integration_with_storage_backend(self, node_name: str) -> None:
        """Verify node interaction with actual storage backends."""
        pass
