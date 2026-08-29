"""Zombie Code Scanner — detects functions and classes that are never called.

Uses AST analysis to find definitions and cross-reference them against
all name references in the codebase.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory, Severity

# Decorators that indicate a function is used externally (not dead)
FRAMEWORK_DECORATORS: set[str] = {
    # Web frameworks
    "route",
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "head",
    "options",
    "api_view",
    "action",
    "app_route",
    # Testing
    "fixture",
    "pytest_fixture",
    "parametrize",
    "override_settings",
    "mock_patch",
    # General
    "property",
    "staticmethod",
    "classmethod",
    "abstractmethod",
    "cached_property",
    "lru_cache",
    "cache",
    "register",
    "receiver",
    "hook",
    "hookimpl",
    "validator",
    "field_validator",
    "model_validator",
    "event",
    "listener",
    "subscriber",
    "handler",
    "task",
    "shared_task",
    "periodic_task",
    "command",
    "group",
    "callback",
    "click_command",
    "click_group",
    "app_command",
    "app_group",
    "overload",
}

# Method names that are expected to exist by convention (dunder, lifecycle, etc.)
CONVENTIONAL_NAMES: set[str] = {
    # Dunder methods
    "__init__",
    "__new__",
    "__del__",
    "__repr__",
    "__str__",
    "__bytes__",
    "__format__",
    "__hash__",
    "__bool__",
    "__len__",
    "__length_hint__",
    "__getitem__",
    "__setitem__",
    "__delitem__",
    "__iter__",
    "__next__",
    "__reversed__",
    "__contains__",
    "__add__",
    "__radd__",
    "__iadd__",
    "__sub__",
    "__mul__",
    "__truediv__",
    "__floordiv__",
    "__mod__",
    "__pow__",
    "__lshift__",
    "__rshift__",
    "__and__",
    "__xor__",
    "__or__",
    "__neg__",
    "__pos__",
    "__abs__",
    "__invert__",
    "__complex__",
    "__int__",
    "__float__",
    "__index__",
    "__enter__",
    "__exit__",
    "__await__",
    "__aiter__",
    "__anext__",
    "__aenter__",
    "__aexit__",
    "__call__",
    "__get__",
    "__set__",
    "__delete__",
    "__set_name__",
    "__init_subclass__",
    "__class_getitem__",
    "__eq__",
    "__ne__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
    "__getattr__",
    "__getattribute__",
    "__setattr__",
    "__delattr__",
    "__dir__",
    "__slots__",
    "__dict__",
    "__weakref__",
    "__reduce__",
    "__reduce_ex__",
    "__getstate__",
    "__setstate__",
    "__copy__",
    "__deepcopy__",
    "__sizeof__",
    "__fspath__",
    "__missing__",
    "__post_init__",
    # Lifecycle / Framework hooks
    "setUp",
    "tearDown",
    "setUpClass",
    "tearDownClass",
    "setUpModule",
    "tearDownModule",
    "setup_method",
    "teardown_method",
    "main",
}


@dataclass
class _Definition:
    """A function or class definition found in the codebase."""

    name: str
    file_path: Path
    line_number: int
    is_method: bool = False
    is_class: bool = False
    has_framework_decorator: bool = False


class ZombieCodeScanner:
    """Detects functions and classes that are never called/referenced."""

    name = "zombie-code"

    def scan(self, path: Path) -> list[Ghost]:
        """Scan a project directory for zombie code."""
        definitions: list[_Definition] = []
        references: set[str] = set()

        for py_file in path.rglob("*.py"):
            # Skip non-source directories
            parts = py_file.relative_to(path).parts
            if any(
                p
                in {
                    "venv",
                    ".venv",
                    "node_modules",
                    ".git",
                    "__pycache__",
                    ".tox",
                    ".nox",
                    "build",
                    "dist",
                    "migrations",
                    ".eggs",
                }
                for p in parts
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, OSError):
                continue

            # Collect definitions and references from this file
            file_defs, file_refs = self._analyze_file(tree, py_file)
            definitions.extend(file_defs)
            references.update(file_refs)

        # Find zombies: defined but never referenced
        ghosts: list[Ghost] = []
        for defn in definitions:
            if self._is_zombie(defn, references):
                rel_path = (
                    defn.file_path.relative_to(path)
                    if path in defn.file_path.parents or path == defn.file_path.parent
                    else defn.file_path
                )
                kind = "Class" if defn.is_class else "Function"
                action = "referenced" if defn.is_class else "called"
                ghosts.append(
                    Ghost(
                        category=GhostCategory.ZOMBIE_CODE,
                        name=defn.name,
                        message=f"{kind} '{defn.name}' is defined at {rel_path}:{defn.line_number} but never {action}",
                        file_path=defn.file_path,
                        line_number=defn.line_number,
                        severity=Severity.LOW,
                        fixable=False,
                        suggestion=f"Remove '{defn.name}' if it's truly unused, or add '# noqa: ghostbuster' to suppress",
                    )
                )

        return ghosts

    def _analyze_file(
        self, tree: ast.Module, file_path: Path
    ) -> tuple[list[_Definition], set[str]]:
        """Extract function/class definitions and name references from a file."""
        definitions: list[_Definition] = []
        references: set[str] = set()

        # Check if this is a test file (test files are excluded from zombie detection)
        is_test_file = file_path.name.startswith("test_") or file_path.name.endswith("_test.py")

        for node in ast.walk(tree):
            # Collect function definitions
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Skip test functions entirely
                if is_test_file or node.name.startswith("test_"):
                    references.add(node.name)
                    continue

                is_method = self._is_method(node, tree)
                has_decorator = self._has_framework_decorator(node)

                definitions.append(
                    _Definition(
                        name=node.name,
                        file_path=file_path,
                        line_number=node.lineno,
                        is_method=is_method,
                        has_framework_decorator=has_decorator,
                    )
                )

            # Collect class definitions
            elif isinstance(node, ast.ClassDef):
                if not is_test_file:
                    definitions.append(
                        _Definition(
                            name=node.name,
                            file_path=file_path,
                            line_number=node.lineno,
                            is_class=True,
                        )
                    )

            # Collect references (names being used)
            elif isinstance(node, ast.Name):
                references.add(node.id)
            elif isinstance(node, ast.Attribute):
                references.add(node.attr)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    references.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    references.add(node.func.attr)

        return definitions, references

    def _is_method(self, node: ast.FunctionDef | ast.AsyncFunctionDef, tree: ast.Module) -> bool:
        """Check if a function is defined inside a class (i.e., is a method)."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                for child in parent.body:
                    if child is node:
                        return True
        return False

    def _has_framework_decorator(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check if a function has a decorator that indicates external usage."""
        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)
            if dec_name and dec_name.lower() in FRAMEWORK_DECORATORS:
                return True
        return False

    def _get_decorator_name(self, node: ast.expr) -> str | None:
        """Extract the base name from a decorator node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return None

    def _is_zombie(self, defn: _Definition, references: set[str]) -> bool:
        """Determine if a definition is truly a zombie (unreferenced)."""
        # Skip conventional names (dunders, lifecycle hooks)
        if defn.name in CONVENTIONAL_NAMES:
            return False

        # Skip names starting with underscore in test patterns
        if defn.name.startswith("test_"):
            return False

        # Skip if it has a framework decorator
        if defn.has_framework_decorator:
            return False

        # Skip private methods with a single underscore (often used by framework)
        # But flag double-underscore non-dunder names
        if defn.is_method and defn.name.startswith("_") and not defn.name.startswith("__"):
            return False

        # The core check: is the name referenced anywhere?
        return defn.name not in references
