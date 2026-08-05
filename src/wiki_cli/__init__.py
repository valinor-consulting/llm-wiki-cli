"""llm-wiki: scaffold and upgrade an LLM-maintained knowledge wiki."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from . import _scaffold, _skills, _upgrade

app = typer.Typer(
    add_completion=False,
    help="Scaffold and upgrade an LLM-maintained knowledge wiki for Claude Code and Codex.",
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(_upgrade.package_version())
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed llm-wiki-cli version and exit.",
    ),
) -> None:
    """Scaffold and upgrade an LLM-maintained knowledge wiki."""


@app.command()
def init(
    directory: str = typer.Argument(..., help="Target directory for the new wiki."),
    no_skills: bool = typer.Option(
        False,
        "--no-skills",
        help="Skip optional commands, skills, and hooks for both agents.",
    ),
    force: bool = typer.Option(
        False, "--force", help="Allow scaffolding into a non-empty directory."
    ),
) -> None:
    """Create a new LLM wiki in DIRECTORY."""
    target = _scaffold.resolve_target(directory, force=force)
    _scaffold.copy_template(target)
    if not no_skills:
        _skills.install(target)
    _upgrade.record_fresh_install(target, include_integrations=not no_skills)

    console.print()
    console.print(f"[green]✓[/green] Created wiki in [bold]{target}[/bold]")
    console.print()
    console.print("Next steps:")
    console.print(f"  1. cd {Path(directory)}")
    console.print("  2. Claude Code: run [bold]/define-topic[/bold]")
    console.print("     Codex: review [bold]/hooks[/bold], then run [bold]$define-topic[/bold]")
    console.print(
        "  3. (optional) run [bold]git init[/bold] yourself if you want version control"
    )


@app.command()
def upgrade(
    directory: str = typer.Argument(
        ".", help="Existing wiki directory to upgrade (default: current directory)."
    ),
) -> None:
    """Add or refresh managed Claude Code and Codex integration files."""
    result = _upgrade.upgrade(Path(directory))

    console.print()
    resolved = Path(directory).expanduser().resolve()
    console.print(f"[green]✓[/green] Upgraded wiki in [bold]{resolved}[/bold]")
    for label, paths in (
        ("Created", result.created),
        ("Updated", result.updated),
        ("Adopted", result.adopted),
    ):
        if paths:
            console.print(f"  {label}: {', '.join(paths)}")
    if result.conflicts:
        console.print("[yellow]Preserved conflicting files:[/yellow]")
        for path in result.conflicts:
            console.print(f"  - {path}")
        console.print("Resolve these files and run the upgrade again.")
        raise typer.Exit(code=1)
    if not any((result.created, result.updated, result.adopted)):
        console.print("  Already up to date.")


def main() -> None:
    app()
