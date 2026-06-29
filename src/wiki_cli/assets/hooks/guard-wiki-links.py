#!/usr/bin/env python3
# PreToolUse guard — blocks piped wiki links inside Markdown table cells with
# an unescaped pipe. Obsidian reads the pipe as a column delimiter, so the link
# fails to render.
# Exit 0 = allow.  Exit 2 = block (stderr is fed back to the model as the reason).
# Fails OPEN on any internal error: a bug here must never wedge a legitimate edit.

import json
import re
import sys


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        payload = json.loads(raw)
    except Exception:
        sys.exit(0)

    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input")
    if not ti:
        sys.exit(0)

    try:
        path = str(ti.get("file_path") or "")
        if not path.endswith(".md"):
            sys.exit(0)

        new_texts = []
        if tool == "Edit":
            new_texts.append(str(ti.get("new_string") or ""))
        elif tool == "Write":
            new_texts.append(str(ti.get("content") or ""))
        elif tool == "MultiEdit":
            for e in (ti.get("edits") or []):
                new_texts.append(str(e.get("new_string") or ""))

        bad_link = re.compile(r"\[\[[^\]]*?(?<!\\)\|[^\]]*?\]\]")
        offenders = []
        for text in new_texts:
            for line in text.splitlines():
                if line.lstrip().startswith("|") and bad_link.search(line):
                    offenders.append(line.strip())

        if offenders:
            sample = "\n  ".join(offenders[:3])
            block(
                "BLOCKED: this edit places a piped wiki link inside a Markdown "
                "table cell with an unescaped '|'. Obsidian treats that pipe as a "
                "column separator, so the link will not render. Fix: escape it as "
                r"[[target\|Display]] (backslash before the pipe), or when Display "
                f"equals the slug just write [[slug]]. Offending line(s):\n  {sample}"
            )
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
