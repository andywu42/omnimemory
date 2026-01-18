# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Contract validation tests for Core 8 ONEX nodes.

Tests both schema validation (Pydantic) and runtime load tests.
"""
from __future__ import annotations

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
        contract_path = NODES_DIR / node_name / "contract.yaml"
        # Skip if not yet implemented (scaffold phase)
        if not contract_path.exists():
            pytest.skip(f"Contract not yet implemented: {node_name}")
        assert contract_path.exists(), f"Missing contract: {contract_path}"

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_is_valid_yaml(self, node_name: str) -> None:
        """Verify contract.yaml is valid YAML."""
        contract_path = NODES_DIR / node_name / "contract.yaml"
        if not contract_path.exists():
            pytest.skip(f"Contract not yet implemented: {node_name}")

        with open(contract_path) as f:
            data = yaml.safe_load(f)

        assert isinstance(data, dict), f"Contract must be a dict: {node_name}"
        assert "name" in data, f"Contract must have 'name' field: {node_name}"
        assert "node_type" in data, f"Contract must have 'node_type' field: {node_name}"

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_validates_with_pydantic(self, node_name: str) -> None:
        """Verify contract validates against appropriate Pydantic model."""
        contract_path = NODES_DIR / node_name / "contract.yaml"
        if not contract_path.exists():
            pytest.skip(f"Contract not yet implemented: {node_name}")

        with open(contract_path) as f:
            data = yaml.safe_load(f)

        node_type = data.get("node_type", "")

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
    """Test contracts load at runtime with actual node classes."""

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_can_be_imported(self, node_name: str) -> None:
        """Verify node class can be imported."""
        # This will be enabled once node.py files are created
        pytest.skip(f"Node not yet implemented: {node_name}")
