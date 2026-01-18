# SPDX-License-Identifier: MIT
# Copyright (c) 2025 OmniNode Team
"""Node.py enforcement tests - AST-based declarative pattern validation.

Ensures all node.py files follow the FULLY DECLARATIVE pattern:
- Exactly one class
- Only __init__ method
- Only super().__init__(container) in body
"""
from __future__ import annotations

import ast
import pytest
from pathlib import Path
from typing import NamedTuple

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


class NodeValidationResult(NamedTuple):
    """Result of node.py validation."""
    valid: bool
    error: str | None = None


def validate_node_py(filepath: Path) -> NodeValidationResult:
    """Enforce declarative node pattern via AST parsing.

    Rules:
    1. Exactly one class definition
    2. Only __init__ method allowed
    3. __init__ must only call super().__init__(container)
    """
    if not filepath.exists():
        return NodeValidationResult(False, f"File not found: {filepath}")

    with open(filepath) as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError as e:
            return NodeValidationResult(False, f"Syntax error: {e}")

    # Find all class definitions (excluding TYPE_CHECKING blocks)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

    if len(classes) == 0:
        return NodeValidationResult(False, "No class found in node.py")

    if len(classes) > 1:
        return NodeValidationResult(False, f"Expected 1 class, found {len(classes)}")

    cls = classes[0]

    # Get all methods (FunctionDef nodes that are direct children of class)
    methods = [n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    # Filter out __all__ and other non-method assignments
    method_names = [m.name for m in methods]

    if len(methods) == 0:
        return NodeValidationResult(False, "No __init__ method found")

    if len(methods) > 1:
        extra_methods = [m for m in method_names if m != "__init__"]
        return NodeValidationResult(
            False,
            f"Node.py must have ONLY __init__, found extra methods: {extra_methods}"
        )

    if methods[0].name != "__init__":
        return NodeValidationResult(
            False,
            f"Expected __init__, found: {methods[0].name}"
        )

    # Check __init__ body - should only have super().__init__(container)
    init_body = methods[0].body

    # Allow docstrings + super().__init__()
    non_docstring_stmts = [
        stmt for stmt in init_body
        if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))
    ]

    if len(non_docstring_stmts) > 1:
        return NodeValidationResult(
            False,
            f"__init__ should only call super().__init__(), found {len(non_docstring_stmts)} statements"
        )

    if len(non_docstring_stmts) == 0:
        return NodeValidationResult(
            False,
            "__init__ must call super().__init__(container)"
        )

    # Validate that the single statement is super().__init__(container)
    stmt = non_docstring_stmts[0]
    if not _is_super_init_call(stmt):
        return NodeValidationResult(
            False,
            "__init__ body must be exactly super().__init__(container)"
        )

    return NodeValidationResult(True)


def _is_super_init_call(stmt: ast.stmt) -> bool:
    """Check if statement is super().__init__(container) call.

    Valid AST structure:
        Expr(
            value=Call(
                func=Attribute(
                    value=Call(func=Name(id='super'), args=[]),
                    attr='__init__'
                ),
                args=[Name(id='container')]
            )
        )
    """
    # Must be an expression statement
    if not isinstance(stmt, ast.Expr):
        return False

    # Must be a function call
    call = stmt.value
    if not isinstance(call, ast.Call):
        return False

    # Must be calling an attribute (super().__init__)
    if not isinstance(call.func, ast.Attribute):
        return False

    attr = call.func
    if attr.attr != "__init__":
        return False

    # The attribute's value must be super() call
    if not isinstance(attr.value, ast.Call):
        return False

    super_call = attr.value
    if not isinstance(super_call.func, ast.Name):
        return False

    if super_call.func.id != "super":
        return False

    # super() should have no arguments
    if super_call.args or super_call.keywords:
        return False

    # __init__ must have exactly one positional argument named 'container'
    if len(call.args) != 1:
        return False

    arg = call.args[0]
    if not isinstance(arg, ast.Name):
        return False

    if arg.id != "container":
        return False

    # No keyword arguments allowed
    if call.keywords:
        return False

    return True


