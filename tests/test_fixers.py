"""Tests for Ghostbuster auto-fixers."""

from __future__ import annotations

from pathlib import Path

from ghostbuster.core.models import Ghost, GhostCategory, Severity
from ghostbuster.fixers.env_fixer import EnvFixer
from ghostbuster.fixers.gitignore_fixer import GitignoreFixer


class TestGitignoreFixer:
    """Tests for GitignoreFixer."""

    def test_preview_gitignore_changes(self, tmp_path: Path) -> None:
        """Should preview adding orphan directories/files to .gitignore."""
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()

        ghosts = [
            Ghost(
                category=GhostCategory.ORPHAN_FILE,
                name="node_modules",
                message="Directory node_modules should be in .gitignore",
                file_path=node_modules,
                severity=Severity.HIGH,
                fixable=True,
            ),
            Ghost(
                category=GhostCategory.ORPHAN_FILE,
                name=".DS_Store",
                message="File .DS_Store should be in .gitignore",
                file_path=tmp_path / ".DS_Store",
                severity=Severity.LOW,
                fixable=True,
            ),
        ]

        fixer = GitignoreFixer()
        preview = fixer.preview(ghosts, tmp_path)

        assert len(preview) == 2
        assert any("node_modules/" in p for p in preview)
        assert any(".DS_Store" in p for p in preview)
        # .gitignore should NOT be created during preview
        assert not (tmp_path / ".gitignore").exists()

    def test_apply_gitignore_fix(self, tmp_path: Path) -> None:
        """Should append missing entries to .gitignore."""
        (tmp_path / "venv").mkdir()
        (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")

        ghosts = [
            Ghost(
                category=GhostCategory.ORPHAN_FILE,
                name="venv",
                message="venv should be in .gitignore",
                file_path=tmp_path / "venv",
                severity=Severity.HIGH,
                fixable=True,
            ),
        ]

        fixer = GitignoreFixer()
        applied = fixer.fix(ghosts, tmp_path)

        assert len(applied) == 1
        content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
        assert "__pycache__/\n" in content
        assert "venv/\n" in content

    def test_skips_already_ignored_entries(self, tmp_path: Path) -> None:
        """Should not add duplicate entries."""
        (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        (tmp_path / "node_modules").mkdir()

        ghosts = [
            Ghost(
                category=GhostCategory.ORPHAN_FILE,
                name="node_modules",
                message="Directory node_modules",
                file_path=tmp_path / "node_modules",
                severity=Severity.HIGH,
                fixable=True,
            ),
        ]

        fixer = GitignoreFixer()
        applied = fixer.fix(ghosts, tmp_path)
        assert len(applied) == 0


class TestEnvFixer:
    """Tests for EnvFixer."""

    def test_preview_env_changes(self, tmp_path: Path) -> None:
        """Should preview adding missing env keys to .env.example."""
        ghosts = [
            Ghost(
                category=GhostCategory.PHANTOM_ENV,
                name="DATABASE_URL",
                message="DATABASE_URL is missing",
                severity=Severity.HIGH,
                fixable=True,
            ),
            Ghost(
                category=GhostCategory.PHANTOM_ENV,
                name="STRIPE_SECRET_KEY",
                message="STRIPE_SECRET_KEY is missing",
                severity=Severity.HIGH,
                fixable=True,
            ),
        ]

        fixer = EnvFixer()
        preview = fixer.preview(ghosts, tmp_path)

        assert len(preview) == 2
        assert any("DATABASE_URL=" in p for p in preview)
        assert any("STRIPE_SECRET_KEY=" in p for p in preview)
        assert not (tmp_path / ".env.example").exists()

    def test_apply_env_fix(self, tmp_path: Path) -> None:
        """Should create .env.example and append missing keys."""
        ghosts = [
            Ghost(
                category=GhostCategory.PHANTOM_ENV,
                name="API_KEY",
                message="API_KEY is missing",
                severity=Severity.HIGH,
                fixable=True,
            ),
        ]

        fixer = EnvFixer()
        applied = fixer.fix(ghosts, tmp_path)

        assert len(applied) == 1
        env_example = tmp_path / ".env.example"
        assert env_example.exists()
        content = env_example.read_text(encoding="utf-8")
        assert "API_KEY=\n" in content

    def test_preserves_existing_keys_in_env_example(self, tmp_path: Path) -> None:
        """Should append new keys without duplicating existing ones."""
        (tmp_path / ".env.example").write_text("EXISTING_KEY=123\n", encoding="utf-8")

        ghosts = [
            Ghost(
                category=GhostCategory.PHANTOM_ENV,
                name="EXISTING_KEY",
                message="Already in example",
                severity=Severity.HIGH,
                fixable=True,
            ),
            Ghost(
                category=GhostCategory.PHANTOM_ENV,
                name="NEW_KEY",
                message="New key",
                severity=Severity.HIGH,
                fixable=True,
            ),
        ]

        fixer = EnvFixer()
        applied = fixer.fix(ghosts, tmp_path)

        assert len(applied) == 1
        content = (tmp_path / ".env.example").read_text(encoding="utf-8")
        assert "EXISTING_KEY=123\n" in content
        assert "NEW_KEY=\n" in content
