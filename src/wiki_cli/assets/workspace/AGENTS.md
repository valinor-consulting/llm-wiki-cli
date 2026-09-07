# Wiki Workspace Instructions

This repository is a workspace containing multiple LLM wikis under `wikis/`. It is not itself an LLM wiki.

`insights/` holds human-owned notes and cross-wiki synthesis. Do not create or edit files there unless the user explicitly asks.

`research/` holds lightweight, independent research projects. Use `$research-project` to create or continue one; it may edit only its selected project unless the user explicitly asks to promote work into `insights/` or a wiki.

Before ingesting, querying, linting, or editing wiki content, identify a registered target wiki from `.llm-wiki-workspace.json`. Read that wiki's `WIKI.md` and `TOPIC.md` in full, then follow its local instructions. If the request does not identify a wiki, ask the user to select one. Do not infer a target from the current directory.
