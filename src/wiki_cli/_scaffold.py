"""Scaffolding helpers: resolve the target directory and copy the bundled template.

No git operations happen here or anywhere in this tool. Version control is the
user's responsibility.
"""

from __future__ import annotations

import datetime
import shutil
from importlib.resources import files
from pathlib import Path

import typer


def resolve_target(directory: str, *, force: bool) -> Path:
    """Return the absolute target path, refusing a non-empty dir unless ``force``."""
    target = Path(directory).expanduser().resolve()
    if target.exists():
        if not target.is_dir():
            raise typer.BadParameter(f"{target} exists and is not a directory.")
        if any(target.iterdir()) and not force:
            raise typer.BadParameter(
                f"{target} is not empty. Use --force to scaffold into it anyway."
            )
    return target


def _today() -> str:
    return datetime.date.today().isoformat()


def copy_template(target: Path) -> None:
    """Copy the bundled template into ``target`` and render placeholders."""
    template_root = files("wiki_cli") / "template"

    target.mkdir(parents=True, exist_ok=True)
    # importlib.resources.files returns a Traversable; for a real filesystem
    # package this is a Path, which shutil.copytree accepts.
    shutil.copytree(str(template_root), str(target), dirs_exist_ok=True)

    _render_placeholders(target)


def _render_placeholders(target: Path) -> None:
    """String-replace placeholders in rendered template files."""
    replacements = {
        "<YYYY-MM-DD>": _today(),
        "<WIKI_NAME>": target.name,
    }
    for rel in ("wiki/index.md", "README.md"):
        path = target / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for needle, value in replacements.items():
            text = text.replace(needle, value)
        path.write_text(text, encoding="utf-8")
