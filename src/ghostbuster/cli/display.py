"""Rich console display helpers for ghostbuster output.

All terminal formatting lives here — the core logic never imports Rich.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from ghostbuster.core.models import ScanResult

console = Console()
error_console = Console(stderr=True)


def print_banner() -> None:
    """Print the ghostbuster ASCII banner."""
    banner = Text()
    banner.append("G H O S T B U S T E R", style="bold cyan")
    banner.append("\n")
    banner.append("Find and bust the ghosts haunting your codebase", style="dim")

    console.print(
        Panel(
            banner,
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print()


def print_scanning_start(path: str, scanner_names: list[str]) -> None:
    """Print the scan start message."""
    console.print(f"  Scanning [bold cyan]{path}[/bold cyan]")
    console.print(f"  Scanners: [dim]{', '.join(scanner_names)}[/dim]")
    console.print()


def print_scan_result(result: ScanResult, verbose: bool = False) -> None:
    """Print the full scan result with ghost table and score card."""
    if not result.ghosts:
        _print_clean_result(result)
        return

    _print_ghost_table(result, verbose)
    console.print()
    _print_category_summary(result)
    console.print()
    _print_score_card(result)
    _print_footer(result)


def print_scan_result_json(result: ScanResult) -> None:
    """Print scan result as JSON (for scripting/CI)."""
    console.print_json(json.dumps(result.to_dict(), indent=2))


def print_scan_result_markdown(result: ScanResult) -> None:
    """Print scan result as markdown (for pasting into issues/PRs)."""
    if result.score:
        console.print(f"# Ghost Score: {result.score.value}/100")
        console.print(f"_{result.score.label}_")
        console.print()

    if not result.ghosts:
        console.print("No ghosts found!")
        return

    console.print(f"**{result.ghost_count} ghosts found** ({result.fixable_count} auto-fixable)")
    console.print()

    by_category = result.ghosts_by_category()
    for category, ghosts in by_category.items():
        console.print(f"## {category.label} ({len(ghosts)})")
        console.print()
        for ghost in ghosts:
            location = ""
            if ghost.file_path:
                location = f" - `{ghost.file_path.name}"
                if ghost.line_number:
                    location += f":{ghost.line_number}"
                location += "`"
            console.print(f"- **{ghost.name}**: {ghost.message}{location}")
        console.print()


def print_bust_preview(changes: list[str]) -> None:
    """Print a preview of changes that would be made in bust mode."""
    if not changes:
        console.print("  [green]Nothing to fix - your codebase is clean![/green]")
        return

    console.print(f"  [bold yellow]{len(changes)} fixes available (dry-run):[/bold yellow]")
    console.print()
    for change in changes:
        console.print(f"  [dim]{change}[/dim]")
    console.print()
    console.print("  [dim]Run with [bold]--confirm[/bold] to apply these fixes.[/dim]")


def print_bust_applied(changes: list[str]) -> None:
    """Print the results of applied fixes."""
    if not changes:
        console.print("  [green]Nothing to fix![/green]")
        return

    console.print(f"  [bold green]Applied {len(changes)} fixes:[/bold green]")
    console.print()
    for change in changes:
        console.print(f"  [green]{change}[/green]")


def print_error(message: str, hint: str = "") -> None:
    """Print a user-friendly error message."""
    error_console.print(f"  [bold red]Error:[/bold red] {message}")
    if hint:
        error_console.print(f"  [dim]Hint: {hint}[/dim]")


def _print_clean_result(result: ScanResult) -> None:
    """Print the all-clear message when no ghosts are found."""
    msg = Text()
    msg.append("No ghosts detected!\n", style="bold green")
    msg.append("Your codebase is squeaky clean.", style="green")

    console.print(
        Panel(
            msg,
            border_style="green",
            title="[bold green]Ghost Report[/bold green]",
            padding=(1, 2),
        )
    )
    if result.duration_ms > 0:
        console.print(f"  [dim]Completed in {result.duration_ms:.0f}ms[/dim]")


def _print_ghost_table(result: ScanResult, verbose: bool) -> None:
    """Print the table of found ghosts."""
    table = Table(
        title="Ghosts Found",
        title_style="bold red",
        border_style="red",
        show_lines=verbose,
        padding=(0, 1),
    )

    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Category", style="cyan", width=14)
    table.add_column("Severity", width=8, justify="center")
    table.add_column("Name", style="bold", max_width=30)
    table.add_column("Message", max_width=60)
    if verbose:
        table.add_column("Location", style="dim", max_width=30)
        table.add_column("Fix", style="green dim", max_width=30)

    for i, ghost in enumerate(result.ghosts, 1):
        row = [
            str(i),
            ghost.category.label,
            ghost.severity.value.upper(),
            ghost.name,
            ghost.message,
        ]
        if verbose:
            location = ""
            if ghost.file_path:
                location = ghost.file_path.name
                if ghost.line_number:
                    location += f":{ghost.line_number}"
            row.append(location)
            row.append(ghost.suggestion if ghost.fixable else "-")

        table.add_row(*row)

    console.print(table)


def _print_category_summary(result: ScanResult) -> None:
    """Print a summary breakdown by category."""
    by_category = result.ghosts_by_category()

    table = Table(
        title="Breakdown by Category",
        title_style="bold",
        border_style="dim",
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right", style="bold")
    table.add_column("Fixable", justify="right", style="green")
    table.add_column("Description", style="dim")

    for category in sorted(by_category.keys(), key=lambda c: len(by_category[c]), reverse=True):
        ghosts = by_category[category]
        fixable = sum(1 for g in ghosts if g.fixable)
        table.add_row(
            category.label,
            str(len(ghosts)),
            str(fixable) if fixable > 0 else "-",
            category.description,
        )

    console.print(table)


def _print_score_card(result: ScanResult) -> None:
    """Print the Ghost Score card."""
    if not result.score:
        return

    score = result.score
    score_val = score.value

    # Color based on score severity
    if score_val == 0 or score_val <= 20:
        color = "green"
        bar_char = "#"
    elif score_val <= 50:
        color = "yellow"
        bar_char = "#"
    elif score_val <= 80:
        color = "red"
        bar_char = "#"
    else:
        color = "bold red"
        bar_char = "#"

    # Build the score bar (50 chars wide)
    bar_width = 50
    filled = int(score_val / 100 * bar_width)
    empty = bar_width - filled
    bar = f"[{color}]{bar_char * filled}[/{color}][dim]{'-' * empty}[/dim]"

    content = f"  [bold {color}]{score_val}[/bold {color}] / 100\n\n  {bar}\n\n  {score.label}"

    console.print(
        Panel(
            content,
            title=f"[bold {color}]Ghost Score[/bold {color}]",
            border_style=color,
            padding=(1, 2),
            width=62,
        )
    )


def _print_footer(result: ScanResult) -> None:
    """Print the scan footer with stats."""
    console.print()
    parts = []
    if result.ghost_count > 0:
        parts.append(f"[bold]{result.ghost_count}[/bold] ghosts found")
    if result.fixable_count > 0:
        parts.append(f"[green]{result.fixable_count}[/green] auto-fixable")
    if result.duration_ms > 0:
        parts.append(f"Completed in {result.duration_ms:.0f}ms")

    if parts:
        console.print("  " + " | ".join(parts))

    if result.fixable_count > 0:
        console.print(
            "\n  [dim]Run [bold]ghostbuster bust --confirm[/bold] to auto-fix what we can.[/dim]"
        )
    console.print()
