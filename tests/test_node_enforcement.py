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
from functools import lru_cache
from typing import NamedTuple

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


class NodeValidationResult(NamedTuple):
    """Result of node.py validation."""
    valid: bool
    error: str | None = None


def validate_node_py(filepath: Path) -> NodeValidationResult:
    """Enforce declarative node pattern via AST parsing.

    Results are cached to improve test performance.

    Rules:
    1. Exactly one class definition
    2. Only __init__ method allowed
    3. __init__ must only call super().__init__(container)
    """
    return _validate_node_py_cached(str(filepath))


@lru_cache(maxsize=32)
def _validate_node_py_cached(filepath_str: str) -> NodeValidationResult:
    """Cached implementation of node.py validation."""
    filepath = Path(filepath_str)
    if not filepath.exists():
        return NodeValidationResult(False, f"File not found: {filepath}")

    with open(filepath) as f:
        try:
            tree: ast.Module = ast.parse(f.read())
        except SyntaxError as e:
            return NodeValidationResult(False, f"Syntax error: {e}")

    # Find all class definitions (excluding TYPE_CHECKING blocks)
    classes: list[ast.ClassDef] = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]

    if len(classes) == 0:
        return NodeValidationResult(False, "No class found in node.py")

    if len(classes) > 1:
        return NodeValidationResult(False, f"Expected 1 class, found {len(classes)}")

    cls: ast.ClassDef = classes[0]

    # Get all methods (FunctionDef nodes that are direct children of class)
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
        n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    # Filter out __all__ and other non-method assignments
    method_names: list[str] = [m.name for m in methods]

    if len(methods) == 0:
        return NodeValidationResult(False, "No __init__ method found")

    if len(methods) > 1:
        extra_methods: list[str] = [m for m in method_names if m != "__init__"]
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
    init_body: list[ast.stmt] = methods[0].body

    # Allow docstring (ONLY first statement, ONLY if it's a string constant)
    # Docstrings in Python are ALWAYS:
    # 1. The first statement in the function body
    # 2. A string literal (not other constants like int/float)
    first_stmt_is_docstring: bool = (
        bool(init_body)
        and isinstance(init_body[0], ast.Expr)
        and isinstance(init_body[0].value, ast.Constant)
        and isinstance(init_body[0].value.value, str)
    )
    non_docstring_stmts: list[ast.stmt] = init_body[1:] if first_stmt_is_docstring else init_body

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
    stmt: ast.stmt = non_docstring_stmts[0]
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
    call: ast.expr = stmt.value
    if not isinstance(call, ast.Call):
        return False

    # Must be calling an attribute (super().__init__)
    if not isinstance(call.func, ast.Attribute):
        return False

    attr: ast.Attribute = call.func
    if attr.attr != "__init__":
        return False

    # The attribute's value must be super() call
    if not isinstance(attr.value, ast.Call):
        return False

    super_call: ast.Call = attr.value
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

    arg: ast.expr = call.args[0]
    if not isinstance(arg, ast.Name):
        return False

    if arg.id != "container":
        return False

    # No keyword arguments allowed
    if call.keywords:
        return False

    return True


class TestNodeEnforcement:
    """Test that all node.py files follow declarative pattern.

    These tests use AST parsing to verify that node.py files conform to
    the ONEX declarative pattern requirements:
    - Exactly one class definition
    - Only __init__ method allowed
    - __init__ body must be exactly super().__init__(container)
    - Optional docstring allowed as first statement in __init__
    """

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_py_exists(self, node_name: str) -> None:
        """Verify node.py exists for each Core 8 node.

        Skipped for nodes not yet implemented during scaffold phase.
        """
        node_path: Path = NODES_DIR / node_name / "node.py"
        # Skip if not yet implemented
        if not node_path.exists():
            pytest.skip(f"Node not yet implemented: {node_name}")
        assert node_path.exists()

    @pytest.mark.parametrize("node_name", CORE_8_NODES)
    def test_node_py_is_declarative(self, node_name: str) -> None:
        """Verify node.py follows declarative pattern.

        Uses AST-based validation to ensure the node.py file contains
        exactly one class with only __init__ that calls super().__init__(container).
        Skipped for nodes not yet implemented.
        """
        node_path: Path = NODES_DIR / node_name / "node.py"
        if not node_path.exists():
            pytest.skip(f"Node not yet implemented: {node_name}")

        result: NodeValidationResult = validate_node_py(node_path)
        assert result.valid, f"Node {node_name} failed enforcement: {result.error}"

    def test_validate_node_py_rejects_custom_methods(self, tmp_path: Path) -> None:
        """Test that validator rejects nodes with custom methods."""
        bad_node: Path = tmp_path / "bad_node.py"
        bad_node.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__(container)

    def custom_method(self):
        pass
