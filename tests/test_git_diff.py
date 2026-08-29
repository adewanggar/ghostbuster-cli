"""Tests for Git Diff / Fast Scan mode."""

from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from ghostbuster.cli.app import app
from ghostbuster.core.git_diff import get_changed_files
from ghostbuster.core.models import Ghost, GhostCategory, Severity
from ghostbuster.core.scanner import ScanOrchestrator

runner = CliRunner()


class TestGitDiffHelper:
    """Tests for get_changed_files."""

    def test_non_git_directory_returns_empty_set(self, tmp_path: Path) -> None:
        """Should return empty set for a non-git directory."""
        changed = get_changed_files(tmp_path)
        assert len(changed) == 0

    def test_detects_untracked_and_modified_files(self, tmp_path: Path) -> None:
        """Should detect untracked and modified files in a git repo."""
        # Initialize git repo in tmp_path
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

        # Create committed file
        file1 = tmp_path / "initial.py"
        file1.write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True, check=True
        )

        # Modify file1 and create untracked file2
        file1.write_text("x = 2\n", encoding="utf-8")
        file2 = tmp_path / "untracked.py"
        file2.write_text("y = 3\n", encoding="utf-8")

        changed = get_changed_files(tmp_path)
        assert file1.resolve() in changed
        assert file2.resolve() in changed


class TestScanOrchestratorDiffFilter:
    """Tests for ScanOrchestrator filtering with changed_files."""

    def test_filters_ghosts_to_changed_files(self, tmp_path: Path) -> None:
        """Should only return ghosts originating in changed_files."""
        file_a = tmp_path / "a.py"
        file_b = tmp_path / "b.py"
        file_a.write_text("pass\n", encoding="utf-8")
        file_b.write_text("pass\n", encoding="utf-8")

        ghosts = [
            Ghost(
                category=GhostCategory.ZOMBIE_CODE,
                name="unused_a",
                message="unused in a",
                file_path=file_a,
                severity=Severity.LOW,
            ),
            Ghost(
                category=GhostCategory.ZOMBIE_CODE,
                name="unused_b",
                message="unused in b",
                file_path=file_b,
                severity=Severity.LOW,
            ),
        ]

        class MockScanner:
            name = "mock"

            def scan(self, path: Path) -> list[Ghost]:
                return ghosts

        orchestrator = ScanOrchestrator()
        orchestrator.register(MockScanner())

        # Only file_a changed
        result = orchestrator.run(tmp_path, changed_files={file_a})
        assert len(result.ghosts) == 1
        assert result.ghosts[0].name == "unused_a"


class TestScanCliDiffFlag:
    """Tests for CLI --diff flag."""

    def test_cli_diff_option_help(self) -> None:
        """--help should include --diff and --diff-base."""
        result = runner.invoke(app, ["scan", "--help"])
        assert result.exit_code == 0
        assert "--diff" in result.output
        assert "--diff-base" in result.output
