"""Tests for the Phantom Env Scanner."""

from __future__ import annotations

from pathlib import Path

from ghostbuster.core.models import GhostCategory
from ghostbuster.core.phantom_env import PhantomEnvScanner


class TestPhantomEnvScanner:
    """Tests for PhantomEnvScanner."""

    def setup_method(self) -> None:
        self.scanner = PhantomEnvScanner()

    def test_empty_project(self, tmp_path: Path) -> None:
        """Should return empty for a project with no env var usage."""
        (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        assert ghosts == []

    def test_detects_phantom_env_var(self, tmp_path: Path) -> None:
        """Should detect env vars referenced but not defined."""
        (tmp_path / "app.py").write_text(
            'import os\nval = os.environ["GHOST_VAR"]\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "GHOST_VAR" in ghost_names

    def test_detects_getenv_pattern(self, tmp_path: Path) -> None:
        """Should detect os.getenv() usage."""
        (tmp_path / "app.py").write_text(
            'import os\nval = os.getenv("MISSING_KEY")\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "MISSING_KEY" in ghost_names

    def test_detects_environ_get_pattern(self, tmp_path: Path) -> None:
        """Should detect os.environ.get() usage."""
        (tmp_path / "app.py").write_text(
            'import os\nval = os.environ.get("ANOTHER_MISSING")\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "ANOTHER_MISSING" in ghost_names

    def test_skips_if_defined_in_env_file(self, tmp_path: Path) -> None:
        """Should not flag vars that are defined in .env file."""
        (tmp_path / "app.py").write_text(
            'import os\nval = os.environ["DB_HOST"]\n',
            encoding="utf-8",
        )
        (tmp_path / ".env").write_text("DB_HOST=localhost\n", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "DB_HOST" not in ghost_names

    def test_skips_if_defined_in_env_example(self, tmp_path: Path) -> None:
        """Should not flag vars defined in .env.example."""
        (tmp_path / "app.py").write_text(
            'import os\nval = os.getenv("MY_VAR")\n',
            encoding="utf-8",
        )
        (tmp_path / ".env.example").write_text("MY_VAR=example_value\n", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "MY_VAR" not in ghost_names

    def test_ghost_category(self, tmp_path: Path) -> None:
        """All ghosts should have the PHANTOM_ENV category."""
        (tmp_path / "app.py").write_text(
            'import os\nos.environ["X"]\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        assert all(g.category == GhostCategory.PHANTOM_ENV for g in ghosts)

    def test_ghost_severity_is_high(self, tmp_path: Path) -> None:
        """Phantom env ghosts should be HIGH severity (runtime crash risk)."""
        (tmp_path / "app.py").write_text(
            'import os\nos.environ["CRASH_VAR"]\n',
            encoding="utf-8",
        )
        ghosts = self.scanner.scan(tmp_path)
        from ghostbuster.core.models import Severity

        assert all(g.severity == Severity.HIGH for g in ghosts)

    def test_parses_export_syntax(self, tmp_path: Path) -> None:
        """Should parse 'export KEY=value' syntax in .env files."""
        (tmp_path / "app.py").write_text(
            'import os\nos.environ["EXPORTED_VAR"]\n',
            encoding="utf-8",
        )
        (tmp_path / ".env").write_text("export EXPORTED_VAR=value\n", encoding="utf-8")
        ghosts = self.scanner.scan(tmp_path)
        ghost_names = {g.name for g in ghosts}
        assert "EXPORTED_VAR" not in ghost_names
