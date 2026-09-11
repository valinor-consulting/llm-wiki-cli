---
name: research-project
description: Create or iteratively refine a lightweight research project in a workspace's research directory.
---

# Research Project

Use this workflow for independent research at a workspace root, not for maintaining a registered wiki.

The project name identifies its directory; it is not the research question. Never infer the question solely from the project name.

Ask for a project name if one is not provided. Inspect `research/` for an existing matching project; if none exists, create it with `llm-wiki workspace research init "<name>" --workspace .` before continuing. Read that project's `BRIEF.md`, `REPORT.md`, and `SOURCES.md` in full.

Before researching, inspect `BRIEF.md`. If `## Research question` has no meaningful content beyond its placeholder comment, use a clear research question already supplied in the user's request or ask: "What specific question should this project answer?" Do not begin research until the user has supplied an explicit question and you have written it under `## Research question`.

Ask one short follow-up at a time for missing context, constraints, or a definition of done only when the answer would materially shape the research. Write the answers into the matching brief sections, replacing placeholder comments in sections you fill. Preserve existing brief content and do not make the user repeat information already present or supplied with the invocation.

Once the brief defines the question, research iteratively, recording useful sources and verification notes in `SOURCES.md`, then improve the answer, findings, and open questions in `REPORT.md`. Keep report citations as standard Markdown links in its terminal `## References` section. Preserve uncertainty rather than implying unsupported conclusions.

You may edit only the active `research/<project>/` directory. Do not alter `insights/` or any registered wiki unless the user explicitly asks to promote material there. Do not apply wiki schemas, OKF rules, or wiki-selection instructions to project files.
