---
description: Create or iteratively refine a lightweight research project in the workspace's research directory.
---

# Research Project

Use this workflow for independent research at a workspace root, not for maintaining a registered wiki.

Ask for a project name if one is not provided. Inspect `research/` for an existing matching project; if none exists, create it with `llm-wiki workspace research init "<name>" --workspace .` before continuing. Read that project's `BRIEF.md`, `REPORT.md`, and `SOURCES.md` before researching.

Use the brief to define the question and constraints. Research iteratively, recording useful sources and verification notes in `SOURCES.md`, then improve the answer, findings, and open questions in `REPORT.md`. Keep report citations as standard Markdown links in its terminal `## References` section. Preserve uncertainty rather than implying unsupported conclusions.

You may edit only the active `research/<project>/` directory. Do not alter `insights/` or any registered wiki unless the user explicitly asks to promote material there. Do not apply wiki schemas, OKF rules, or wiki-selection instructions to project files.
