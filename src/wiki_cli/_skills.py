"""Install bundled Claude Code and Codex project integrations."""

from __future__ import annotations

import json
import stat
from importlib.resources import files
from pathlib import Path

_HOOK_MATCHER = "Edit|Write|MultiEdit"
_GUARD_HOOKS = [
    ("guard-blank-edits.py", "Checking edit against blank-line-only rule..."),
    ("guard-immutable-dirs.py", "Checking edit against immutable source directories..."),
    ("guard-wiki-links.py", "Checking edit for piped wiki links in table cells..."),
]


def _read_asset(relative: str) -> bytes:
    return (files("wiki_cli") / "assets" / relative).read_bytes()


def _claude_settings() -> bytes:
    hooks = [
        {
            "type": "command",
            "command": f'python3 "${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{script}"',
            "timeout": 10,
            "statusMessage": message,
        }
        for script, message in _GUARD_HOOKS
    ]
    value = {"hooks": {"PreToolUse": [{"matcher": _HOOK_MATCHER, "hooks": hooks}]}}
    return (json.dumps(value, indent=2) + "\n").encode()


def _codex_hooks() -> bytes:
    value = {
        "description": "LLM wiki edit guardrails.",
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 .codex/hooks/guard-edits.py",
                            "timeout": 10,
                            "statusMessage": "Checking edit against wiki guardrails...",
                        }
                    ],
                }
            ]
        },
    }
    return (json.dumps(value, indent=2) + "\n").encode()


def rendered_files() -> dict[str, tuple[bytes, bool]]:
    """Return integration files as ``relative path -> (content, executable)``."""
    rendered: dict[str, tuple[bytes, bool]] = {}

    for relative in (
        "skills/prose-voice/SKILL.md",
        "skills/prose-voice/lint-prose.py",
        "commands/define-topic.md",
        "hooks/guard-blank-edits.py",
        "hooks/guard-immutable-dirs.py",
        "hooks/guard-wiki-links.py",
    ):
        rendered[f".claude/{relative}"] = (
            _read_asset(relative),
            relative.endswith(".py"),
        )
    rendered[".claude/settings.json"] = (_claude_settings(), False)

    prose = _read_asset("skills/prose-voice/SKILL.md").decode()
    prose = prose.replace(
        "${CLAUDE_PROJECT_DIR}/.claude/skills/prose-voice/lint-prose.py",
        ".agents/skills/prose-voice/lint-prose.py",
    )
    rendered[".agents/skills/prose-voice/SKILL.md"] = (prose.encode(), False)
    rendered[".agents/skills/prose-voice/lint-prose.py"] = (
        _read_asset("skills/prose-voice/lint-prose.py"),
        True,
    )

    define_topic = _read_asset("commands/define-topic.md").decode()
    define_topic = define_topic.replace(
        "---\ndescription:", "---\nname: define-topic\ndescription:", 1
    )
    define_topic = define_topic.replace("`CLAUDE.md`", "`WIKI.md`")
    rendered[".agents/skills/define-topic/SKILL.md"] = (define_topic.encode(), False)

    rendered[".codex/hooks/guard-edits.py"] = (
        _read_asset("codex-hooks/guard-edits.py"),
        True,
    )
    rendered[".codex/hooks.json"] = (_codex_hooks(), False)
    return rendered


def workspace_rendered_files() -> dict[str, tuple[bytes, bool]]:
    """Return integrations installed at a multi-wiki workspace root."""
    rendered: dict[str, tuple[bytes, bool]] = {
        "AGENTS.md": (_read_asset("workspace/AGENTS.md"), False),
        "CLAUDE.md": (_read_asset("workspace/CLAUDE.md"), False),
        "insights/.gitkeep": (_read_asset("workspace/insights/.gitkeep"), False),
    }

    selector = _read_asset("workspace/select-wiki/SKILL.md")
    rendered[".agents/skills/select-wiki/SKILL.md"] = (selector, False)
    rendered[".claude/skills/select-wiki/SKILL.md"] = (selector, False)

    prose = _read_asset("skills/prose-voice/SKILL.md").decode()
    prose = prose.replace(
        "Use whenever creating or editing .md files.",
        "Use only after a workspace wiki has been selected, when creating or editing that wiki's .md files.",
    ).replace(
        "# Writing deliverables in a human voice",
        "# Writing Deliverables in a Human Voice\n\nIn a multi-wiki workspace, do not apply this skill until the user has selected a registered wiki.",
        1,
    )
    rendered[".claude/skills/prose-voice/SKILL.md"] = (prose.encode(), False)
    rendered[".claude/skills/prose-voice/lint-prose.py"] = (
        _read_asset("skills/prose-voice/lint-prose.py"),
        True,
    )
    codex_prose = prose.replace(
        "${CLAUDE_PROJECT_DIR}/.claude/skills/prose-voice/lint-prose.py",
        ".agents/skills/prose-voice/lint-prose.py",
    )
    rendered[".agents/skills/prose-voice/SKILL.md"] = (codex_prose.encode(), False)
    rendered[".agents/skills/prose-voice/lint-prose.py"] = (
        _read_asset("skills/prose-voice/lint-prose.py"),
        True,
    )

    for relative in (
        "hooks/guard-blank-edits.py",
        "hooks/guard-immutable-dirs.py",
        "hooks/guard-wiki-links.py",
    ):
        rendered[f".claude/{relative}"] = (_read_asset(relative), True)
    rendered[".claude/settings.json"] = (_claude_settings(), False)
    rendered[".codex/hooks/guard-edits.py"] = (
        _read_asset("codex-hooks/guard-edits.py"),
        True,
    )
    rendered[".codex/hooks.json"] = (_codex_hooks(), False)
    return rendered


def install(target: Path) -> None:
    """Write both agents' optional integrations into ``target``."""
    for relative, (content, executable) in rendered_files().items():
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        if executable:
            destination.chmod(
                destination.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )
