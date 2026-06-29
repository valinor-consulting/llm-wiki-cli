#!/usr/bin/env python3
"""Vendor the claude-wiki-skills marketplace into this CLI's package data.

Reads skill, hook, and command files from a local ``claude-wiki-skills``
checkout (a plain filesystem path — this script never fetches from git) and
copies them into ``src/wiki_cli/assets/``. During the copy it rewrites the
marketplace-only ``${CLAUDE_PLUGIN_ROOT}`` placeholder to
``${CLAUDE_PROJECT_DIR}/.claude``, which is the path the vendored files live at
once ``llm-wiki init`` writes them into a wiki's ``.claude/`` directory.

Run this manually before each release whenever the skills repo changes:

    python3 scripts/sync-skills.py [path/to/claude-wiki-skills]

The default source path is ``../claude-wiki-skills`` relative to this repo.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

# Marketplace placeholder -> vendored-into-.claude placeholder.
PLUGIN_ROOT = "${CLAUDE_PLUGIN_ROOT}"
PROJECT_ROOT = "${CLAUDE_PROJECT_DIR}/.claude"

# (source path relative to the skills checkout, destination relative to assets/).
FILES = [
    (
        "prose-voice/skills/prose-voice/SKILL.md",
        "skills/prose-voice/SKILL.md",
    ),
    (
        "prose-voice/skills/prose-voice/lint-prose.py",
        "skills/prose-voice/lint-prose.py",
    ),
    (
        "define-topic/commands/define-topic.md",
        "commands/define-topic.md",
    ),
    (
        "guard-blank-edits/hooks/guard-blank-edits.py",
        "hooks/guard-blank-edits.py",
    ),
    (
        "guard-immutable-dirs/hooks/guard-immutable-dirs.py",
        "hooks/guard-immutable-dirs.py",
    ),
    (
        "guard-wiki-links/hooks/guard-wiki-links.py",
        "hooks/guard-wiki-links.py",
    ),
]


def main(argv: list[str]) -> int:
    repo_root = Path(__file__).resolve().parent.parent
    default_src = repo_root.parent / "claude-wiki-skills"
    src_root = Path(argv[1]).expanduser().resolve() if len(argv) > 1 else default_src

    if not src_root.is_dir():
        print(f"error: skills checkout not found at {src_root}", file=sys.stderr)
        return 1

    assets_root = repo_root / "src" / "wiki_cli" / "assets"

    for rel_src, rel_dst in FILES:
        src = src_root / rel_src
        dst = assets_root / rel_dst
        if not src.is_file():
            print(f"error: missing source file {src}", file=sys.stderr)
            return 1

        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        rewritten = text.replace(PLUGIN_ROOT, PROJECT_ROOT)
        dst.write_text(rewritten, encoding="utf-8")
        # Preserve the executable bit for hook/lint scripts.
        if src.suffix == ".py":
            shutil.copymode(src, dst)

        note = " (rewrote CLAUDE_PLUGIN_ROOT)" if PLUGIN_ROOT in text else ""
        print(f"  {rel_dst}{note}")

    print(f"Vendored {len(FILES)} files from {src_root} into {assets_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
