"""Scan command — the primary ghostbuster command.

Usage:
    ghostbuster scan [PATH] [OPTIONS]
    ghostbuster scan .
    ghostbuster scan --format json
    ghostbuster scan --category dead-import --verbose
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer

from ghostbuster.cli.display import (
    console,
    print_banner,
    print_error,
    print_scan_result,
    print_scan_result_json,
    print_scan_result_markdown,
    print_scanning_start,
)
from ghostbuster.core.git_diff import get_changed_files
from ghostbuster.core.models import GhostCategory
from ghostbuster.core.scanner import create_default_orchestrator


class OutputFormat(str, Enum):
    """Output format for scan results."""

    rich = "rich"
    json = "json"
    markdown = "markdown"


def scan(
    path: Path = typer.Argument(
        Path("."),
        help="Path to the project directory to scan.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.rich,
        "--format",
        "-f",
        help="Output format: rich (colorful), json (machine-readable), markdown (for issues/PRs).",
    ),
    category: list[str] | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Only scan specific categories (dead-import, orphan-file, zombie-code, phantom-env).",
    ),
    diff: bool = typer.Option(
        False,
        "--diff",
        "-d",
        help="Incremental fast scan: only scan modified, staged, and untracked files.",
    ),
    diff_base: str | None = typer.Option(
        None,
        "--diff-base",
        help="Compare changed files against a specific git ref/branch (e.g. main, origin/main, HEAD~1).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed findings with locations and fix suggestions.",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output.",
    ),
) -> None:
    """Scan your codebase for ghosts.

    Searches for dead imports, orphan files, zombie code, and phantom
    environment variables in your project.

    Examples:
        ghostbuster scan
        ghostbuster scan --diff
        ghostbuster scan --diff-base origin/main
        ghostbuster scan ./my-project --verbose
        ghostbuster scan --format json --category dead-import
    """
    if no_color:
        console.no_color = True

    # Validate categories if provided
    valid_categories = {c.value for c in GhostCategory}
    if category:
        for cat in category:
            if cat not in valid_categories:
                print_error(
                    f"Unknown category: '{cat}'",
                    f"Valid categories: {', '.join(sorted(valid_categories))}",
                )
                raise typer.Exit(1)

    # Handle diff mode
    changed_files: set[Path] | None = None
    if diff or diff_base:
        changed_files = get_changed_files(path, base_ref=diff_base)

    # Show banner for rich format
    if format == OutputFormat.rich:
        print_banner()
        print_scanning_start(str(path), _get_scanner_names(category))
        if diff or diff_base:
            console.print(
                f"  [cyan]Diff mode active ({len(changed_files or set())} changed files analyzed)[/cyan]\n"
            )

    # Run the scan
    try:
        orchestrator = create_default_orchestrator()

        with (
            console.status("[cyan]Hunting for ghosts...[/cyan]", spinner="dots")
            if format == OutputFormat.rich
            else _nullcontext()
        ):
            result = orchestrator.run(
                path,
                categories=category,
                changed_files=changed_files if (diff or diff_base) else None,
            )

    except Exception as exc:
        print_error(f"Scan failed: {exc}", "Run with --debug flag for full traceback.")
        raise typer.Exit(1) from exc

    # Display results
    if format == OutputFormat.json:
        print_scan_result_json(result)
    elif format == OutputFormat.markdown:
        print_scan_result_markdown(result)
    else:
        print_scan_result(result, verbose=verbose)

    # Exit with non-zero code if ghosts were found (useful for CI)
    if result.ghost_count > 0:
        raise typer.Exit(1)


def _get_scanner_names(categories: list[str] | None) -> list[str]:
    """Get human-readable scanner names."""
    if categories:
        return categories
    return ["dead-import", "orphan-file", "zombie-code", "phantom-env"]


class _nullcontext:
    """Simple null context manager for Python 3.10 compatibility."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *args: object) -> None:
        pass
