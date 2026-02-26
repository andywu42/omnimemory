# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""AST-based boundary enforcement for handler_subscription.py (OMN-2816).

Verifies that ``handler_subscription.py`` does NOT import ``HandlerDb``
directly from ``omnibase_infra``.  The concrete class must be resolved
lazily via ``importlib`` through the local ``_DbHandlerProtocol`` /
``_create_db_handler()`` pattern introduced in GAP-002.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Path to the module under test (resolved relative to repo root).
_HANDLER_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "omnimemory"
    / "handlers"
    / "handler_subscription.py"
)


@pytest.mark.unit
class TestNoDirectHandlerDbImport:
    """Ensure handler_subscription.py never imports HandlerDb at module level."""

    def _parse_tree(self) -> ast.Module:
        source = _HANDLER_PATH.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(_HANDLER_PATH))

    def test_no_from_import_handler_db(self) -> None:
        """No ``from omnibase_infra.handlers.handler_db import HandlerDb``."""
        tree = self._parse_tree()
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module == "omnibase_infra.handlers.handler_db":
                    names = [alias.name for alias in node.names]
                    violations.append(
                        f"Line {node.lineno}: from {node.module} import {', '.join(names)}"
                    )
        assert violations == [], (
            "Direct import of HandlerDb from omnibase_infra detected. "
            "Use the local _DbHandlerProtocol and _create_db_handler() factory instead.\n"
            + "\n".join(violations)
        )

    def test_no_bare_import_handler_db_module(self) -> None:
        """No ``import omnibase_infra.handlers.handler_db``."""
        tree = self._parse_tree()
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("omnibase_infra.handlers.handler_db"):
                        violations.append(f"Line {node.lineno}: import {alias.name}")
        assert violations == [], (
            "Direct import of handler_db module from omnibase_infra detected.\n"
            + "\n".join(violations)
        )

    def test_protocol_class_exists(self) -> None:
        """Verify ``_DbHandlerProtocol`` is defined as a class in the module."""
        tree = self._parse_tree()
        protocol_classes = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == "_DbHandlerProtocol"
        ]
        assert len(protocol_classes) == 1, (
            "_DbHandlerProtocol class must be defined in handler_subscription.py"
        )

    def test_factory_function_exists(self) -> None:
        """Verify ``_create_db_handler`` factory function is defined."""
        tree = self._parse_tree()
        factory_funcs = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_create_db_handler"
        ]
        assert len(factory_funcs) == 1, (
            "_create_db_handler factory must be defined in handler_subscription.py"
        )

    def test_importlib_used_for_lazy_resolution(self) -> None:
        """Verify ``importlib`` is imported (required for lazy class resolution)."""
        tree = self._parse_tree()
        has_importlib = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "importlib":
                        has_importlib = True
            elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
                has_importlib = True
        assert has_importlib, "importlib must be imported for lazy HandlerDb resolution"
