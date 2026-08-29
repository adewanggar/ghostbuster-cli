"""Main Typer application — entry point for the ghostbuster CLI.

This module ties together all sub-commands and global options.
"""

from __future__ import annotations

import typer

import ghostbuster
from ghostbuster.cli.bust import bust
from ghostbuster.cli.scan import scan

app = typer.Typer(
    name="ghostbuster",
    help="Find and bust the ghosts haunting your codebase.",
    no_args_is_help=False,
    add_completion=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,
)


def _version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"ghostbuster {ghostbuster.__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool | None = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show full stack traces on error.",
        envvar="GHOSTBUSTER_DEBUG",
    ),
) -> None:
    """Ghostbuster - Find and bust the ghosts haunting your codebase.

    Run [bold cyan]ghostbuster scan[/bold cyan] to detect issues, or
    [bold cyan]ghostbuster bust[/bold cyan] to auto-fix them.

    [dim]Examples:[/dim]
        ghostbuster scan                    # Scan current directory
        ghostbuster scan ./my-project -v    # Verbose scan
        ghostbuster scan --format json      # JSON output for CI
        ghostbuster bust --confirm          # Auto-fix issues
    """
    # Store debug flag in context for sub-commands
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

    # If no sub-command is given, run scan with defaults
    if ctx.invoked_subcommand is None:
        ctx.invoke(scan)


# Register sub-commands
app.command(name="scan")(scan)
app.command(name="bust")(bust)


if __name__ == "__main__":
    app()
