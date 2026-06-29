#!/usr/bin/env python3
# PreToolUse guard — blocks edits whose only change is adding/removing blank lines.
# Exit 0 = allow.  Exit 2 = block (stderr is fed back to the model as the reason).
# Fails OPEN on any internal error: a bug here must never wedge a legitimate edit.

import json
import sys


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def strip_blank_lines(s):
    return "\n".join(ln for ln in (s or "").splitlines() if ln.strip())


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
        pairs = []
        if tool == "Edit":
            pairs.append((str(ti.get("old_string") or ""), str(ti.get("new_string") or "")))
        elif tool == "MultiEdit":
            for e in (ti.get("edits") or []):
                pairs.append((str(e.get("old_string") or ""), str(e.get("new_string") or "")))

        if pairs and all(
            old != new and strip_blank_lines(old) == strip_blank_lines(new)
            for old, new in pairs
        ):
            block(
                "BLOCKED: this edit's only change is adding or removing "
                "blank/whitespace lines. Project policy rejects blank-line-only "
                "edits. Either fold the change into a substantive content edit "
                "or skip it entirely."
            )
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
