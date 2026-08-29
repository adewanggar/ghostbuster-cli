"""Orphan File Scanner — detects files/folders that should be in .gitignore.

Identifies large files, common build artifacts, dependency directories,
and other items that are tracked by git but shouldn't be.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory, Severity

# Directories that should almost always be in .gitignore
IGNORABLE_DIRS: dict[str, str] = {
    "node_modules": "Node.js dependencies directory",
    "venv": "Python virtual environment",
    ".venv": "Python virtual environment",
    "env": "Python virtual environment",
    ".env": "Python virtual environment",
    "__pycache__": "Python bytecode cache",
    ".pytest_cache": "Pytest cache",
    ".mypy_cache": "Mypy cache",
    ".ruff_cache": "Ruff cache",
    ".tox": "Tox environments",
    ".nox": "Nox environments",
    "dist": "Build distribution directory",
    "build": "Build output directory",
    ".eggs": "Python eggs directory",
    "*.egg-info": "Python egg-info directory",
    "htmlcov": "Coverage HTML report",
    ".coverage": "Coverage data file",
    ".hypothesis": "Hypothesis testing cache",
    "bower_components": "Bower dependencies",
    ".next": "Next.js build output",
    ".nuxt": "Nuxt.js build output",
    ".cache": "Generic cache directory",
    ".parcel-cache": "Parcel bundler cache",
    ".turbo": "Turborepo cache",
}

# File patterns that are commonly forgotten
IGNORABLE_PATTERNS: dict[str, str] = {
    ".pyc": "Python bytecode",
    ".pyo": "Python optimized bytecode",
    ".DS_Store": "macOS metadata",
    "Thumbs.db": "Windows thumbnail cache",
    ".env": "Environment variables file (may contain secrets)",
    ".env.local": "Local environment variables",
}

# Size threshold for flagging large files (10 MB)
LARGE_FILE_THRESHOLD = 10 * 1024 * 1024

# File extensions that are commonly large and shouldn't be in repos
LARGE_FILE_EXTENSIONS: set[str] = {
    ".h5", ".hdf5",        # ML model files
    ".pkl", ".pickle",     # Pickled data
    ".pt", ".pth",         # PyTorch models
    ".onnx",               # ONNX models
    ".bin",                # Generic binary
    ".db", ".sqlite",      # Databases
    ".sqlite3",
    ".csv",                # Data files (when large)
    ".parquet",
    ".zip", ".tar", ".gz", # Archives
    ".tar.gz", ".tgz",
    ".rar", ".7z",
    ".mp4", ".avi",        # Video files
    ".mov", ".mkv",
    ".iso",                # Disk images
}


class OrphanFileScanner:
    """Detects files and directories that should be in .gitignore."""

    name = "orphan-file"

    def scan(self, path: Path) -> list[Ghost]:
        """Scan a project directory for orphan files."""
        ghosts: list[Ghost] = []
        gitignore_patterns = self._load_gitignore(path)

        # Check for ignorable directories
        ghosts.extend(self._check_ignorable_dirs(path, gitignore_patterns))

        # Check for large files
        ghosts.extend(self._check_large_files(path))

        # Check for common forgotten files
        ghosts.extend(self._check_forgotten_files(path, gitignore_patterns))

        return ghosts

    def _load_gitignore(self, path: Path) -> set[str]:
        """Load patterns from .gitignore file."""
        gitignore = path / ".gitignore"
        if not gitignore.exists():
            return set()

        patterns: set[str] = set()
        try:
            for line in gitignore.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    # Normalize: remove trailing slashes for directory matching
                    patterns.add(line.rstrip("/"))
            return patterns
        except OSError:
            return set()

    def _is_in_gitignore(self, name: str, patterns: set[str]) -> bool:
        """Check if a name matches any gitignore pattern (simplified check)."""
        # Simple check: exact match or glob pattern
        if name in patterns:
            return True
        if name + "/" in patterns:
            return True
        if "/" + name in patterns:
            return True
        # Check wildcard patterns like *.pyc
        for pattern in patterns:
            if pattern.startswith("*") and name.endswith(pattern[1:]):
                return True
            if pattern.endswith("*") and name.startswith(pattern[:-1]):
                return True
            if pattern.endswith("/") and name == pattern[:-1]:
                return True
        return False

    def _check_ignorable_dirs(
        self, path: Path, gitignore_patterns: set[str]
    ) -> list[Ghost]:
        """Check for directories that should be in .gitignore."""
        ghosts: list[Ghost] = []

        for item in path.iterdir():
            if not item.is_dir():
                continue

            dir_name = item.name

            # Check known ignorable directories
            if dir_name in IGNORABLE_DIRS and not self._is_in_gitignore(dir_name, gitignore_patterns):
                # Calculate directory size for impact assessment
                size = self._get_dir_size(item)
                size_str = self._format_size(size)
                ghosts.append(
                    Ghost(
                        category=GhostCategory.ORPHAN_FILE,
                        name=dir_name,
                        message=(
                            f"Directory '{dir_name}/' ({size_str}) is "
                            f"{IGNORABLE_DIRS[dir_name]} and should be in .gitignore"
                        ),
                        file_path=item,
                        severity=Severity.HIGH if size > LARGE_FILE_THRESHOLD else Severity.MEDIUM,
                        fixable=True,
                        suggestion=f"Add '{dir_name}/' to .gitignore",
                    )
                )

            # Check for egg-info directories
            if dir_name.endswith(".egg-info") and not self._is_in_gitignore("*.egg-info", gitignore_patterns):
                ghosts.append(
                    Ghost(
                        category=GhostCategory.ORPHAN_FILE,
                        name=dir_name,
                        message=f"Directory '{dir_name}/' is a build artifact and should be in .gitignore",
                        file_path=item,
                        severity=Severity.MEDIUM,
                        fixable=True,
                        suggestion="Add '*.egg-info/' to .gitignore",
                    )
                )

        return ghosts

    def _check_large_files(self, path: Path) -> list[Ghost]:
        """Check for files that exceed the size threshold."""
        ghosts: list[Ghost] = []

        for item in path.rglob("*"):
            if not item.is_file():
                continue

            # Skip .git directory
            try:
                rel = item.relative_to(path)
            except ValueError:
                continue

            parts = rel.parts
            if any(
                p in {".git", "node_modules", "venv", ".venv", "__pycache__"}
                for p in parts
            ):
                continue

            try:
                size = item.stat().st_size
            except OSError:
                continue

            # Flag files with suspicious extensions regardless of size
            suffix = item.suffix.lower()
            if suffix in LARGE_FILE_EXTENSIONS and size > 1024 * 1024:  # > 1MB
                size_str = self._format_size(size)
                ghosts.append(
                    Ghost(
                        category=GhostCategory.ORPHAN_FILE,
                        name=item.name,
                        message=f"Large file '{rel}' ({size_str}) should probably not be in the repository",
                        file_path=item,
                        severity=Severity.HIGH if size > LARGE_FILE_THRESHOLD else Severity.MEDIUM,
                        fixable=True,
                        suggestion=f"Add '{item.name}' to .gitignore and use Git LFS or external storage",
                    )
                )
            elif size > LARGE_FILE_THRESHOLD:
                size_str = self._format_size(size)
                ghosts.append(
                    Ghost(
                        category=GhostCategory.ORPHAN_FILE,
                        name=item.name,
                        message=f"File '{rel}' ({size_str}) exceeds {self._format_size(LARGE_FILE_THRESHOLD)} threshold",
                        file_path=item,
                        severity=Severity.HIGH,
                        fixable=False,
                        suggestion=f"Consider adding '{item.name}' to .gitignore or using Git LFS",
                    )
                )

        return ghosts

    def _check_forgotten_files(
        self, path: Path, gitignore_patterns: set[str]
    ) -> list[Ghost]:
        """Check for common files that should be gitignored."""
        ghosts: list[Ghost] = []

        for item in path.iterdir():
            if not item.is_file():
                continue

            name = item.name

            # Check specific filenames
            if name in IGNORABLE_PATTERNS and not self._is_in_gitignore(
                name, gitignore_patterns
            ):
                ghosts.append(
                    Ghost(
                        category=GhostCategory.ORPHAN_FILE,
                        name=name,
                        message=f"File '{name}' ({IGNORABLE_PATTERNS[name]}) should be in .gitignore",
                        file_path=item,
                        severity=Severity.LOW if name in {".DS_Store", "Thumbs.db"} else Severity.MEDIUM,
                        fixable=True,
                        suggestion=f"Add '{name}' to .gitignore",
                    )
                )

        return ghosts

    def _get_dir_size(self, path: Path, max_depth: int = 3) -> int:
        """Calculate approximate directory size (limited depth for speed)."""
        total = 0
        depth = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    with contextlib.suppress(OSError):
                        total += item.stat().st_size
                # Simple depth tracking
                depth += 1
                if depth > 10000:  # Safety limit
                    break
        except OSError:
            pass
        return total

    @staticmethod
    def _format_size(size: int) -> str:
        """Format a file size in human-readable format."""
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size //= 1024
        return f"{size:.1f} TB"
