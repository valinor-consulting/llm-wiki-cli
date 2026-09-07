---
name: select-wiki
description: Select a registered LLM wiki in a multi-wiki workspace before performing wiki maintenance.
---

# Select a Wiki

The workspace root is not a wiki. For a wiki request, identify the target directory in `.llm-wiki-workspace.json`. If the request does not name one registered wiki, ask the user which wiki to use.

After selecting it, read `<wiki>/WIKI.md` and `<wiki>/TOPIC.md` before acting. Those files define the schema, scope, and operating rules. If `WIKI.md` contains an OKF format override, it takes precedence for files in `wiki/`. Apply the shared `prose-voice` skill only to files in the selected wiki.
