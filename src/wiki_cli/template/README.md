# <WIKI_NAME>

An LLM-maintained knowledge wiki built on the [LLM Wiki pattern](llm-wiki.md). A human curates sources and asks questions; Claude Code or Codex does the research, ingestion, synthesis, cross-referencing, and upkeep.

## Getting started

1. Open this directory as the workspace root in Claude Code or Codex.
2. In Claude Code, run `/define-topic`. In Codex, review and trust the project hooks with `/hooks`, then invoke `$define-topic`. Answer the interview to write a complete `TOPIC.md`.
3. Add source material to `raw/` (immutable source docs the agent reads but never edits) and ask the agent to ingest it.
4. Ask questions. Each valuable answer is filed back into the wiki as a new page.

## Layout

- `TOPIC.md` — the subject and scope of this wiki (filled in by the define-topic workflow).
- `WIKI.md` — the shared operating schema and maintenance instructions.
- `CLAUDE.md` and `AGENTS.md` — entrypoints for Claude Code and Codex.
- `llm-wiki.md` — background on the LLM Wiki pattern.
- `raw/` — immutable source documents you add; agents read only.
- `Clippings/` — web clipper exports, ingested on explicit request.
- `wiki/` — the maintained knowledge base:
  - `index.md` — catalog of every page.
  - `log.md` — chronological record of operations.
  - `sources/`, `concepts/`, `entities/`, `outputs/`, `insights/` — content pages by category.

## Conventions

By default, this wiki ships with agent-specific skills and guard hooks under `.claude/`, `.agents/`, and `.codex/`. These keep pages in a clear, human-readable voice and protect source directories from accidental edits. See `WIKI.md` for the full schema, frontmatter rules, and operations. Codex project hooks are guardrails rather than a complete security boundary.

This directory is not under version control. If you want history, run `git init` here yourself.
