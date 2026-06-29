# <WIKI_NAME>

An LLM-maintained knowledge wiki built on the [LLM Wiki pattern](llm-wiki.md). A human curates sources and asks questions; Claude does the research, ingestion, synthesis, cross-referencing, and upkeep.

## Getting started

1. Open this directory in Claude Code.
2. Run `/define-topic` and answer the interview. It writes a complete `TOPIC.md` describing what this wiki covers.
3. Add source material to `raw/` (immutable source docs Claude reads but never edits) and ask Claude to ingest it.
4. Ask questions. Each valuable answer is filed back into the wiki as a new page.

## Layout

- `TOPIC.md` — the subject and scope of this wiki (filled in by `/define-topic`).
- `CLAUDE.md` — the operating instructions Claude follows when maintaining the wiki.
- `llm-wiki.md` — background on the LLM Wiki pattern.
- `raw/` — immutable source documents you add; Claude reads only.
- `Clippings/` — web clipper exports, ingested on explicit request.
- `wiki/` — the maintained knowledge base:
  - `index.md` — catalog of every page.
  - `log.md` — chronological record of operations.
  - `sources/`, `concepts/`, `entities/`, `outputs/`, `insights/` — content pages by category.

## Conventions

This wiki ships with the `prose-voice` skill and guard hooks preinstalled under `.claude/`, so pages stay in a clear, human-readable voice and protected directories are not modified by accident. See `CLAUDE.md` for the full schema, frontmatter rules, and operations.

This directory is not under version control. If you want history, run `git init` here yourself.
