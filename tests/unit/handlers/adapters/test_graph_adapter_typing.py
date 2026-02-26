# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""AST-based boundary test: graph adapters must not import HandlerGraph directly.

This test enforces the architectural boundary that omnimemory graph adapters
type against ``ProtocolGraphDatabaseHandler`` from ``omnibase_spi`` rather than
importing the concrete ``HandlerGraph`` class from ``omnibase_infra`` at module
level.

The concrete class should only be resolved at runtime via ``importlib`` inside
a factory function, not via a top-level ``from omnibase_infra.handlers...``
import statement.

Ticket: OMN-2815 (GAP-003)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Adapter source files under test
_ADAPTERS_DIR = (
    Path(__file__).resolve().parents[4] / "src" / "omnimemory" / "handlers" / "adapters"
)

_ADAPTER_FILES = [
    _ADAPTERS_DIR / "adapter_graph_memory.py",
    _ADAPTERS_DIR / "adapter_intent_graph.py",
]

# Banned import pattern: direct import of HandlerGraph from omnibase_infra
_BANNED_MODULE = "omnibase_infra.handlers.handler_graph"
_BANNED_NAME = "HandlerGraph"


def _collect_top_level_imports(tree: ast.Module) -> list[tuple[int, str, str]]:
    """Collect top-level import statements that import HandlerGraph from omnibase_infra.

    Only inspects top-level statements (not nested inside functions/classes)
    to allow importlib-based lazy resolution inside factory functions.

    Returns:
        List of (line_number, module_path, imported_name) tuples for violations.
    """
    violations: list[tuple[int, str, str]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == _BANNED_MODULE or module.startswith(
                "omnibase_infra.handlers.handler_graph."
            ):
                for alias in node.names:
                    if alias.name == _BANNED_NAME:
                        violations.append((node.lineno, module, alias.name))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == _BANNED_MODULE:
                    violations.append((node.lineno, alias.name, _BANNED_NAME))
    return violations


@pytest.mark.unit
class TestGraphAdapterBoundary:
    """Verify that graph adapter files do not directly import HandlerGraph."""

    @pytest.mark.parametrize(
        "adapter_path",
        _ADAPTER_FILES,
        ids=[p.name for p in _ADAPTER_FILES],
    )
    def test_no_direct_handler_graph_import(self, adapter_path: Path) -> None:
        """Adapter must not have a top-level import of HandlerGraph from omnibase_infra."""
        assert adapter_path.exists(), f"Adapter file not found: {adapter_path}"

        source = adapter_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(adapter_path))
        violations = _collect_top_level_imports(tree)

        if violations:
            details = "\n".join(
                f"  line {line}: from {mod} import {name}"
                for line, mod, name in violations
            )
            pytest.fail(
                f"Direct HandlerGraph import found in {adapter_path.name}.\n"
                f"Adapters must type against ProtocolGraphDatabaseHandler "
                f"from omnibase_spi.\n"
                f"Violations:\n{details}"
            )

    @pytest.mark.parametrize(
        "adapter_path",
        _ADAPTER_FILES,
        ids=[p.name for p in _ADAPTER_FILES],
    )
    def test_uses_protocol_graph_database_handler(self, adapter_path: Path) -> None:
        """Adapter must import ProtocolGraphDatabaseHandler from omnibase_spi."""
        assert adapter_path.exists(), f"Adapter file not found: {adapter_path}"

        source = adapter_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(adapter_path))

        found = False
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if (
                    "omnibase_spi" in module
                    and "protocol_graph_database_handler" in module
                ):
                    for alias in node.names:
                        if alias.name == "ProtocolGraphDatabaseHandler":
                            found = True
                            break

        assert found, (
            f"{adapter_path.name} does not import ProtocolGraphDatabaseHandler "
            f"from omnibase_spi. Adapters must type against the SPI protocol."
        )

    @pytest.mark.parametrize(
        "adapter_path",
        _ADAPTER_FILES,
        ids=[p.name for p in _ADAPTER_FILES],
    )
    def test_has_importlib_factory(self, adapter_path: Path) -> None:
        """Adapter must use importlib for lazy concrete class resolution."""
        source = adapter_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(adapter_path))

        has_importlib_import = False
        has_factory_function = False

        for node in ast.iter_child_nodes(tree):
            # Check for importlib import
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "importlib":
                        has_importlib_import = True
            # Check for _create_graph_handler function
            if (
                isinstance(node, ast.FunctionDef)
                and node.name == "_create_graph_handler"
            ):
                has_factory_function = True

        assert has_importlib_import, (
            f"{adapter_path.name} does not import importlib. "
            f"Concrete handler resolution must use importlib."
        )
        assert has_factory_function, (
            f"{adapter_path.name} does not define _create_graph_handler(). "
            f"Concrete handler resolution must happen in a factory function."
        )
