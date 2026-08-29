"""Dead Import Scanner - detects dependencies declared but never imported.

Checks requirements.txt, pyproject.toml, and package.json for declared
dependencies, then walks Python, JavaScript, and TypeScript files to see which
are actually imported.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory, Severity

# Mapping from PyPI package names to their actual import names.
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

# Python tool packages that are run via CLI or plugins
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

# Node.js tool/build packages that are run via CLI or config
NODE_TOOL_PACKAGES: set[str] = {
    "typescript",
    "eslint",
    "prettier",
    "vite",
    "webpack",
    "rollup",
    "tsup",
    "esbuild",
    "jest",
    "vitest",
    "mocha",
    "chai",
    "husky",
    "lint-staged",
    "rimraf",
    "nodemon",
    "concurrently",
    "cross-env",
    "tailwindcss",
    "postcss",
    "autoprefixer",
    "dotenv-cli",
}

# Directories to skip when scanning source files
SKIP_DIRS: set[str] = {
    "venv",
    ".venv",
    "node_modules",
    ".git",
    "__pycache__",
    ".tox",
    ".nox",
    "build",
    "dist",
    ".next",
    ".nuxt",
    ".turbo",
    "coverage",
}

JS_TS_EXTENSIONS: set[str] = {
    ".js",
    ".mjs",
    ".cjs",
    ".jsx",
    ".ts",
    ".mts",
    ".cts",
    ".tsx",
    ".vue",
    ".svelte",
}


class DeadImportScanner:
    """Detects dependencies declared in config but never imported in code."""

    name = "dead-import"

    def scan(self, path: Path) -> list[Ghost]:
        """Scan a project directory for dead imports across Python and Node.js."""
        declared = self._find_declared_dependencies(path)
        if not declared:
            return []

        imported = self._find_all_imports(path)
        ghosts: list[Ghost] = []

        for dep_name, source_file in declared:
            is_node = source_file.startswith("package.json")

            if is_node:
                # Node.js package handling
                if self._is_node_tool_package(dep_name):
                    continue

                if not self._is_node_dep_used(dep_name, imported):
                    ghosts.append(
                        Ghost(
                            category=GhostCategory.DEAD_IMPORT,
                            name=dep_name,
                            message=f"Package '{dep_name}' is declared in {source_file} but never imported",
                            file_path=path / "package.json",
                            severity=Severity.MEDIUM,
                            fixable=True,
                            suggestion=f"Remove '{dep_name}' from package.json",
                        )
                    )
            else:
                # Python package handling
                normalized = self._normalize_package_name(dep_name)
                if normalized in TOOL_PACKAGES:
                    continue

                import_names = self._get_import_names(normalized)
                is_used = any(
                    self._import_matches(imp, name) for imp in imported for name in import_names
                )

                if not is_used:
                    ghosts.append(
                        Ghost(
                            category=GhostCategory.DEAD_IMPORT,
                            name=dep_name,
                            message=f"Package '{dep_name}' is declared in {source_file} but never imported",
                            file_path=path / (source_file.split(" [")[0]),
                            severity=Severity.MEDIUM,
                            fixable=True,
                            suggestion=f"Remove '{dep_name}' from {source_file.split(' [')[0]}",
                        )
                    )

        return ghosts

    def _is_node_tool_package(self, pkg_name: str) -> bool:
        """Check if a Node package is a known CLI/type/build tool."""
        if pkg_name.startswith("@types/"):
            return True
        if pkg_name.startswith("@vitejs/") or pkg_name.startswith("@babel/"):
            return True
        return pkg_name.lower() in NODE_TOOL_PACKAGES

    def _is_node_dep_used(self, dep_name: str, imported: set[str]) -> bool:
        """Check if a declared Node dependency is used in imports."""
        dep_lower = dep_name.lower()
        for imp in imported:
            imp_lower = imp.lower()
            if imp_lower == dep_lower or imp_lower.startswith(dep_lower + "/"):
                return True
        return False

    def _normalize_package_name(self, name: str) -> str:
        """Normalize a Python package name: lowercase, hyphens to underscores."""
        name = re.split(r"[>=<!\[;@]", name)[0].strip()
        return name.lower().replace("-", "_")

    def _get_import_names(self, normalized: str) -> list[str]:
        """Get all possible import names for a normalized package name."""
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

        return [normalized]

    def _import_matches(self, imported: str, expected: str) -> bool:
        """Check if an imported module matches an expected package name."""
        imported_lower = imported.lower().replace("-", "_")
        expected_lower = expected.lower().replace("-", "_")
        return imported_lower == expected_lower or imported_lower.startswith(expected_lower + ".")

    def _find_declared_dependencies(self, path: Path) -> list[tuple[str, str]]:
        """Find all declared dependencies from Python and Node.js config files."""
        deps: list[tuple[str, str]] = []

        # Check requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            deps.extend(self._parse_requirements_txt(req_file))

        # Check pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            deps.extend(self._parse_pyproject_toml(pyproject))

        # Check package.json (Node.js)
        package_json = path / "package.json"
        if package_json.exists():
            deps.extend(self._parse_package_json(package_json))

        return deps

    def _parse_requirements_txt(self, filepath: Path) -> list[tuple[str, str]]:
        """Parse a requirements.txt file for package names."""
        deps: list[tuple[str, str]] = []
        try:
            for line in filepath.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
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

    def _parse_package_json(self, filepath: Path) -> list[tuple[str, str]]:
        """Parse package.json for declared dependencies."""
        deps: list[tuple[str, str]] = []
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            for section in ["dependencies", "devDependencies", "peerDependencies"]:
                sec_deps = data.get(section, {})
                if isinstance(sec_deps, dict):
                    for dep_name in sec_deps:
                        deps.append((dep_name, f"package.json [{section}]"))
        except (OSError, ValueError):
            pass
        return deps

    def _find_all_imports(self, path: Path) -> set[str]:
        """Walk Python and JS/TS files and collect all imported module/package names."""
        imports: set[str] = set()

        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue

            parts = file_path.relative_to(path).parts
            if any(p in SKIP_DIRS for p in parts):
                continue

            suffix = file_path.suffix.lower()

            # Python files
            if suffix == ".py":
                self._extract_python_imports(file_path, imports)
            # JS/TS/Vue/Svelte files
            elif suffix in JS_TS_EXTENSIONS:
                self._extract_js_ts_imports(file_path, imports)

        return imports

    def _extract_python_imports(self, filepath: Path, imports: set[str]) -> None:
        """Extract imports from a Python file."""
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(filepath))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
        except (SyntaxError, OSError):
            pass

    def _extract_js_ts_imports(self, filepath: Path, imports: set[str]) -> None:
        """Extract imports/requires from a JavaScript or TypeScript file."""
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")

            # Patterns:
            # 1. import ... from 'pkg'
            # 2. import 'pkg'
            # 3. export ... from 'pkg'
            # 4. require('pkg')
            # 5. import('pkg')
            patterns = [
                r"""(?:import|export)\s+(?:[\w\s{},*]+from\s+)?['"]([^'"]+)['"]""",
                r"""(?:require|import)\s*\(\s*['"]([^'"]+)['"]\s*\)""",
            ]

            for pattern in patterns:
                for match in re.finditer(pattern, source):
                    raw_specifier = match.group(1).strip()
                    # Skip relative or absolute paths
                    if (
                        raw_specifier.startswith(".")
                        or raw_specifier.startswith("/")
                        or raw_specifier.startswith("#")
                    ):
                        continue

                    # Handle scoped package: @org/pkg/sub -> @org/pkg
                    if raw_specifier.startswith("@"):
                        parts = raw_specifier.split("/")
                        if len(parts) >= 2:
                            imports.add(f"{parts[0]}/{parts[1]}")
                        else:
                            imports.add(raw_specifier)
                    else:
                        # Unscoped package: pkg/sub -> pkg
                        pkg_root = raw_specifier.split("/")[0]
                        imports.add(pkg_root)

        except OSError:
            pass
