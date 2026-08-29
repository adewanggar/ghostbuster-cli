"""Configuration loading for ghostbuster.

Supports configuration from:
- .ghostbuster.toml (project root)
- pyproject.toml [tool.ghostbuster] section
- CLI flags (highest priority)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast


@dataclass
class GhostbusterConfig:
    """Configuration for a ghostbuster scan.

    All fields have sensible defaults so ghostbuster works with zero config.
    """

    # Directories to exclude from scanning
    exclude_dirs: list[str] = field(
        default_factory=lambda: [
            "venv",
            ".venv",
            "node_modules",
            ".git",
            "__pycache__",
            ".tox",
            ".nox",
            "build",
            "dist",
            ".eggs",
            "migrations",
        ]
    )

    # File patterns to exclude from scanning
    exclude_patterns: list[str] = field(default_factory=list)

    # Categories to scan (empty = all)
    categories: list[str] = field(default_factory=list)

    # Packages to ignore in dead-import scanning
    ignore_packages: list[str] = field(default_factory=list)

    # Env vars to ignore in phantom-env scanning
    ignore_env_vars: list[str] = field(default_factory=list)

    # Functions/classes to ignore in zombie-code scanning
    ignore_names: list[str] = field(default_factory=list)

    # Large file threshold in bytes (default: 10MB)
    large_file_threshold: int = 10 * 1024 * 1024

    @staticmethod
    def load(path: Path) -> GhostbusterConfig:
        """Load configuration from project files.

        Priority:
        1. .ghostbuster.toml
        2. pyproject.toml [tool.ghostbuster]
        3. Defaults
        """
        config = GhostbusterConfig()

        # Try .ghostbuster.toml first
        ghostbuster_toml = path / ".ghostbuster.toml"
        if ghostbuster_toml.exists():
            data = _load_toml(ghostbuster_toml)
            config = _apply_config(config, data)
            return config

        # Try pyproject.toml [tool.ghostbuster]
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            data = _load_toml(pyproject)
            tool_config = data.get("tool", {}).get("ghostbuster", {})
            if tool_config:
                config = _apply_config(config, tool_config)

        return config


def _load_toml(filepath: Path) -> dict[str, Any]:
    """Load a TOML file and return its contents as a dict."""
    try:
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore[no-redef]

        data = tomllib.loads(filepath.read_text(encoding="utf-8"))
        return cast("dict[str, Any]", data) if isinstance(data, dict) else {}
    except Exception:
        return {}


def _apply_config(config: GhostbusterConfig, data: dict[str, Any]) -> GhostbusterConfig:
    """Apply a dict of config values to a GhostbusterConfig."""
    if "exclude_dirs" in data and isinstance(data["exclude_dirs"], list):
        config.exclude_dirs = data["exclude_dirs"]
    if "exclude_patterns" in data and isinstance(data["exclude_patterns"], list):
        config.exclude_patterns = data["exclude_patterns"]
    if "categories" in data and isinstance(data["categories"], list):
        config.categories = data["categories"]
    if "ignore_packages" in data and isinstance(data["ignore_packages"], list):
        config.ignore_packages = data["ignore_packages"]
    if "ignore_env_vars" in data and isinstance(data["ignore_env_vars"], list):
        config.ignore_env_vars = data["ignore_env_vars"]
    if "ignore_names" in data and isinstance(data["ignore_names"], list):
        config.ignore_names = data["ignore_names"]
    if "large_file_threshold" in data and isinstance(data["large_file_threshold"], int):
        config.large_file_threshold = data["large_file_threshold"]
    return config
