"""Auto-fix modules for resolving ghost findings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from ghostbuster.fixers.env_fixer import EnvFixer
from ghostbuster.fixers.gitignore_fixer import GitignoreFixer
from ghostbuster.fixers.import_fixer import ImportFixer

if TYPE_CHECKING:
    from pathlib import Path

    from ghostbuster.core.models import Ghost


class Fixer(Protocol):
    """Protocol that all fixers must implement."""

    def preview(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Return preview of changes without applying them."""
        ...

    def fix(self, ghosts: list[Ghost], path: Path) -> list[str]:
        """Apply fixes and return list of changes made."""
        ...


__all__ = ["EnvFixer", "Fixer", "GitignoreFixer", "ImportFixer"]
