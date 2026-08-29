"""Data models for ghost findings, scan results, and scoring."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path


class GhostCategory(str, enum.Enum):
    """Categories of ghosts that can haunt a codebase."""

    DEAD_IMPORT = "dead-import"
    ORPHAN_FILE = "orphan-file"
    ZOMBIE_CODE = "zombie-code"
    PHANTOM_ENV = "phantom-env"

    @property
    def emoji(self) -> str:
        """Return category tag for display."""
        return ""

    @property
    def label(self) -> str:
        """Return a human-readable label for each category."""
        return {
            GhostCategory.DEAD_IMPORT: "Dead Import",
            GhostCategory.ORPHAN_FILE: "Orphan File",
            GhostCategory.ZOMBIE_CODE: "Zombie Code",
            GhostCategory.PHANTOM_ENV: "Phantom Env",
        }[self]

    @property
    def description(self) -> str:
        """Return a short description for each category."""
        return {
            GhostCategory.DEAD_IMPORT: "Dependency declared but never imported",
            GhostCategory.ORPHAN_FILE: "File/folder that should be in .gitignore",
            GhostCategory.ZOMBIE_CODE: "Function or class that is never called",
            GhostCategory.PHANTOM_ENV: "Env var referenced but never set",
        }[self]


class Severity(str, enum.Enum):
    """How severe this finding is."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def emoji(self) -> str:
        return ""


@dataclass(frozen=True)
class Ghost:
    """A single ghost finding in the codebase.

    This is the atomic unit of a scan result. Each ghost represents one
    specific issue found (e.g., one unused import, one orphan file).
    """

    category: GhostCategory
    name: str
    message: str
    file_path: Path | None = None
    line_number: int | None = None
    severity: Severity = Severity.MEDIUM
    fixable: bool = False
    suggestion: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "category": self.category.value,
            "name": self.name,
            "message": self.message,
            "file_path": str(self.file_path) if self.file_path else None,
            "line_number": self.line_number,
            "severity": self.severity.value,
            "fixable": self.fixable,
            "suggestion": self.suggestion,
        }


@dataclass
class GhostScore:
    """The overall 'hauntedness' score for a codebase.

    Score ranges from 0 (clean) to 100 (extremely haunted).
    """

    value: int
    label: str
    breakdown: dict[GhostCategory, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "score": self.value,
            "label": self.label,
            "breakdown": {k.value: v for k, v in self.breakdown.items()},
        }


@dataclass
class ScanResult:
    """Complete result of a ghostbuster scan."""

    ghosts: list[Ghost] = field(default_factory=list)
    score: GhostScore | None = None
    scanned_path: Path | None = None
    duration_ms: float = 0.0

    @property
    def ghost_count(self) -> int:
        return len(self.ghosts)

    @property
    def fixable_count(self) -> int:
        return sum(1 for g in self.ghosts if g.fixable)

    def ghosts_by_category(self) -> dict[GhostCategory, list[Ghost]]:
        """Group ghosts by their category."""
        result: dict[GhostCategory, list[Ghost]] = {}
        for ghost in self.ghosts:
            result.setdefault(ghost.category, []).append(ghost)
        return result

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "ghosts": [g.to_dict() for g in self.ghosts],
            "ghost_count": self.ghost_count,
            "fixable_count": self.fixable_count,
            "score": self.score.to_dict() if self.score else None,
            "scanned_path": str(self.scanned_path) if self.scanned_path else None,
            "duration_ms": round(self.duration_ms, 2),
        }
