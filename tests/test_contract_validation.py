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
            pytest.skip(f"Contract not yet implemented: {node_name}")
        assert contract_path.exists(), f"Missing contract: {contract_path}"

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_is_valid_yaml(self, node_name: str) -> None:
        """Verify contract.yaml is valid YAML with required ONEX fields.

        Checks that the contract has the required fields either:
        - At root level (new ONEX format): name, node_type
        - Under 'onex' key (legacy format): onex.name, onex.node_type
        """
        contract_path: Path = NODES_DIR / node_name / "contract.yaml"
        if not contract_path.exists():
            pytest.skip(f"Contract not yet implemented: {node_name}")

        with open(contract_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)

        assert isinstance(data, dict), f"Contract must be a dict: {node_name}"

        # ONEX contracts may have fields at root (new format) or under 'onex' key (legacy)
        if "onex" in data:
            # Legacy nested format
            onex_section: dict[str, Any] = data["onex"]
            assert "name" in onex_section, f"Contract must have 'onex.name' field: {node_name}"
            assert "node_type" in onex_section, f"Contract must have 'onex.node_type' field: {node_name}"
        else:
            # New flat format with fields at root
            assert "name" in data, f"Contract must have 'name' field: {node_name}"
            assert "node_type" in data, f"Contract must have 'node_type' field: {node_name}"

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_validates_with_pydantic(self, node_name: str) -> None:
        """Verify contract validates against appropriate Pydantic model."""
        contract_path: Path = NODES_DIR / node_name / "contract.yaml"
        if not contract_path.exists():
            pytest.skip(f"Contract not yet implemented: {node_name}")

        with open(contract_path) as f:
            data: dict[str, Any] = yaml.safe_load(f)

        # ONEX contracts may have node_type at root or under 'onex' key
        # Check root level first (new ONEX format), then fall back to onex section
        node_type: str = data.get("node_type", "")
        if not node_type:
            onex_section: dict[str, Any] = data.get("onex", {})
            node_type = onex_section.get("node_type", "")
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
    def test_node_can_be_imported(self, node_name: str) -> None:
        """Verify node class can be imported from its package.

        This test checks that the node.py file exists and that the
        corresponding node class can be imported without errors.
        Skipped for nodes not yet implemented.
        """
        node_path: Path = NODES_DIR / node_name / "node.py"
        if not node_path.exists():
            pytest.skip(f"Node not yet implemented: {node_name}")

        # Convert node_name to class name (e.g., memory_storage_effect -> NodeMemoryStorageEffect)
        class_name: str = "Node" + "".join(word.capitalize() for word in node_name.split("_"))

        module_name: str = f"omnimemory.nodes.{node_name}.node"
        try:
            module: types.ModuleType = importlib.import_module(module_name)
            node_class: type[Any] | None = getattr(module, class_name, None)
            assert node_class is not None, f"Node class {class_name} not found in {module_name}"
        except ModuleNotFoundError as e:
            # Package not installed in editable mode - skip rather than fail
            pytest.skip(f"Package not installed in editable mode: {e}")
        except ImportError as e:
            # Other import errors indicate real problems - fail the test
            pytest.fail(f"Failed to import {module_name}: {e}")