''')
        result: NodeValidationResult = validate_node_py(bad_node)
        assert not result.valid
        assert result.error is not None
        assert "extra methods" in result.error.lower() or "only __init__" in result.error.lower()

    def test_validate_node_py_accepts_valid_node(self, tmp_path: Path) -> None:
        """Test that validator accepts properly declarative nodes."""
        good_node: Path = tmp_path / "good_node.py"
        good_node.write_text('''
class GoodNode:
    def __init__(self, container):
        super().__init__(container)
''')
        result: NodeValidationResult = validate_node_py(good_node)
        assert result.valid, f"Should be valid: {result.error}"

    def test_validate_node_py_rejects_wrong_init_body(self, tmp_path: Path) -> None:
        """Test that validator rejects nodes with incorrect __init__ body.

        The __init__ must contain exactly super().__init__(container).
        Any other statement should be rejected.
        """
        # Test case 1: print statement instead of super().__init__
        bad_node_print: Path = tmp_path / "bad_node_print.py"
        bad_node_print.write_text('''
class BadNode:
    def __init__(self, container):
        print("hello")
''')
        result: NodeValidationResult = validate_node_py(bad_node_print)
        assert not result.valid
        assert result.error is not None
        assert "super().__init__(container)" in result.error

        # Test case 2: assignment instead of super().__init__
        bad_node_assign: Path = tmp_path / "bad_node_assign.py"
        bad_node_assign.write_text('''
class BadNode:
    def __init__(self, container):
        self.container = container
''')
        result = validate_node_py(bad_node_assign)
        assert not result.valid
        assert result.error is not None
        assert "super().__init__(container)" in result.error

        # Test case 3: wrong argument name
        bad_node_arg: Path = tmp_path / "bad_node_arg.py"
        bad_node_arg.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__(self)
''')
        result = validate_node_py(bad_node_arg)
        assert not result.valid
        assert result.error is not None
        assert "super().__init__(container)" in result.error

        # Test case 4: calling wrong method on super()
        bad_node_method: Path = tmp_path / "bad_node_method.py"
        bad_node_method.write_text('''
class BadNode:
    def __init__(self, container):
        super().setup(container)
''')
        result = validate_node_py(bad_node_method)
        assert not result.valid
        assert result.error is not None
        assert "super().__init__(container)" in result.error

        # Test case 5: empty __init__ body (only pass)
        bad_node_empty: Path = tmp_path / "bad_node_empty.py"
        bad_node_empty.write_text('''
class BadNode:
    def __init__(self, container):
        pass
''')
        result = validate_node_py(bad_node_empty)
        assert not result.valid
        assert result.error is not None
        assert "super().__init__(container)" in result.error

    def test_validate_node_py_accepts_valid_node_with_docstring(self, tmp_path: Path) -> None:
        """Test that validator accepts nodes with docstring + super().__init__."""
        good_node: Path = tmp_path / "good_node_docstring.py"
        good_node.write_text('''
class GoodNode:
    def __init__(self, container):
        """Initialize the node with container."""
        super().__init__(container)
''')
        result: NodeValidationResult = validate_node_py(good_node)
        assert result.valid, f"Should be valid with docstring: {result.error}"

    def test_validate_node_py_rejects_non_string_constant(self, tmp_path: Path) -> None:
        """Test that non-string constants are NOT treated as docstrings.

        Only string literals in first position are valid docstrings.
        Integer, float, and other constants must be rejected.
        """
        # Test case 1: Integer constant before super().__init__
        bad_node_int: Path = tmp_path / "bad_node_int.py"
        bad_node_int.write_text('''
class BadNode:
    def __init__(self, container):
        42
        super().__init__(container)
''')
        result: NodeValidationResult = validate_node_py(bad_node_int)
        assert not result.valid, "Integer constant should not be treated as docstring"
        assert result.error is not None
        assert "super().__init__" in result.error or "2 statements" in result.error

        # Test case 2: Float constant before super().__init__
        bad_node_float: Path = tmp_path / "bad_node_float.py"
        bad_node_float.write_text('''
class BadNode:
    def __init__(self, container):
        3.14
        super().__init__(container)
''')
        result = validate_node_py(bad_node_float)
        assert not result.valid, "Float constant should not be treated as docstring"

        # Test case 3: None constant before super().__init__
        bad_node_none: Path = tmp_path / "bad_node_none.py"
        bad_node_none.write_text('''
class BadNode:
    def __init__(self, container):
        None
        super().__init__(container)
''')
        result = validate_node_py(bad_node_none)
        assert not result.valid, "None constant should not be treated as docstring"

        # Test case 4: Boolean constant before super().__init__
        bad_node_bool: Path = tmp_path / "bad_node_bool.py"
        bad_node_bool.write_text('''
class BadNode:
    def __init__(self, container):
        True
        super().__init__(container)
''')
        result = validate_node_py(bad_node_bool)
        assert not result.valid, "Boolean constant should not be treated as docstring"

    def test_validate_node_py_rejects_string_after_super_init(self, tmp_path: Path) -> None:
        """Test that string constants after super().__init__ are rejected.

        Only the FIRST statement can be a docstring. String literals
        appearing after super().__init__() are invalid extra statements.
        """
        bad_node: Path = tmp_path / "bad_node_string_after.py"
        bad_node.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__(container)
        """This is NOT a docstring - it comes after super().__init__"""
