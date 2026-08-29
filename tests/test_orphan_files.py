"""Tests for the Orphan File Scanner."""

from __future__ import annotations

from pathlib import Path

from ghostbuster.core.models import GhostCategory
from ghostbuster.core.orphan_files import OrphanFileScanner


class TestOrphanFileScanner:
    """Tests for OrphanFileScanner."""

    def setup_method(self) -> None:
        self.scanner = OrphanFileScanner()

    def test_empty_project(self, tmp_path: Path) -> None:
        """Should return empty list for a project with no orphan files."""
        (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        assert ghosts == []

    def test_detects_node_modules(self, project_with_orphans: Path) -> None:
        """Should detect unignored node_modules directory."""
        ghosts = self.scanner.scan(project_with_orphans)
        ghost_names = {g.name for g in ghosts}
        assert "node_modules" in ghost_names

    def test_detects_pycache(self, project_with_orphans: Path) -> None:
        """Should detect unignored __pycache__ directory."""
        ghosts = self.scanner.scan(project_with_orphans)
        ghost_names = {g.name for g in ghosts}
        assert "__pycache__" in ghost_names

    def test_detects_venv(self, project_with_orphans: Path) -> None:
        """Should detect unignored venv directory."""
        ghosts = self.scanner.scan(project_with_orphans)
        ghost_names = {g.name for g in ghosts}
        assert "venv" in ghost_names

    def test_skips_if_gitignored(self, project_with_orphans: Path) -> None:
        """Should not flag directories that are already in .gitignore."""
        gitignore = project_with_orphans / ".gitignore"
        gitignore.write_text("node_modules/\n__pycache__/\nvenv/\n", encoding="utf-8")

        ghosts = self.scanner.scan(project_with_orphans)
        ghost_names = {g.name for g in ghosts}
        assert "node_modules" not in ghost_names
        assert "__pycache__" not in ghost_names
        assert "venv" not in ghost_names

    def test_ghost_category(self, project_with_orphans: Path) -> None:
        """All ghosts should have the ORPHAN_FILE category."""
        ghosts = self.scanner.scan(project_with_orphans)
        assert all(g.category == GhostCategory.ORPHAN_FILE for g in ghosts)

    def test_detects_ds_store(self, tmp_path: Path) -> None:
        """Should detect .DS_Store files."""
        (tmp_path / ".DS_Store").write_bytes(b"\x00" * 10)
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert ".DS_Store" in ghost_names

    def test_detects_large_files(self, tmp_path: Path) -> None:
        """Should detect files with suspicious extensions over 1MB."""
        large_file = tmp_path / "model.pkl"
        large_file.write_bytes(b"\x00" * (2 * 1024 * 1024))  # 2MB
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "model.pkl" in ghost_names

    def test_format_size(self) -> None:
        """Should format file sizes correctly."""
        assert OrphanFileScanner._format_size(500) == "500.0 B"
        assert OrphanFileScanner._format_size(1024) == "1.0 KB"
        assert OrphanFileScanner._format_size(1024 * 1024) == "1.0 MB"
