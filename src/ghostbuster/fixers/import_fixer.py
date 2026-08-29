"""Import Fixer — removes unused import statements from Python files.

Works with the dead-import scanner findings to automatically clean up
import statements that reference packages no longer needed.
"""

from __future__ import annotations

import ast
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory


class ImportFixer:
    """Removes unused import statements from Python files.

    This fixer works on a per-file basis, removing import lines that
    reference packages identified as dead imports.
    """

    def preview(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Preview what changes would be made (dry-run mode).

        Returns a list of human-readable descriptions of changes.
        """
        changes: list[str] = []
        dead_packages = self._get_dead_package_names(ghosts)

        for py_file in path.rglob("*.py"):
            parts = py_file.relative_to(path).parts
            if any(
                p in {"venv", ".venv", "node_modules", ".git", "__pycache__"}
                for p in parts
            ):
                continue

            file_changes = self._find_removable_imports(py_file, dead_packages)
            changes.extend(file_changes)

        return changes

    def fix(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Actually apply fixes: remove unused import statements.

        Returns a list of applied changes.
        """
        applied: list[str] = []
        dead_packages = self._get_dead_package_names(ghosts)

        for py_file in path.rglob("*.py"):
            parts = py_file.relative_to(path).parts
            if any(
                p in {"venv", ".venv", "node_modules", ".git", "__pycache__"}
                for p in parts
            ):
                continue

            result = self._remove_imports_from_file(py_file, dead_packages)
            applied.extend(result)

        return applied

    def _get_dead_package_names(self, ghosts: list[Ghost]) -> set[str]:
        """Extract package names from dead-import ghost findings."""
        return {
            g.name.lower().replace("-", "_")
            for g in ghosts
            if g.category == GhostCategory.DEAD_IMPORT
        }

    def _find_removable_imports(
        self, filepath: Path, dead_packages: set[str]
    ) -> list[str]:
        """Find import statements that can be removed from a file."""
        changes: list[str] = []
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, OSError):
            return changes

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0].lower().replace("-", "_")
                    if pkg in dead_packages:
                        changes.append(
                            f"  Would remove: 'import {alias.name}' from {filepath.name}:{node.lineno}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                pkg = node.module.split(".")[0].lower().replace("-", "_")
                if pkg in dead_packages:
                    names = ", ".join(a.name for a in node.names)
                    changes.append(
                        f"  Would remove: 'from {node.module} import {names}' from {filepath.name}:{node.lineno}"
                    )

        return changes

    def _remove_imports_from_file(
        self, filepath: Path, dead_packages: set[str]
    ) -> list[str]:
        """Remove import statements for dead packages from a single file."""
        applied: list[str] = []
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(filepath))
        except (SyntaxError, OSError):
            return applied

        lines_to_remove: set[int] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0].lower().replace("-", "_")
                    if pkg in dead_packages:
                        lines_to_remove.add(node.lineno)
                        applied.append(
                            f"  Removed: 'import {alias.name}' from {filepath.name}:{node.lineno}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                pkg = node.module.split(".")[0].lower().replace("-", "_")
                if pkg in dead_packages:
                    lines_to_remove.add(node.lineno)
                    # Handle multi-line imports
                    if node.end_lineno and node.end_lineno > node.lineno:
                        for ln in range(node.lineno, node.end_lineno + 1):
                            lines_to_remove.add(ln)
                    names = ", ".join(a.name for a in node.names)
                    applied.append(
                        f"  Removed: 'from {node.module} import {names}' from {filepath.name}:{node.lineno}"
                    )

        if lines_to_remove:
            source_lines = source.splitlines(keepends=True)
            new_lines = [
                line
                for i, line in enumerate(source_lines, start=1)
                if i not in lines_to_remove
            ]
            filepath.write_text("".join(new_lines), encoding="utf-8")

        return applied