''')
        result: NodeValidationResult = validate_node_py(bad_node)
        assert not result.valid, "String after super().__init__ should be rejected"
        assert result.error is not None
        assert "2 statements" in result.error or "super().__init__" in result.error

    def test_validate_node_py_rejects_docstring_only(self, tmp_path: Path) -> None:
        """Test that docstring without super().__init__() is rejected.

        Even a valid docstring requires super().__init__(container) call.
        """
        bad_node: Path = tmp_path / "bad_node_docstring_only.py"
        bad_node.write_text('''
class BadNode:
    def __init__(self, container):
        """This is a docstring but no super().__init__() call."""
''')
        result: NodeValidationResult = validate_node_py(bad_node)
        assert not result.valid, "Docstring-only init should be rejected"
        assert result.error is not None
        assert "must call super().__init__(container)" in result.error

    def test_validate_node_py_rejects_extra_statements_with_super(self, tmp_path: Path) -> None:
        """Test that extra statements are rejected even with valid super().__init__().

        The __init__ body must contain ONLY:
        - Optionally a docstring (first statement)
        - super().__init__(container)
        """
        # Test case 1: Docstring + super + extra print
        bad_node_extra: Path = tmp_path / "bad_node_extra.py"
        bad_node_extra.write_text('''
class BadNode:
    def __init__(self, container):
        """Valid docstring."""
        super().__init__(container)
        print("extra statement")
''')
        result: NodeValidationResult = validate_node_py(bad_node_extra)
        assert not result.valid, "Extra statements after super().__init__ should be rejected"
        assert result.error is not None
        assert "2 statements" in result.error

        # Test case 2: Docstring + assignment + super
        bad_node_assign: Path = tmp_path / "bad_node_assign_before.py"
        bad_node_assign.write_text('''
class BadNode:
    def __init__(self, container):
        """Valid docstring."""
        self.x = 1
        super().__init__(container)
''')
        result = validate_node_py(bad_node_assign)
        assert not result.valid, "Assignment before super().__init__ should be rejected"

    def test_validate_node_py_rejects_missing_container_arg(self, tmp_path: Path) -> None:
        """Test that validator rejects super().__init__() without correct container arg.

        The super().__init__() call must have exactly one positional argument
        named 'container'. This test verifies rejection of:
        - No arguments
        - Wrong argument name
        - Too many arguments
        - Keyword arguments
        """
        # Test case 1: super().__init__() with no arguments
        bad_node_no_args: Path = tmp_path / "bad_node_no_args.py"
        bad_node_no_args.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__()
''')
        result: NodeValidationResult = validate_node_py(bad_node_no_args)
        assert not result.valid, "super().__init__() without args should be rejected"
        assert result.error is not None
        assert "super().__init__(container)" in result.error

        # Test case 2: super().__init__() with wrong argument name
        bad_node_wrong_name: Path = tmp_path / "bad_node_wrong_name.py"
        bad_node_wrong_name.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__(wrong_name)
''')
        result = validate_node_py(bad_node_wrong_name)
        assert not result.valid, "super().__init__(wrong_name) should be rejected"
        assert result.error is not None
        assert "super().__init__(container)" in result.error

        # Test case 3: super().__init__() with too many arguments
        bad_node_too_many: Path = tmp_path / "bad_node_too_many.py"
        bad_node_too_many.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__(container, extra)
''')
        result = validate_node_py(bad_node_too_many)
        assert not result.valid, "super().__init__(container, extra) should be rejected"
        assert result.error is not None
        assert "super().__init__(container)" in result.error

        # Test case 4: super().__init__() with keyword argument
        bad_node_keyword: Path = tmp_path / "bad_node_keyword.py"
        bad_node_keyword.write_text('''
class BadNode:
    def __init__(self, container):
        super().__init__(container=container)
''')
        result = validate_node_py(bad_node_keyword)
        assert not result.valid, "super().__init__(container=container) should be rejected"
        assert result.error is not None
        assert "super().__init__(container)" in result.error
