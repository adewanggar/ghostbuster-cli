"""Bust command — auto-fix ghost findings.

Usage:
    ghostbuster bust [PATH] [OPTIONS]
    ghostbuster bust .                    # dry-run by default (safe)
    ghostbuster bust . --confirm          # actually apply fixes
    ghostbuster bust --category dead-import --confirm
"""

from __future__ import annotations

from pathlib import Path

import typer

from ghostbuster.cli.display import (
    console,
    print_banner,
    print_bust_applied,
    print_bust_preview,
    print_error,
)
from ghostbuster.core.models import GhostCategory
from ghostbuster.core.scanner import create_default_orchestrator
from ghostbuster.fixers.import_fixer import ImportFixer


def bust(
    path: Path = typer.Argument(
        Path("."),
        help="Path to the project directory to fix.",
        exists=True,
        file_okay=False,
        resolve_path=True,
    ),
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="Actually apply fixes. Without this flag, only shows what would be changed (dry-run).",
    ),
    category: list[str] | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Only fix specific categories.",
    ),
    no_color: bool = typer.Option(
        False,
        "--no-color",
        help="Disable colored output.",
    ),
) -> None:
    """Bust the ghosts - auto-fix findings in your codebase.

    By default, runs in dry-run mode (shows what would be fixed).
    Use --confirm to actually apply the fixes.

    Examples:
        ghostbuster bust                      # preview changes (safe)
        ghostbuster bust --confirm            # apply fixes
        ghostbuster bust -c dead-import --confirm
    """
    if no_color:
        console.no_color = True

    # Validate categories
    valid_categories = {c.value for c in GhostCategory}
    if category:
        for cat in category:
            if cat not in valid_categories:
                print_error(
                    f"Unknown category: '{cat}'",
                    f"Valid categories: {', '.join(sorted(valid_categories))}",
                )
                raise typer.Exit(1)

    print_banner()

    if confirm:
        console.print("  [bold yellow]LIVE MODE[/bold yellow] - changes will be applied!\n")
    else:
        console.print("  [bold cyan]DRY-RUN MODE[/bold cyan] - no changes will be made.\n")

    # First, scan to find ghosts
    try:
        orchestrator = create_default_orchestrator()

        with console.status("[cyan]Scanning for fixable ghosts...[/cyan]", spinner="dots"):
            result = orchestrator.run(path, categories=category)

    except Exception as exc:
        print_error(f"Scan failed: {exc}")
        raise typer.Exit(1) from exc

    # Filter to only fixable ghosts
    fixable_ghosts = [g for g in result.ghosts if g.fixable]

    if not fixable_ghosts:
        console.print("  [green]No fixable ghosts found. Your codebase is clean![/green]\n")
        return

    console.print(f"  Found [bold]{len(fixable_ghosts)}[/bold] fixable ghosts.\n")

    # Apply fixes per category
    fixer = ImportFixer()

    if confirm:
        changes = fixer.fix(fixable_ghosts, path)
        print_bust_applied(changes)
        console.print(
            "\n  [bold green]Ghostbusting complete![/bold green] "
            "Don't forget to review the changes and run your tests.\n"
        )
    else:
        changes = fixer.preview(fixable_ghosts, path)
        print_bust_preview(changes)
