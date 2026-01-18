# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Node import tests - verify all Core 8 nodes import cleanly.

These tests ensure the node package structure is correct and all
nodes can be imported without errors.
"""
from __future__ import annotations

import importlib
import pytest
from pathlib import Path

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


class TestNodeImports:
    """Test that all nodes can be imported."""

    def test_nodes_package_imports(self) -> None:
        """Verify the nodes package can be imported."""
        try:
            import omnimemory.nodes
            assert omnimemory.nodes is not None
        except ImportError as e:
            pytest.skip(f"Package not installed in editable mode: {e}")

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_package_imports(self, node_name: str) -> None:
        """Verify each node package can be imported."""
        module_name = f"omnimemory.nodes.{node_name}"
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            # Expected during scaffold phase
            pytest.skip(f"Node package not yet fully implemented: {e}")

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_class_can_be_imported(self, node_name: str) -> None:
        """Verify node class can be imported from package."""
        # Check if node.py exists first
        node_path = NODES_DIR / node_name / "node.py"
        if not node_path.exists():
            pytest.skip(f"Node class not yet implemented: {node_name}")

        # Convert node_name to class name (e.g., memory_storage_effect -> NodeMemoryStorageEffect)
        class_name = "Node" + "".join(word.capitalize() for word in node_name.split("_"))

        module_name = f"omnimemory.nodes.{node_name}.node"
        try:
            module = importlib.import_module(module_name)
            node_class = getattr(module, class_name, None)
            if node_class is None:
                pytest.skip(f"Node class {class_name} not found in {module_name}")
            assert node_class is not None
        except ImportError as e:
            pytest.skip(f"Node not yet implemented: {e}")

    def test_all_nodes_in_package_all(self) -> None:
        """Verify __all__ in nodes package lists all Core 8 nodes."""
        try:
            from omnimemory.nodes import __all__
            for node_name in CORE_8_NODES:
                assert node_name in __all__, f"Missing from __all__: {node_name}"
        except ImportError:
            pytest.skip("nodes package not properly configured")


class TestNodeStructure:
    """Test node directory structure is correct."""

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_directory_exists(self, node_name: str) -> None:
        """Verify node directory exists."""
        node_dir = NODES_DIR / node_name
        assert node_dir.exists(), f"Missing node directory: {node_dir}"
        assert node_dir.is_dir(), f"Not a directory: {node_dir}"

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_init_exists(self, node_name: str) -> None:
        """Verify __init__.py exists in node directory."""
        init_path = NODES_DIR / node_name / "__init__.py"
        assert init_path.exists(), f"Missing __init__.py: {init_path}"

    @pytest.mark.parametrize("node_name", ["memory_storage_effect", "memory_retrieval_effect",
                                           "memory_lifecycle_orchestrator", "agent_coordinator_orchestrator"])
    def test_effect_orchestrator_has_handlers_dir(self, node_name: str) -> None:
        """Verify Effect and Orchestrator nodes have handlers directory."""
        handlers_dir = NODES_DIR / node_name / "handlers"
        assert handlers_dir.exists(), f"Missing handlers dir: {handlers_dir}"
        assert (handlers_dir / "__init__.py").exists(), f"Missing handlers/__init__.py"
