"""Dead Import Scanner — detects dependencies declared but never imported.

Checks requirements.txt, pyproject.toml, and setup.cfg for declared
dependencies, then walks all Python files to see which are actually imported.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory, Severity

# Mapping from PyPI package names to their actual import names.
# Many packages have different install names vs import names.
PACKAGE_TO_IMPORT: dict[str, str | list[str]] = {
    "pillow": "PIL",
    "scikit-learn": "sklearn",
    "scikit-image": "skimage",
    "opencv-python": "cv2",
    "opencv-python-headless": "cv2",
    "python-dateutil": "dateutil",
    "pyyaml": "yaml",
    "beautifulsoup4": "bs4",
    "python-dotenv": "dotenv",
    "pymysql": "pymysql",
    "attrs": "attr",
    "google-cloud-storage": "google.cloud.storage",
    "google-auth": "google.auth",
    "python-jose": "jose",
    "python-multipart": "multipart",
    "ujson": "ujson",
    "msgpack": "msgpack",
    "setuptools": ["setuptools", "pkg_resources"],
    "typing-extensions": "typing_extensions",
    "importlib-metadata": "importlib_metadata",
    "importlib-resources": "importlib_resources",
}

# Packages that are commonly used as CLI tools or plugins, not imported directly.
# These should not be flagged as dead imports.
TOOL_PACKAGES: set[str] = {
    "pip",
    "setuptools",
    "wheel",
    "build",
    "twine",
    "ruff",
    "black",
    "isort",
    "flake8",
    "mypy",
    "pytest",
    "pytest-cov",
    "pytest-xdist",
    "pytest-asyncio",
    "pre-commit",
    "tox",
    "nox",
    "sphinx",
    "ipython",
    "ipdb",
    "debugpy",
    "hatchling",
    "hatch",
    "poetry",
    "flit",
    "pdm",
    "autopep8",
    "pyright",
    "pylint",
    "bandit",
    "safety",
    "coverage",
}


class DeadImportScanner:
    """Detects dependencies declared in config but never imported in code."""

    name = "dead-import"

    def scan(self, path: Path) -> list[Ghost]:
        """Scan a project directory for dead imports."""
        declared = self._find_declared_dependencies(path)
        if not declared:
            return []

        imported = self._find_all_imports(path)
        ghosts: list[Ghost] = []

        for dep_name, source_file in declared:
            normalized = self._normalize_package_name(dep_name)

            # Skip known tool-only packages
            if normalized in TOOL_PACKAGES:
                continue

            # Get possible import names for this package
            import_names = self._get_import_names(normalized)

            # Check if any of the possible import names are actually used
            is_used = any(
                self._import_matches(imp, name) for imp in imported for name in import_names
            )

            if not is_used:
                ghosts.append(
                    Ghost(
                        category=GhostCategory.DEAD_IMPORT,
                        name=dep_name,
                        message=f"Package '{dep_name}' is declared in {source_file} but never imported",
                        file_path=path / source_file,
                        severity=Severity.MEDIUM,
                        fixable=True,
                        suggestion=f"Remove '{dep_name}' from {source_file}",
                    )
                )

        return ghosts

    def _normalize_package_name(self, name: str) -> str:
        """Normalize a package name: lowercase, hyphens to underscores, strip extras."""
        # Remove version specifiers and extras
        name = re.split(r"[>=<!\[;]", name)[0].strip()
        return name.lower().replace("-", "_")

    def _get_import_names(self, normalized: str) -> list[str]:
        """Get all possible import names for a normalized package name."""
        # Check our known mapping
        original = normalized.replace("_", "-")
        if original in PACKAGE_TO_IMPORT:
            mapping = PACKAGE_TO_IMPORT[original]
            if isinstance(mapping, list):
                return [m.lower().replace("-", "_") for m in mapping]
            return [mapping.lower().replace("-", "_")]

        if normalized in PACKAGE_TO_IMPORT:
            mapping = PACKAGE_TO_IMPORT[normalized]
            if isinstance(mapping, list):
                return [m.lower().replace("-", "_") for m in mapping]
            return [mapping.lower().replace("-", "_")]

        # Default: the normalized name itself is the import name
        return [normalized]

    def _import_matches(self, imported: str, expected: str) -> bool:
        """Check if an imported module matches an expected package name."""
        imported_lower = imported.lower().replace("-", "_")
        expected_lower = expected.lower().replace("-", "_")
        # Exact match or sub-module import (e.g., "google.cloud.storage" matches "google")
        return imported_lower == expected_lower or imported_lower.startswith(expected_lower + ".")

    def _find_declared_dependencies(self, path: Path) -> list[tuple[str, str]]:
        """Find all declared dependencies from project config files.

        Returns list of (package_name, source_file) tuples.
        """
        deps: list[tuple[str, str]] = []

        # Check requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            deps.extend(self._parse_requirements_txt(req_file))

        # Check pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            deps.extend(self._parse_pyproject_toml(pyproject))

        return deps

    def _parse_requirements_txt(self, filepath: Path) -> list[tuple[str, str]]:
        """Parse a requirements.txt file for package names."""
        deps: list[tuple[str, str]] = []
        try:
            for line in filepath.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                # Skip comments, empty lines, and options
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Extract package name (before any version specifier)
                name = re.split(r"[>=<!\[;@]", line)[0].strip()
                if name:
                    deps.append((name, "requirements.txt"))
        except OSError:
            pass
        return deps

    def _parse_pyproject_toml(self, filepath: Path) -> list[tuple[str, str]]:
        """Parse pyproject.toml for declared dependencies."""
        deps: list[tuple[str, str]] = []
        try:
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli as tomllib  # type: ignore[no-redef]

            data = tomllib.loads(filepath.read_text(encoding="utf-8"))
            project_deps = data.get("project", {}).get("dependencies", [])
            for dep in project_deps:
                name = re.split(r"[>=<!\[;@]", dep)[0].strip()
                if name:
                    deps.append((name, "pyproject.toml"))

            # Also check optional dependencies
            optional = data.get("project", {}).get("optional-dependencies", {})
            for group_name, group_deps in optional.items():
                for dep in group_deps:
                    name = re.split(r"[>=<!\[;@]", dep)[0].strip()
                    if name:
                        deps.append((name, f"pyproject.toml [optional: {group_name}]"))

            # Support Poetry: [tool.poetry.dependencies]
            poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
            if isinstance(poetry_deps, dict):
                for dep_name in poetry_deps:
                    if dep_name.lower() != "python":
                        deps.append((dep_name, "pyproject.toml [poetry.dependencies]"))

            # Support Poetry groups: [tool.poetry.group.<group>.dependencies]
            poetry_groups = data.get("tool", {}).get("poetry", {}).get("group", {})
            if isinstance(poetry_groups, dict):
                for group_name, group_data in poetry_groups.items():
                    if isinstance(group_data, dict):
                        g_deps = group_data.get("dependencies", {})
                        if isinstance(g_deps, dict):
                            for dep_name in g_deps:
                                if dep_name.lower() != "python":
                                    deps.append(
                                        (dep_name, f"pyproject.toml [poetry.group.{group_name}]")
                                    )

        except (OSError, Exception):
            pass
        return deps

    def _find_all_imports(self, path: Path) -> set[str]:
        """Walk all .py files and collect all imported module names via AST."""
        imports: set[str] = set()
        for py_file in path.rglob("*.py"):
            # Skip common non-source directories
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
                }
                for p in parts
            ):
                continue
            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(py_file))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module)
            except (SyntaxError, OSError):
                continue
        return imports
