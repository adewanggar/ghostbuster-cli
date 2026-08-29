"""Import Fixer - removes unused packages from requirements/pyproject and unused import statements."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory


class ImportFixer:
    """Removes unused dependencies from config files and unused import statements."""

    def preview(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Preview what changes would be made (dry-run mode)."""
        changes: list[str] = []
        dead_ghosts = [g for g in ghosts if g.category == GhostCategory.DEAD_IMPORT and g.fixable]
        if not dead_ghosts:
            return changes

        # 1. Preview removing from requirements.txt and pyproject.toml
        changes.extend(self._preview_config_removals(dead_ghosts))

        # 2. Preview removing unused import statements from Python files
        dead_packages = self._get_dead_package_names(dead_ghosts)
        for py_file in path.rglob("*.py"):
            parts = py_file.relative_to(path).parts
            if any(p in {"venv", ".venv", "node_modules", ".git", "__pycache__"} for p in parts):
                continue

            file_changes = self._find_removable_imports(py_file, dead_packages)
            changes.extend(file_changes)

        return changes

    def fix(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Apply fixes: remove unused dependencies from config and import statements."""
        applied: list[str] = []
        dead_ghosts = [g for g in ghosts if g.category == GhostCategory.DEAD_IMPORT and g.fixable]
        if not dead_ghosts:
            return applied

        # 1. Remove from requirements.txt and pyproject.toml
        applied.extend(self._apply_config_removals(dead_ghosts))

        # 2. Remove unused import statements from Python files
        dead_packages = self._get_dead_package_names(dead_ghosts)
        for py_file in path.rglob("*.py"):
            parts = py_file.relative_to(path).parts
            if any(p in {"venv", ".venv", "node_modules", ".git", "__pycache__"} for p in parts):
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

    def _preview_config_removals(self, ghosts: list[Ghost]) -> list[str]:
        """Preview removal of dependencies from requirements.txt and pyproject.toml."""
        changes: list[str] = []
        for ghost in ghosts:
            if ghost.file_path and ghost.file_path.exists():
                changes.append(f"  Would remove '{ghost.name}' from {ghost.file_path.name}")
        return changes

    def _apply_config_removals(self, ghosts: list[Ghost]) -> list[str]:
        """Remove declared dependencies from requirements.txt and pyproject.toml."""
        applied: list[str] = []

        # Group by config file
        by_file: dict[Path, list[str]] = {}
        for ghost in ghosts:
            if ghost.file_path and ghost.file_path.exists():
                by_file.setdefault(ghost.file_path, []).append(ghost.name)

        for file_path, package_names in by_file.items():
            if file_path.name == "requirements.txt" or file_path.name.endswith(".txt"):
                removed = self._remove_from_requirements_txt(file_path, package_names)
                for pkg in removed:
                    applied.append(f"  Removed '{pkg}' from {file_path.name}")
            elif file_path.name == "pyproject.toml":
                removed = self._remove_from_pyproject_toml(file_path, package_names)
                for pkg in removed:
                    applied.append(f"  Removed '{pkg}' from {file_path.name}")
            elif file_path.name == "package.json":
                removed = self._remove_from_package_json(file_path, package_names)
                for pkg in removed:
                    applied.append(f"  Removed '{pkg}' from {file_path.name}")

        return applied

    def _remove_from_package_json(self, filepath: Path, package_names: list[str]) -> list[str]:
        """Remove package entries from dependencies / devDependencies in package.json."""
        removed: list[str] = []
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            targets = set(package_names)

            for section in ["dependencies", "devDependencies", "peerDependencies"]:
                if section in data and isinstance(data[section], dict):
                    for pkg in list(data[section].keys()):
                        if pkg in targets:
                            del data[section][pkg]
                            removed.append(pkg)

            if removed:
                filepath.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        except (OSError, ValueError):
            pass

        return removed

    def _remove_from_requirements_txt(self, filepath: Path, package_names: list[str]) -> list[str]:
        """Remove package entries from a requirements.txt file."""
        removed: list[str] = []
        try:
            lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)
            norm_targets = {p.lower().replace("-", "_") for p in package_names}

            new_lines: list[str] = []
            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                    new_lines.append(line)
                    continue

                pkg_name = re.split(r"[>=<!\[;@]", stripped)[0].strip()
                norm_pkg = pkg_name.lower().replace("-", "_")

                if norm_pkg in norm_targets:
                    removed.append(pkg_name)
                else:
                    new_lines.append(line)

            if removed:
                filepath.write_text("".join(new_lines), encoding="utf-8")
        except OSError:
            pass

        return removed

    def _remove_from_pyproject_toml(self, filepath: Path, package_names: list[str]) -> list[str]:
        """Remove package entries from dependencies list in pyproject.toml."""
        removed: list[str] = []
        try:
            lines = filepath.read_text(encoding="utf-8").splitlines(keepends=True)
            norm_targets = {p.lower().replace("-", "_") for p in package_names}

            new_lines: list[str] = []
            for line in lines:
                stripped = line.strip().strip(",").strip('"').strip("'")
                pkg_name = re.split(r"[>=<!\[;@]", stripped)[0].strip()
                norm_pkg = pkg_name.lower().replace("-", "_")

                if norm_pkg in norm_targets and ("=" not in stripped or "[" not in stripped):
                    removed.append(pkg_name)
                else:
                    new_lines.append(line)

            if removed:
                filepath.write_text("".join(new_lines), encoding="utf-8")
        except OSError:
            pass

        return removed

    def _find_removable_imports(self, filepath: Path, dead_packages: set[str]) -> list[str]:
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

    def _remove_imports_from_file(self, filepath: Path, dead_packages: set[str]) -> list[str]:
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
                line for i, line in enumerate(source_lines, start=1) if i not in lines_to_remove
            ]
            filepath.write_text("".join(new_lines), encoding="utf-8")

        return applied
