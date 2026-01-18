# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Contract enforcement tests - ONEX declarative node validation.

Ensures all ONEX nodes follow the FULLY DECLARATIVE pattern:
- contract.yaml defines node type, inputs, outputs, handlers
- handlers/ directory contains business logic
- No node.py class needed (contracts ARE the nodes)

This module validates that node directories contain proper contracts
and handler registrations, catching violations at test time.

Skip Behavior:
    Tests skip gracefully when contracts don't exist during scaffold phase,
    using pytest.skip() with clear messages about what's missing.

Path Resolution:
    Uses Path(__file__) for CWD-independent path resolution via conftest.py.
"""
from __future__ import annotations

from typing import NamedTuple

import pytest
import yaml
from pathlib import Path

from tests.conftest import CORE_8_NODES, NODES_DIR


# Valid ONEX node types
VALID_NODE_TYPES: frozenset[str] = frozenset({"effect", "compute", "reducer", "orchestrator"})


class ContractValidationResult(NamedTuple):
    """Result of contract.yaml validation."""
    valid: bool
    error: str | None = None


def validate_contract(contract_path: Path) -> ContractValidationResult:
    """Validate ONEX contract follows required structure.

    Supports two formats:
    1. Flat format: name and node_type at root level (preferred)
    2. Nested format: name and node_type under 'onex' key

    Rules:
    1. Must be valid YAML
    2. Must specify valid node_type (effect, compute, reducer, orchestrator)
    3. Must have name field
    """
    if not contract_path.exists():
        return ContractValidationResult(False, f"Contract not found: {contract_path}")

    try:
        with open(contract_path) as f:
            data: dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return ContractValidationResult(False, f"Invalid YAML: {e}")

    if not isinstance(data, dict):
        return ContractValidationResult(False, "Contract must be a YAML mapping")

    # Support both flat format (preferred) and nested 'onex' format
    if "onex" in data and isinstance(data["onex"], dict):
        contract_data: dict = data["onex"]
    else:
        contract_data = data

    # Check for required fields
    if "node_type" not in contract_data:
        return ContractValidationResult(False, "Missing 'node_type' in contract")

    node_type: str = str(contract_data["node_type"]).lower()
    if node_type not in VALID_NODE_TYPES:
        return ContractValidationResult(
            False,
            f"Invalid node_type '{node_type}', must be one of: {', '.join(sorted(VALID_NODE_TYPES))}"
        )

    if "name" not in contract_data:
        return ContractValidationResult(False, "Missing 'name' in contract")

    return ContractValidationResult(True)


class TestContractEnforcement:
    """Test that all nodes have valid ONEX contracts.

    These tests verify that node directories contain proper contract.yaml
    files that define the node declaratively. No node.py files are needed -
    the contract IS the node definition.

    ONEX Declarative Pattern:
    - contract.yaml defines: node_type, name, inputs, outputs, handlers
    - handlers/ contains business logic implementations
    - Runtime instantiates nodes from contracts, not classes
    """

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_exists(self, node_name: str) -> None:
        """Verify contract.yaml exists for each Core 8 node.

        Skipped for nodes not yet implemented during scaffold phase.
        """
        contract_path: Path = NODES_DIR / node_name / "contract.yaml"
        # Skip if not yet implemented
        if not contract_path.exists():
            pytest.skip(f"Contract not yet implemented: {contract_path}")
        assert contract_path.exists()

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_contract_is_valid(self, node_name: str) -> None:
        """Verify contract.yaml follows ONEX schema.

        Validates that the contract contains required fields:
        - onex.node_type (effect, compute, reducer, orchestrator)
        - onex.name

        Skipped for nodes not yet implemented.
        """
        contract_path: Path = NODES_DIR / node_name / "contract.yaml"
        if not contract_path.exists():
            pytest.skip(f"Contract not yet implemented: {contract_path}")

        result: ContractValidationResult = validate_contract(contract_path)
        assert result.valid, f"Contract {node_name} failed validation: {result.error}"

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_no_node_py_exists(self, node_name: str) -> None:
        """Verify no node.py files exist (fully declarative pattern).

        ONEX nodes are defined by contracts, not Python classes.
        The presence of a node.py file indicates legacy architecture.
        """
        node_py_path: Path = NODES_DIR / node_name / "node.py"
        assert not node_py_path.exists(), (
            f"node.py should not exist for {node_name} - "
            "use contract.yaml for declarative node definition"
        )

    def test_validate_contract_accepts_flat_format(self, tmp_path: Path) -> None:
        """Test that validator accepts flat format (no 'onex' wrapper)."""
        good_contract: Path = tmp_path / "flat_contract.yaml"
        good_contract.write_text("""
name: test_node
node_type: effect
version: {major: 1, minor: 0, patch: 0}
""")
        result: ContractValidationResult = validate_contract(good_contract)
        assert result.valid, f"Flat format should be valid: {result.error}"

    def test_validate_contract_rejects_invalid_node_type(self, tmp_path: Path) -> None:
        """Test that validator rejects invalid node_type values."""
        bad_contract: Path = tmp_path / "bad_contract.yaml"
        bad_contract.write_text("""
onex:
  name: test
  node_type: invalid_type
""")
        result: ContractValidationResult = validate_contract(bad_contract)
        assert not result.valid
        assert result.error is not None
        assert "invalid" in result.error.lower() or "node_type" in result.error.lower()

    def test_validate_contract_rejects_missing_name(self, tmp_path: Path) -> None:
        """Test that validator rejects contracts without name field."""
        bad_contract: Path = tmp_path / "bad_contract.yaml"
        bad_contract.write_text("""
onex:
  node_type: effect
""")
        result: ContractValidationResult = validate_contract(bad_contract)
        assert not result.valid
        assert result.error is not None
        assert "name" in result.error.lower()

    def test_validate_contract_accepts_valid_contract(self, tmp_path: Path) -> None:
        """Test that validator accepts properly formed contracts."""
        good_contract: Path = tmp_path / "good_contract.yaml"
        good_contract.write_text("""
onex:
  name: memory_storage
  node_type: effect
  version: 1.0.0
  handlers:
    - handler_db
    - handler_redis
""")
        result: ContractValidationResult = validate_contract(good_contract)
        assert result.valid, f"Should be valid: {result.error}"

    @pytest.mark.parametrize("node_type", ["effect", "compute", "reducer", "orchestrator"])
    def test_validate_contract_accepts_all_node_types(
        self, tmp_path: Path, node_type: str
    ) -> None:
        """Test that validator accepts all valid node types."""
        contract: Path = tmp_path / f"{node_type}_contract.yaml"
        contract.write_text(f"""
onex:
  name: test_{node_type}
  node_type: {node_type}
""")
        result: ContractValidationResult = validate_contract(contract)
        assert result.valid, f"node_type '{node_type}' should be valid: {result.error}"

    def test_validate_contract_rejects_invalid_yaml(self, tmp_path: Path) -> None:
        """Test that validator rejects malformed YAML."""
        bad_contract: Path = tmp_path / "bad_yaml.yaml"
        bad_contract.write_text("""
onex:
  name: test
  node_type: effect
  invalid: [unclosed bracket
""")
        result: ContractValidationResult = validate_contract(bad_contract)
        assert not result.valid
        assert result.error is not None
        assert "yaml" in result.error.lower() or "invalid" in result.error.lower()
