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
uvx --from git+https://github.com/valinor-consulting/llm-wiki-cli.git@v0.7.2 llm-wiki init my-wiki
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

Open the generated directory as the workspace root. In Claude Code or the Codex VS Code extension, run `/define-topic`. In Codex, use `/hooks` to review and trust the project hooks when prompted. The workflow interviews you and writes a structured `TOPIC.md`. From there, add sources and ask the agent to ingest them or answer questions.

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
  --from git+https://github.com/valinor-consulting/llm-wiki-cli.git@v0.7.2 \
  llm-wiki-cli
llm-wiki --version
```

Then upgrade each existing wiki explicitly:

```bash
llm-wiki upgrade /path/to/wiki
```

The upgrade is additive and conflict-safe. It copies a legacy customized `CLAUDE.md` to `WIKI.md`, verifies the copy, then replaces `CLAUDE.md` with the small entrypoint used by new wikis. If an existing `WIKI.md` has diverged from `CLAUDE.md`, the latter is preserved and reported as a conflict. The command installs Codex support and tracks CLI-managed files in `.llm-wiki.json`; a managed file is refreshed only while its recorded hash still matches. It never changes wiki content, source documents, or Git state.

## Mono-Repo Workspaces

Use a workspace when one repository contains several independent LLM wikis. The repository root is a dispatcher, not a wiki. It keeps shared agent entrypoints and separates durable knowledge by purpose:

```text
wiki-workspace/
  wikis/
    example-wiki/       # registered LLM wikis
  research/             # lightweight, independent research projects
  insights/             # human-owned cross-wiki notes and synthesis
  .llm-wiki-workspace.json
```

Every registered wiki lives in `wikis/<name>/` and retains its own `TOPIC.md`, `WIKI.md`, and content. `wikis`, `research`, and `insights` are reserved workspace-root names, not valid wiki names.

### Create and populate a workspace

```bash
llm-wiki workspace init /path/to/wiki-workspace                    # create a workspace root
llm-wiki workspace create example-wiki --workspace /path/to/wiki-workspace # create and register a fresh wiki
llm-wiki workspace import /path/to/example-wiki example-wiki \
  --workspace /path/to/wiki-workspace                              # copy and register it as wikis/example-wiki/
llm-wiki workspace status /path/to/wiki-workspace                  # inspect registered wiki readiness
```

`workspace import` copies the source working tree except `.git`, upgrades safe legacy integrations, and registers the result at `wikis/example-wiki/`. It does not perform Git operations.

Open the mono-repo root in Claude Code or Codex. For wiki work, name the registered wiki you intend to use; the root dispatcher then loads that wiki's `WIKI.md` and `TOPIC.md`. The workspace root itself is never treated as a wiki.

### Upgrade workspace infrastructure and wikis

`workspace upgrade` is preview-first: omit `--apply` to see the plan, then add it to make the preflighted changes. Root-managed files include agent entrypoints, shared skills, and the placeholder directories for `wikis/`, `research/`, and `insights/`.

| Command | What it upgrades |
| --- | --- |
| `llm-wiki upgrade /path/to/standalone-wiki` | One standalone wiki. It applies immediately and never operates on a workspace root. |
| `llm-wiki workspace upgrade ROOT --workspace-only --apply` | Only workspace-root integrations and directories. |
| `llm-wiki workspace upgrade ROOT --wiki example-wiki --apply` | The workspace root plus one registered wiki. Repeat `--wiki` to select several. |
| `llm-wiki workspace upgrade ROOT --apply` | The workspace root plus every registered wiki. |

Legacy workspaces whose registered wikis are direct children of the root are migrated to `wikis/<name>/` by the normal workspace upgrade. The move is included in the preview and happens only with `--apply`. Any managed-file conflict, invalid wiki, or occupied `wikis/<name>/` destination stops the complete requested upgrade before changes are written.

Workspace upgrade also recognizes generated schemas from the older Obsidian-era template family. For those files it updates only the workspace-specific `prose-voice` reference; it does not replace the rest of `WIKI.md`. Unrecognized schemas remain classified as customized, and their wiki-local integrations are preserved. Converting a wiki's schema and corpus to OKF remains a separate `workspace migrate-okf` operation.

### Migrate wiki content to OKF

`workspace migrate-okf` is a separate, preview-first content migration. It converts selected registered wiki corpora to the OKF v0.2 profile only after every selected wiki passes preflight.

```bash
llm-wiki workspace migrate-okf /path/to/wiki-workspace --wiki example-wiki         # preview one wiki
llm-wiki workspace migrate-okf /path/to/wiki-workspace --wiki example-wiki --apply # apply after preflight
```

### Research projects

Research projects are deliberately lighter than wikis and are never registered as wikis.

```bash
llm-wiki workspace research init "Compare local-first note apps" \
  --workspace /path/to/wiki-workspace                              # create research/<slug>/
llm-wiki workspace research status /path/to/wiki-workspace         # list project readiness
```

`workspace research init NAME` creates `research/<slug>/BRIEF.md`, `REPORT.md`, and `SOURCES.md`. The brief defines the question and constraints; the report is the evolving answer with a terminal `## References` section; the source ledger retains working source and verification notes.

From the workspace root, use `/research-project` in Claude Code or the Codex VS Code extension to create or resume a project. The workflow researches and refines only the chosen project directory. It does not modify a wiki or `insights/` unless you explicitly request promotion of the work.

### Current-directory defaults

When the terminal is already at the workspace root, workspace commands use the current directory by default. The following are equivalent to supplying that root path explicitly:

```bash
llm-wiki workspace status                                      # inspect this workspace
llm-wiki workspace upgrade --workspace-only                    # preview root-only changes
llm-wiki workspace upgrade --wiki example-wiki --apply         # upgrade this root and one wiki
llm-wiki workspace research init "New question"                # create a project in this workspace
llm-wiki workspace research status                              # list this workspace's projects
llm-wiki workspace migrate-okf --wiki example-wiki             # preview this wiki's OKF migration
```

## Versioning

Releases are tagged `vX.Y.Z`. Use the `@vX.Y.Z` suffix on the Git URL to pin the scaffolder to a specific version.
