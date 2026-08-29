"""Integration tests for the ghostbuster CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from ghostbuster.cli.app import app

runner = CliRunner()


class TestCLI:
    """Integration tests for CLI commands."""

    def test_version_flag(self) -> None:
        """--version should print version and exit 0."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "ghostbuster" in result.output
        assert "0.2.0" in result.output

    def test_help_flag(self) -> None:
        """--help should print help text."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ghostbuster" in result.output.lower() or "ghost" in result.output.lower()

    def test_scan_help(self) -> None:
        """scan --help should print scan-specific help."""
        result = runner.invoke(app, ["scan", "--help"])
        assert result.exit_code == 0
        assert "scan" in result.output.lower()

    def test_bust_help(self) -> None:
        """bust --help should print bust-specific help."""
        result = runner.invoke(app, ["bust", "--help"])
        assert result.exit_code == 0
        assert "bust" in result.output.lower()

    def test_scan_clean_project(self, tmp_path: str) -> None:
        """Scanning a clean project should exit 0."""
        result = runner.invoke(app, ["scan", str(tmp_path)])
        # A clean project with no Python files should exit 0
        assert result.exit_code == 0

    def test_scan_json_output(self, tmp_path: str) -> None:
        """--format json should produce valid JSON."""
        result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        import json

        data = json.loads(result.output)
        assert "ghosts" in data
        assert "ghost_count" in data
        assert "score" in data

    def test_scan_invalid_category(self, tmp_path: str) -> None:
        """Invalid category should produce a helpful error."""
        result = runner.invoke(app, ["scan", str(tmp_path), "--category", "fake-category"])
        assert result.exit_code == 1

    def test_scan_markdown_output(self, tmp_path: str) -> None:
        """--format markdown should produce markdown text."""
        result = runner.invoke(app, ["scan", str(tmp_path), "--format", "markdown"])
        assert result.exit_code == 0
