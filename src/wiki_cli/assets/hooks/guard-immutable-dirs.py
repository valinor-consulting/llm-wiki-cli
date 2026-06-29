#!/usr/bin/env python3
# PreToolUse guard — blocks edits to immutable source directories.
# Exit 0 = allow.  Exit 2 = block (stderr is fed back to the model as the reason).
# Fails OPEN on any internal error: a bug here must never wedge a legitimate edit.

import json
import re
import sys

IMMUTABLE_DIRS = ["raw", "Clippings"]


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
        if path and IMMUTABLE_DIRS:
            norm = path.replace("\\", "/")
            for d in IMMUTABLE_DIRS:
                if re.search(rf"(^|/){re.escape(d)}/", norm):
                    block(
                        f"BLOCKED: '{path}' is under an immutable source directory "
                        f"({d}/). Project policy: these files are read-only inputs and "
                        f"must never be modified by the assistant."
                    )
    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
