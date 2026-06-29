"""Install the vendored prose-voice skill, guard hooks, and slash commands.

The CLI ships path-rewritten copies of the marketplace skills as package data
under ``assets/`` (see ``scripts/sync-skills.py``). This module writes them into
a new wiki's ``.claude/`` directory as plain project files and wires the guard
hooks in a committed ``.claude/settings.json``.

No git operations happen here. The tool never writes ``settings.local.json``.
"""

from __future__ import annotations

import json
import shutil
import stat
from importlib.resources import files
from pathlib import Path

# Guard hooks to wire in .claude/settings.json. Each fires on edits via the same
# PreToolUse matcher. The command paths use ${CLAUDE_PROJECT_DIR}, which Claude
# Code resolves to the wiki root at runtime.
_HOOK_MATCHER = "Edit|Write|MultiEdit"
_GUARD_HOOKS = [
    ("guard-blank-edits.py", "Checking edit against blank-line-only rule..."),
    ("guard-immutable-dirs.py", "Checking edit against immutable source directories..."),
    ("guard-wiki-links.py", "Checking edit for piped wiki links in table cells..."),
]


def install(target: Path) -> None:
    """Write vendored skills/hooks/commands into ``target``/.claude."""
    assets_root = files("wiki_cli") / "assets"
    claude_dir = target / ".claude"

    # Copy the vendored skills, commands, and hooks verbatim into .claude/.
    for subdir in ("skills", "commands", "hooks"):
        src = assets_root / subdir
        if not src.is_dir():
            continue
        shutil.copytree(str(src), str(claude_dir / subdir), dirs_exist_ok=True)

    _make_scripts_executable(claude_dir)
    _write_settings(claude_dir)


def _make_scripts_executable(claude_dir: Path) -> None:
    """Ensure hook and lint scripts keep their executable bit after the copy."""
    for script in (claude_dir / "hooks").glob("*.py"):
        _add_exec_bit(script)
    for script in (claude_dir / "skills").rglob("*.py"):
        _add_exec_bit(script)


def _add_exec_bit(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_settings(claude_dir: Path) -> None:
    """Write committed .claude/settings.json wiring the guard hooks."""
    hooks = [
        {
            "type": "command",
            "command": f'python3 "${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{script}"',
            "timeout": 10,
            "statusMessage": message,
        }
        for script, message in _GUARD_HOOKS
    ]
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": _HOOK_MATCHER,
                    "hooks": hooks,
                }
            ]
        }
    }
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )
