"""Phantom Env Scanner — detects env vars referenced but never set.

Scans Python files for os.environ / os.getenv usage and checks if the
referenced environment variables are defined in .env files or the system.
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory, Severity


class PhantomEnvScanner:
    """Detects environment variables referenced in code but not set anywhere."""

    name = "phantom-env"

    def scan(self, path: Path) -> list[Ghost]:
        """Scan a project directory for phantom environment variables."""
        # Collect all env vars referenced in code
        referenced = self._find_referenced_env_vars(path)
        if not referenced:
            return []

        # Collect all env vars that are defined
        defined = self._find_defined_env_vars(path)

        # Find phantoms: referenced but not defined
        ghosts: list[Ghost] = []
        for env_var, locations in referenced.items():
            if env_var not in defined:
                # Use the first location for the ghost
                first_file, first_line = locations[0]

                locations_str = ", ".join(
                    f"{f.name}:{l}" for f, l in locations[:3]
                )
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

    def _find_referenced_env_vars(
        self, path: Path
    ) -> dict[str, list[tuple[Path, int]]]:
        """Find all env var references in Python files via AST + regex.

        Returns mapping of env_var_name -> list of (file_path, line_number).
        """
        env_vars: dict[str, list[tuple[Path, int]]] = {}

        for py_file in path.rglob("*.py"):
            parts = py_file.relative_to(path).parts
            if any(
                p in {
                    "venv", ".venv", "node_modules", ".git",
                    "__pycache__", ".tox", ".nox", "build", "dist",
                }
                for p in parts
            ):
                continue

            try:
                source = py_file.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, OSError):
                continue

            # AST-based detection
            for node in ast.walk(tree):
                env_name = self._extract_env_var_from_node(node)
                if env_name:
                    env_vars.setdefault(env_name, []).append(
                        (py_file, getattr(node, "lineno", 0))
                    )

        return env_vars

    def _extract_env_var_from_node(self, node: ast.AST) -> str | None:
        """Extract an env var name from an AST node if it's an env access pattern.

        Detects:
        - os.environ["KEY"]
        - os.environ.get("KEY")
        - os.getenv("KEY")
        """
        # Pattern: os.environ["KEY"] or os.environ.get("KEY")
        if (
            isinstance(node, ast.Subscript)
            and self._is_os_environ(node.value)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            return node.slice.value

        # Pattern: os.environ.get("KEY", ...) or os.getenv("KEY", ...)
        if isinstance(node, ast.Call):
            func = node.func

            # os.getenv("KEY")
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "getenv"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            ):
                return self._get_first_str_arg(node)

            # os.environ.get("KEY")
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and self._is_os_environ(func.value)
            ):
                return self._get_first_str_arg(node)

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
        """Find env vars that are actually defined.

        Checks:
        - Current process environment
        - .env file
        - .env.example file
        - .env.sample file
        """
        defined: set[str] = set()

        # System environment
        defined.update(os.environ.keys())

        # .env files
        for env_filename in (".env", ".env.example", ".env.sample", ".env.template", ".env.local"):
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
                # Match KEY=value or export KEY=value
                match = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=", line)
                if match:
                    env_vars.add(match.group(1))
        except OSError:
            pass
        return env_vars
