#!/usr/bin/env python3
"""Codex PreToolUse guard for LLM wiki apply_patch edits.

The hook fails open on malformed or unfamiliar input. Exit code 2 blocks an edit
and sends stderr back to Codex as the reason.
"""

from __future__ import annotations

import json
import re
import sys

IMMUTABLE_DIRS = ("raw", "Clippings")
BAD_TABLE_LINK = re.compile(r"\[\[[^\]]*?(?<!\\)\|[^\]]*?\]\]")
FILE_HEADER = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$")
MOVE_HEADER = re.compile(r"^\*\*\* Move to: (.+)$")


def block(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def normalize(path: str) -> str:
    return path.strip().strip('"').replace("\\", "/")


def immutable(path: str) -> str | None:
    normalized = f"/{normalize(path).lstrip('/')}"
    for directory in IMMUTABLE_DIRS:
        if f"/{directory}/" in normalized:
            return directory
    return None


def parse_patch(command: str) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    in_hunk = False

    for line in command.splitlines():
        header = FILE_HEADER.match(line)
        if header:
            current = {
                "paths": [normalize(header.group(1))],
                "added": [],
                "removed": [],
            }
            files.append(current)
            in_hunk = line.startswith("*** Add File:")
            continue

        move = MOVE_HEADER.match(line)
        if move and current is not None:
            current["paths"].append(normalize(move.group(1)))  # type: ignore[union-attr]
            continue

        if current is None:
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if line.startswith("***"):
            in_hunk = False
            continue
        if not in_hunk:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current["added"].append(line[1:])  # type: ignore[union-attr]
        elif line.startswith("-") and not line.startswith("---"):
            current["removed"].append(line[1:])  # type: ignore[union-attr]

    return files


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if payload.get("tool_name") != "apply_patch":
            return
        command = payload.get("tool_input", {}).get("command")
        if not isinstance(command, str):
            return
        files = parse_patch(command)
    except Exception:
        return

    try:
        for change in files:
            for path in change["paths"]:
                directory = immutable(str(path))
                if directory:
                    block(
                        f"BLOCKED: '{path}' is under immutable source directory "
                        f"{directory}/. These files are read-only inputs."
                    )

        changed_lines = [
            line
            for change in files
            for key in ("added", "removed")
            for line in change[key]
        ]
        if changed_lines and all(not str(line).strip() for line in changed_lines):
            block(
                "BLOCKED: this patch only adds or removes blank/whitespace lines. "
                "Fold the change into a substantive edit or skip it."
            )

        for change in files:
            markdown = any(str(path).lower().endswith(".md") for path in change["paths"])
            if not markdown:
                continue
            offenders = [
                str(line).strip()
                for line in change["added"]
                if str(line).lstrip().startswith("|") and BAD_TABLE_LINK.search(str(line))
            ]
            if offenders:
                sample = "\n  ".join(offenders[:3])
                block(
                    "BLOCKED: a Markdown table contains an unescaped piped wiki "
                    r"link. Use [[target\|Display]] or [[slug]]. Offending line(s):\n  "
                    + sample
                )
    except SystemExit:
        raise
    except Exception:
        return


if __name__ == "__main__":
    main()
