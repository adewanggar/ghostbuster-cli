"""Gitignore Fixer - adds orphan files and directories to .gitignore."""

from __future__ import annotations

from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory


class GitignoreFixer:
    """Auto-fixer that appends orphan files/directories to .gitignore."""

    def preview(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Return a list of changes that would be made without modifying files."""
        orphan_ghosts = [g for g in ghosts if g.category == GhostCategory.ORPHAN_FILE and g.fixable]
        if not orphan_ghosts:
            return []

        entries_to_add = self._get_entries_to_add(orphan_ghosts, path)
        if not entries_to_add:
            return []

        gitignore_path = path / ".gitignore"
        target_name = ".gitignore" if gitignore_path.exists() else ".gitignore (new file)"

        changes: list[str] = []
        for entry in entries_to_add:
            changes.append(f"  Would add '{entry}' to {target_name}")

        return changes

    def fix(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Append missing orphan patterns to .gitignore."""
        orphan_ghosts = [g for g in ghosts if g.category == GhostCategory.ORPHAN_FILE and g.fixable]
        if not orphan_ghosts:
            return []

        entries_to_add = self._get_entries_to_add(orphan_ghosts, path)
        if not entries_to_add:
            return []

        gitignore_path = path / ".gitignore"
        existing_content = ""
        if gitignore_path.exists():
            try:
                existing_content = gitignore_path.read_text(encoding="utf-8")
            except OSError:
                existing_content = ""

        # Prepare new content
        new_lines: list[str] = []
        if existing_content and not existing_content.endswith("\n"):
            new_lines.append("\n")

        for entry in entries_to_add:
            new_lines.append(f"{entry}\n")

        try:
            with gitignore_path.open("a", encoding="utf-8") as f:
                f.write("".join(new_lines))
        except OSError:
            return []

        applied: list[str] = []
        for entry in entries_to_add:
            applied.append(f"  Added '{entry}' to .gitignore")

        return applied

    def _get_entries_to_add(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Determine unique entries that need to be added to .gitignore."""
        gitignore_path = path / ".gitignore"
        existing_lines: set[str] = set()

        if gitignore_path.exists():
            try:
                for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                    cleaned = line.strip()
                    if cleaned and not cleaned.startswith("#"):
                        existing_lines.add(cleaned.rstrip("/"))
            except OSError:
                pass

        entries: list[str] = []
        seen: set[str] = set()

        for ghost in ghosts:
            # Determine appropriate pattern
            name = ghost.name
            if ghost.file_path and ghost.file_path.is_dir():
                pattern = f"{name}/"
                check_name = name.rstrip("/")
            else:
                pattern = name
                check_name = name

            if check_name not in existing_lines and pattern not in seen:
                seen.add(pattern)
                entries.append(pattern)

        return entries
