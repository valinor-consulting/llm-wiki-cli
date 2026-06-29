"""llm-wiki: scaffold an LLM-maintained knowledge wiki for Claude Code."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from . import _scaffold, _skills

app = typer.Typer(
    add_completion=False,
    help="Scaffold an LLM-maintained knowledge wiki for use with Claude Code.",
)
console = Console()


@app.callback()
def _root() -> None:
    """Scaffold an LLM-maintained knowledge wiki for use with Claude Code."""


@app.command()
def init(
    directory: str = typer.Argument(..., help="Target directory for the new wiki."),
    no_skills: bool = typer.Option(
        False, "--no-skills", help="Skip installing the prose-voice skill and guard hooks."
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

    console.print()
    console.print(f"[green]✓[/green] Created wiki in [bold]{target}[/bold]")
    console.print()
    console.print("Next steps:")
    console.print(f"  1. cd {Path(directory)}")
    console.print("  2. Open the directory in Claude Code and run [bold]/define-topic[/bold]")
    console.print(
        "  3. (optional) run [bold]git init[/bold] yourself if you want version control"
    )


def main() -> None:
    app()
