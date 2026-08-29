"""Tests for the Dead Import Scanner."""

from __future__ import annotations

from pathlib import Path

from ghostbuster.core.dead_imports import DeadImportScanner
from ghostbuster.core.models import GhostCategory


class TestDeadImportScanner:
    """Tests for DeadImportScanner."""

    def setup_method(self) -> None:
        self.scanner = DeadImportScanner()

    def test_no_requirements_file(self, tmp_path: Path) -> None:
        """Should return empty list when no dependency file exists."""
        (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        assert ghosts == []

    def test_all_deps_used(self, tmp_path: Path) -> None:
        """Should return empty list when all deps are imported."""
        (tmp_path / "requirements.txt").write_text("requests\n", encoding="utf-8")
        (tmp_path / "app.py").write_text("import requests\n", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        assert ghosts == []

    def test_finds_unused_dep(self, project_with_requirements: Path) -> None:
        """Should detect dependencies that are never imported."""
        ghosts = self.scanner.scan(project_with_requirements)

        ghost_names = {g.name for g in ghosts}
        # flask and numpy are in requirements.txt but never imported
        assert "flask" in ghost_names
        assert "numpy" in ghost_names
        # requests IS imported, so should NOT be flagged
        assert "requests" not in ghost_names

    def test_finds_unused_dep_pyproject(self, project_with_pyproject: Path) -> None:
        """Should detect unused deps from pyproject.toml."""
        ghosts = self.scanner.scan(project_with_pyproject)

        ghost_names = {g.name for g in ghosts}
        # click is in pyproject.toml but never imported
        assert "click" in ghost_names
        # requests and pyyaml (imported as yaml) ARE used
        assert "requests" not in ghost_names
        assert "pyyaml" not in ghost_names

    def test_finds_unused_dep_poetry(self, tmp_path: Path) -> None:
        """Should detect unused deps defined in Poetry format."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[tool.poetry.dependencies]\npython = "^3.10"\nrequests = "^2.28.0"\nredis = "^4.0.0"\n',
            encoding="utf-8",
        )
        app = tmp_path / "app.py"
        app.write_text("import requests\n", encoding="utf-8")

        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "redis" in ghost_names
        assert "requests" not in ghost_names
        assert "python" not in ghost_names

    def test_ghost_category(self, project_with_requirements: Path) -> None:
        """All ghosts should have the DEAD_IMPORT category."""
        ghosts = self.scanner.scan(project_with_requirements)
        assert all(g.category == GhostCategory.DEAD_IMPORT for g in ghosts)

    def test_ghost_is_fixable(self, project_with_requirements: Path) -> None:
        """Dead import ghosts should be marked as fixable."""
        ghosts = self.scanner.scan(project_with_requirements)
        assert all(g.fixable for g in ghosts)

    def test_skips_tool_packages(self, tmp_path: Path) -> None:
        """Should not flag known tool-only packages (pytest, ruff, etc.)."""
        (tmp_path / "requirements.txt").write_text(
            "pytest\nruff\nmypy\nblack\n",
            encoding="utf-8",
        )
        (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        assert ghosts == []

    def test_normalizes_package_names(self) -> None:
        """Package names should be normalized (lowercase, hyphens to underscores)."""
        assert self.scanner._normalize_package_name("Flask") == "flask"
        assert self.scanner._normalize_package_name("scikit-learn") == "scikit_learn"
        assert self.scanner._normalize_package_name("PyYAML>=6.0") == "pyyaml"
        assert self.scanner._normalize_package_name("requests[security]") == "requests"

    def test_skips_venv_directory(self, tmp_path: Path) -> None:
        """Should not scan files inside venv directories."""
        (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
        venv = tmp_path / "venv" / "lib"
        venv.mkdir(parents=True)
        # Even though flask is imported in venv, it should not count
        (venv / "flask_usage.py").write_text("import flask\n", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "flask" in ghost_names
