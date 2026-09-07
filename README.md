# llm-wiki-cli

`llm-wiki` scaffolds an LLM-maintained knowledge wiki for [Claude Code](https://claude.com/claude-code) and [OpenAI Codex](https://developers.openai.com/codex/). It writes a complete wiki tree, shared operating instructions, agent-specific entrypoints, reusable skills, and edit guardrails.

## Install and run

The command is named `llm-wiki` but the distribution is named `llm-wiki-cli`, so `uvx` needs `--from` to map between them.

Run it once without installing:

```bash
uvx --from git+https://github.com/valinor-consulting/llm-wiki-cli.git llm-wiki init my-wiki
```

Pin to a released tag for reproducibility:

```bash
uvx --from git+https://github.com/valinor-consulting/llm-wiki-cli.git@v0.4.0 llm-wiki init my-wiki
```

Install it as a persistent tool on your PATH:

```bash
uv tool install --from git+https://github.com/valinor-consulting/llm-wiki-cli.git llm-wiki-cli
llm-wiki init my-wiki
```

## What `llm-wiki init` produces

`init` copies a bundled template into the target directory. Nothing is downloaded at runtime and no Git operation is performed.

```text
my-wiki/
  WIKI.md              # shared schema, operations, and writing rules
  CLAUDE.md            # Claude Code entrypoint
  AGENTS.md            # Codex entrypoint
  TOPIC.md             # the wiki's subject
  llm-wiki.md          # background on the LLM Wiki pattern
  README.md            # per-wiki instructions
  .llm-wiki.json       # hashes of CLI-managed integration files
  raw/                 # immutable source documents
  Clippings/           # Obsidian Web Clipper exports
  wiki/
    index.md
    log.md
    sources/  concepts/  entities/  outputs/  insights/
  .claude/
    settings.json
    commands/define-topic.md
    skills/prose-voice/{SKILL.md, lint-prose.py}
    hooks/guard-*.py
  .agents/skills/
    define-topic/SKILL.md
    prose-voice/{SKILL.md, lint-prose.py}
  .codex/
    hooks.json
    hooks/guard-edits.py
```

Optional commands, skills, and hooks for both agents are installed by default. Pass `--no-skills` to skip that tooling. Pass `--force` to scaffold into a non-empty directory.

## Getting started

Open the generated directory as the workspace root. In Claude Code, run `/define-topic`. In Codex, use `/hooks` to review and trust the project hooks, then invoke `$define-topic`. The workflow interviews you and writes a structured `TOPIC.md`. From there, add sources and ask the agent to ingest them or answer questions.

Codex hooks are useful guardrails, but their documented tool coverage is not a complete security boundary.

## Upgrade

Updating the installed CLI and updating an existing generated wiki are separate operations.

For an unpinned Git installation, upgrade the tool and verify its version:

```bash
uv tool upgrade llm-wiki-cli
llm-wiki --version
```

`uv tool upgrade` preserves the constraints used during installation. If the tool was pinned to an older tag, reinstall it from the new tag:

```bash
uv tool install --force \
  --from git+https://github.com/valinor-consulting/llm-wiki-cli.git@v0.4.0 \
  llm-wiki-cli
llm-wiki --version
```

Then upgrade each existing wiki explicitly:

```bash
llm-wiki upgrade /path/to/wiki
```

The upgrade is additive and conflict-safe. It copies a legacy customized `CLAUDE.md` to `WIKI.md`, verifies the copy, then replaces `CLAUDE.md` with the small entrypoint used by new wikis. If an existing `WIKI.md` has diverged from `CLAUDE.md`, the latter is preserved and reported as a conflict. The command installs Codex support and tracks CLI-managed files in `.llm-wiki.json`; a managed file is refreshed only while its recorded hash still matches. It never changes wiki content, source documents, or Git state.

## Mono-Repo Workspaces

Use a workspace when one repository contains several independent LLM wikis. The repository root is a dispatcher, not a wiki: each registered top-level directory keeps its own `TOPIC.md`, `WIKI.md`, and content.

```bash
llm-wiki workspace init /path/to/wiki-workspace
llm-wiki workspace import /path/to/existing-wiki research --workspace /path/to/wiki-workspace
llm-wiki workspace status /path/to/wiki-workspace
llm-wiki workspace upgrade /path/to/wiki-workspace
llm-wiki workspace upgrade /path/to/wiki-workspace --apply
llm-wiki workspace migrate-okf /path/to/wiki-workspace --wiki research
llm-wiki workspace migrate-okf /path/to/wiki-workspace --wiki research --apply
```

Imports immediately migrate unchanged legacy integrations to the workspace layout. The upgrade command remains available for existing imported wikis and is read-only until `--apply` is supplied. In Claude Code or Codex, open the mono-repo root, name the wiki you want to work on, and let the root dispatcher load that wiki's local instructions.

`workspace migrate-okf` is a separate, preview-first content migration. It converts a registered wiki corpus to the OKF v0.2 profile only after every selected wiki passes preflight.

## Versioning

Releases are tagged `vX.Y.Z`. Use the `@vX.Y.Z` suffix on the Git URL to pin the scaffolder to a specific version.