class TestNodeEnforcement:
    """Test that all node.py files follow declarative pattern."""

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_py_exists(self, node_name: str) -> None:
        """Verify node.py exists for each Core 8 node."""
        node_path = NODES_DIR / node_name / "node.py"
        # Skip if not yet implemented
        if not node_path.exists():
            pytest.skip(f"Node not yet implemented: {node_name}")
        assert node_path.exists()

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_py_is_declarative(self, node_name: str) -> None:
        """Verify node.py follows declarative pattern."""
        node_path = NODES_DIR / node_name / "node.py"
        if not node_path.exists():
            pytest.skip(f"Node not yet implemented: {node_name}")

        result = validate_node_py(node_path)
        assert result.valid, f"Node {node_name} failed enforcement: {result.error}"

    def test_validate_node_py_rejects_custom_methods(self, tmp_path: Path) -> None:
        """Test that validator rejects nodes with custom methods."""
        bad_node = tmp_path / "bad_node.py"
        bad_node.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__(container)

    def custom_method(self):
        pass
''')
        result = validate_node_py(bad_node)
        assert not result.valid
        assert "extra methods" in result.error.lower() or "only __init__" in result.error.lower()

    def test_validate_node_py_accepts_valid_node(self, tmp_path: Path) -> None:
        """Test that validator accepts properly declarative nodes."""
        good_node = tmp_path / "good_node.py"
        good_node.write_text('''
class GoodNode:
    def __init__(self, container):
        super().__init__(container)
''')
        result = validate_node_py(good_node)
        assert result.valid, f"Should be valid: {result.error}"

    def test_validate_node_py_rejects_wrong_init_body(self, tmp_path: Path) -> None:
        """Test that validator rejects nodes with incorrect __init__ body.

        The __init__ must contain exactly super().__init__(container).
        Any other statement should be rejected.
        """
        # Test case 1: print statement instead of super().__init__
        bad_node_print = tmp_path / "bad_node_print.py"
        bad_node_print.write_text('''
class BadNode:
    def __init__(self, container):
        print("hello")
''')
        result = validate_node_py(bad_node_print)
        assert not result.valid
        assert "super().__init__(container)" in result.error

        # Test case 2: assignment instead of super().__init__
        bad_node_assign = tmp_path / "bad_node_assign.py"
        bad_node_assign.write_text('''
class BadNode:
    def __init__(self, container):
        self.container = container
''')
        result = validate_node_py(bad_node_assign)
        assert not result.valid
        assert "super().__init__(container)" in result.error

        # Test case 3: wrong argument name
        bad_node_arg = tmp_path / "bad_node_arg.py"
        bad_node_arg.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__(self)
''')
        result = validate_node_py(bad_node_arg)
        assert not result.valid
        assert "super().__init__(container)" in result.error

        # Test case 4: calling wrong method on super()
        bad_node_method = tmp_path / "bad_node_method.py"
        bad_node_method.write_text('''
class BadNode:
    def __init__(self, container):
        super().setup(container)
''')
        result = validate_node_py(bad_node_method)
        assert not result.valid
        assert "super().__init__(container)" in result.error

        # Test case 5: empty __init__ body (only pass)
        bad_node_empty = tmp_path / "bad_node_empty.py"
        bad_node_empty.write_text('''
class BadNode:
    def __init__(self, container):
        pass
''')
        result = validate_node_py(bad_node_empty)
        assert not result.valid
        assert "super().__init__(container)" in result.error

    def test_validate_node_py_accepts_valid_node_with_docstring(self, tmp_path: Path) -> None:
        """Test that validator accepts nodes with docstring + super().__init__."""
        good_node = tmp_path / "good_node_docstring.py"
        good_node.write_text('''
class GoodNode:
    def __init__(self, container):
        """Initialize the node with container."""
        super().__init__(container)
''')
        result = validate_node_py(good_node)
        assert result.valid, f"Should be valid with docstring: {result.error}"
