"""Phantom Env Scanner - detects env vars referenced but never set.

Scans Python, JavaScript, and TypeScript files for environment variable usage
and checks if the referenced variables are defined in .env files or the system.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory, Severity

# Standard directories to skip
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

# Standard environment variables to ignore
IGNORED_SYSTEM_VARS: set[str] = {
    "NODE_ENV",
    "PATH",
    "PORT",
    "HOST",
    "HOME",
    "USER",
    "CI",
}


class PhantomEnvScanner:
    """Detects environment variables referenced in code but not set anywhere."""

    name = "phantom-env"

    def scan(self, path: Path) -> list[Ghost]:
        """Scan a project directory for phantom environment variables."""
        referenced = self._find_referenced_env_vars(path)
        if not referenced:
            return []

        defined = self._find_defined_env_vars(path)
        ghosts: list[Ghost] = []

        for env_var, locations in referenced.items():
            if env_var not in defined and env_var not in IGNORED_SYSTEM_VARS:
                first_file, first_line = locations[0]
                locations_str = ", ".join(f"{f.name}:{l}" for f, l in locations[:3])
                if len(locations) > 3:
                    locations_str += f" (+{len(locations) - 3} more)"

                ghosts.append(
                    Ghost(
                        category=GhostCategory.PHANTOM_ENV,
                        name=env_var,
                        message=(
                            f"Environment variable '{env_var}' is referenced "
                            f"at {locations_str} but never defined"
                        ),
                        file_path=first_file,
                        line_number=first_line,
                        severity=Severity.HIGH,
                        fixable=True,
                        suggestion=f"Add '{env_var}=' to your .env file or set it in your environment",
                    )
                )

        return ghosts

    def _find_referenced_env_vars(self, path: Path) -> dict[str, list[tuple[Path, int]]]:
        """Find all env var references in Python and JS/TS files."""
        env_vars: dict[str, list[tuple[Path, int]]] = {}

        for file_path in path.rglob("*"):
            if not file_path.is_file():
                continue

            parts = file_path.relative_to(path).parts
            if any(p in SKIP_DIRS for p in parts):
                continue

            suffix = file_path.suffix.lower()

            if suffix == ".py":
                self._find_python_env_vars(file_path, env_vars)
            elif suffix in JS_TS_EXTENSIONS:
                self._find_js_ts_env_vars(file_path, env_vars)

        return env_vars

    def _find_python_env_vars(
        self, filepath: Path, env_vars: dict[str, list[tuple[Path, int]]]
    ) -> None:
        """Find env var references in a Python file via AST."""
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(filepath))
            for node in ast.walk(tree):
                env_name = self._extract_env_var_from_node(node)
                if env_name:
                    env_vars.setdefault(env_name, []).append((filepath, getattr(node, "lineno", 0)))
        except (SyntaxError, OSError):
            pass

    def _find_js_ts_env_vars(
        self, filepath: Path, env_vars: dict[str, list[tuple[Path, int]]]
    ) -> None:
        """Find env var references in JS/TS files using regex."""
        try:
            source = filepath.read_text(encoding="utf-8", errors="ignore")
            lines = source.splitlines()

            # Patterns:
            # 1. process.env.VAR_NAME
            # 2. process.env["VAR_NAME"] or process.env['VAR_NAME']
            # 3. import.meta.env.VITE_VAR_NAME
            # 4. import.meta.env["VITE_VAR_NAME"]
            patterns = [
                r"""process\.env\.([A-Za-z_][A-Za-z0-9_]*)""",
                r"""process\.env\[['"]([A-Za-z_][A-Za-z0-9_]*)['"]\]""",
                r"""import\.meta\.env\.([A-Za-z_][A-Za-z0-9_]*)""",
                r"""import\.meta\.env\[['"]([A-Za-z_][A-Za-z0-9_]*)['"]\]""",
            ]

            for lineno, line in enumerate(lines, start=1):
                # Skip comments
                stripped = line.strip()
                if (
                    stripped.startswith("//")
                    or stripped.startswith("/*")
                    or stripped.startswith("*")
                ):
                    continue

                for pattern in patterns:
                    for match in re.finditer(pattern, line):
                        var_name = match.group(1)
                        env_vars.setdefault(var_name, []).append((filepath, lineno))

        except OSError:
            pass

    def _extract_env_var_from_node(self, node: ast.AST) -> str | None:
        """Extract an env var name from an AST node if it represents one."""
        # os.environ.get("VAR_NAME") or os.environ.get('VAR_NAME', default)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "get" and self._is_os_environ(node.func.value):
                return self._get_first_str_arg(node)
            if (
                node.func.attr == "getenv"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "os"
            ):
                return self._get_first_str_arg(node)

        # os.environ["VAR_NAME"]
        if isinstance(node, ast.Subscript) and self._is_os_environ(node.value):
            slice_node = node.slice
            if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
                return slice_node.value

        return None

    def _is_os_environ(self, node: ast.AST) -> bool:
        """Check if a node represents 'os.environ'."""
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "environ"
            and isinstance(node.value, ast.Name)
            and node.value.id == "os"
        )

    def _get_first_str_arg(self, node: ast.Call) -> str | None:
        """Get the first string argument from a call node."""
        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            return node.args[0].value
        return None

    def _find_defined_env_vars(self, path: Path) -> set[str]:
        """Find env vars that are actually defined in system or env files."""
        defined: set[str] = set()

        # System environment
        defined.update(os.environ.keys())

        # .env files
        for env_filename in (
            ".env",
            ".env.example",
            ".env.sample",
            ".env.template",
            ".env.local",
            ".env.development",
            ".env.production",
        ):
            env_file = path / env_filename
            if env_file.exists():
                defined.update(self._parse_env_file(env_file))

        return defined

    def _parse_env_file(self, filepath: Path) -> set[str]:
        """Parse a .env file and return all defined variable names."""
        env_vars: set[str] = set()
        try:
            for line in filepath.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=", line)
                if match:
                    env_vars.add(match.group(1))
        except OSError:
            pass
        return env_vars
