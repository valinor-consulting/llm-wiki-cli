"""llm-wiki: scaffold and upgrade an LLM-maintained knowledge wiki."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from . import _scaffold, _skills, _upgrade, _workspace

app = typer.Typer(
    add_completion=False,
    help="Scaffold and upgrade an LLM-maintained knowledge wiki for Claude Code and Codex.",
)
workspace_app = typer.Typer(help="Manage a mono-repo containing registered LLM wikis.")
app.add_typer(workspace_app, name="workspace")
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


@workspace_app.command("init")
def workspace_init(
    directory: str = typer.Argument(".", help="Workspace root (default: current directory)."),
) -> None:
    """Initialize a multi-wiki workspace without creating a wiki at its root."""
    _workspace.init(Path(directory))
    console.print(f"[green]✓[/green] Created wiki workspace in [bold]{Path(directory).expanduser().resolve()}[/bold]")


@workspace_app.command("status")
def workspace_status(
    directory: str = typer.Argument(".", help="Workspace root (default: current directory)."),
) -> None:
    """Show registered wiki readiness without making changes."""
    items = _workspace.status(Path(directory))
    if not items:
        console.print("No wikis registered.")
    for item in items:
        console.print(f"{item.name}: [bold]{item.state}[/bold]" + (f" ({item.detail})" if item.detail else ""))


@workspace_app.command("upgrade")
def workspace_upgrade(
    directory: str = typer.Argument(".", help="Workspace root (default: current directory)."),
    wiki: list[str] = typer.Option(None, "--wiki", help="Registered wiki to select; repeatable."),
    apply: bool = typer.Option(False, "--apply", help="Apply a conflict-free upgrade plan."),
) -> None:
    """Plan or apply upgrades for registered wikis."""
    items = _workspace.upgrade(Path(directory), names=wiki or None, apply=apply)
    for item in items:
        console.print(f"{item.name}: [bold]{item.state}[/bold]" + (f" ({item.detail})" if item.detail else ""))
    if any(item.state == "conflict" for item in items):
        raise typer.Exit(code=1)
    if not apply:
        console.print("Read-only plan. Re-run with --apply to make changes.")


@workspace_app.command("import")
def workspace_import(
    source: str = typer.Argument(..., help="Existing LLM wiki directory to import."),
    name: str | None = typer.Argument(None, help="Top-level destination directory name."),
    directory: str = typer.Option(".", "--workspace", help="Workspace root (default: current directory)."),
) -> None:
    """Copy a standalone wiki into this workspace, excluding its .git directory."""
    imported = _workspace.import_wiki(Path(directory), Path(source), name)
    console.print(f"[green]✓[/green] Imported and registered [bold]{imported}[/bold]")


def main() -> None:
    app()
