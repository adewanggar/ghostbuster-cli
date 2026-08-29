"""Env Fixer - adds phantom environment variables to .env.example or .env."""

from __future__ import annotations

import re
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory


class EnvFixer:
    """Auto-fixer that appends missing environment variable stubs to .env.example."""

    def preview(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Return a list of changes that would be made without modifying files."""
        env_ghosts = [g for g in ghosts if g.category == GhostCategory.PHANTOM_ENV and g.fixable]
        if not env_ghosts:
            return []

        target_file = self._get_target_file(path)
        keys_to_add = self._get_keys_to_add(env_ghosts, target_file)
        if not keys_to_add:
            return []

        target_name = target_file.name if target_file.exists() else f"{target_file.name} (new file)"

        changes: list[str] = []
        for key in keys_to_add:
            changes.append(f"  Would add '{key}=' to {target_name}")

        return changes

    def fix(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Append missing environment variable keys to .env.example or .env."""
        env_ghosts = [g for g in ghosts if g.category == GhostCategory.PHANTOM_ENV and g.fixable]
        if not env_ghosts:
            return []

        target_file = self._get_target_file(path)
        keys_to_add = self._get_keys_to_add(env_ghosts, target_file)
        if not keys_to_add:
            return []

        existing_content = ""
        if target_file.exists():
            try:
                existing_content = target_file.read_text(encoding="utf-8")
            except OSError:
                existing_content = ""

        # Prepare new lines
        new_lines: list[str] = []
        if existing_content and not existing_content.endswith("\n"):
            new_lines.append("\n")

        for key in keys_to_add:
            new_lines.append(f"{key}=\n")

        try:
            with target_file.open("a", encoding="utf-8") as f:
                f.write("".join(new_lines))
        except OSError:
            return []

        applied: list[str] = []
        for key in keys_to_add:
            applied.append(f"  Added '{key}=' to {target_file.name}")

        return applied

    def _get_target_file(self, path: Path) -> Path:
        """Get the preferred env file to update."""
        env_example = path / ".env.example"
        if env_example.exists():
            return env_example

        env_sample = path / ".env.sample"
        if env_sample.exists():
            return env_sample

        env_template = path / ".env.template"
        if env_template.exists():
            return env_template

        # Default to .env.example to prevent accidental secret commits
        return path / ".env.example"

    def _get_keys_to_add(self, ghosts: list[Ghost], target_file: Path) -> list[str]:
        """Determine unique environment variable keys that need to be added."""
        existing_keys: set[str] = set()

        if target_file.exists():
            try:
                for line in target_file.read_text(encoding="utf-8").splitlines():
                    cleaned = line.strip()
                    if cleaned and not cleaned.startswith("#"):
                        match = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=", cleaned)
                        if match:
                            existing_keys.add(match.group(1))
            except OSError:
                pass

        keys: list[str] = []
        seen: set[str] = set()

        for ghost in ghosts:
            key = ghost.name
            if key not in existing_keys and key not in seen:
                seen.add(key)
                keys.append(key)

        return keys
