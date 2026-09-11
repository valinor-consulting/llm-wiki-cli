# LLM Wiki Workspace

This repository groups independent LLM wikis, lightweight research projects, and human-owned cross-wiki insights. The repository root is a workspace, not an LLM wiki.

```text
.
├── wikis/       # registered LLM wikis; each has its own TOPIC.md and WIKI.md
├── research/    # lightweight, independent research projects
├── insights/    # human-owned cross-wiki notes and synthesis
└── .llm-wiki-workspace.json
```

## Work in VS Code with Claude or Codex

Open this repository's root folder in VS Code. Keep it open at the workspace root; you do not need to open a wiki in a separate VS Code window.

For a wiki request, name the target wiki in chat, for example: “Select the `example-wiki` wiki and explain its current topic.” The workspace dispatcher verifies that it is registered, reads `wikis/example-wiki/WIKI.md` and `TOPIC.md`, and then follows that wiki's local rules. Do not ask the agent to ingest, query, lint, or edit wiki content without naming a wiki.

- In Claude Code, use `/research-project` to create or continue a root research project. For wiki setup, ask Claude to select the wiki and use its local `define-topic` workflow.
- In the Codex VS Code extension, use `/research-project` for root research. For wiki setup, ask Codex to select the wiki and use its local `/define-topic` workflow. Review and trust project hooks with `/hooks` if Codex prompts you to do so.
- The shared `prose-voice` skill applies only after a wiki has been selected. It does not apply to `research/` projects.

`insights/` is reserved for human-authored cross-wiki notes. Agents leave it alone unless you explicitly ask them to create or edit an insight.

## Complete example

Run the following from a terminal. Commands without a workspace path use the current directory as the workspace root.

```bash
mkdir example-wiki-workspace && cd example-wiki-workspace          # choose a new repository directory
llm-wiki workspace init .                                           # create the workspace and this README

llm-wiki workspace create example-wiki                              # create and register wikis/example-wiki/
llm-wiki workspace status                                           # confirm the wiki is registered and ready
```

Next, open `example-wiki-workspace/` in VS Code. In the Claude or Codex chat, say:

> Select the `example-wiki` wiki and use its local define-topic workflow to interview me and write `TOPIC.md`.

Answer the short interview. The agent writes the wiki's topic and scope to `wikis/example-wiki/TOPIC.md`. Afterwards, you can add source material to that wiki's `raw/` directory and ask the selected wiki to ingest it or answer questions.

### Import an existing wiki

```bash
llm-wiki workspace import /path/to/existing-wiki imported-wiki     # copy, upgrade, and register wikis/imported-wiki/
llm-wiki workspace status                                           # confirm the imported wiki is ready
```

Imports copy the working tree except `.git`; they do not perform Git operations. The wiki keeps its own content and topic instructions.

### Start a research project

```bash
llm-wiki workspace research init "Local-first note apps"  # create research/local-first-note-apps/
llm-wiki workspace research status                        # list project readiness
```

The CLI argument is only the project name; it is not treated as the research question. Then, in Claude Code or the Codex VS Code extension, run `/research-project`. Name `local-first-note-apps` when prompted. The workflow will ask for the actual research question and any necessary constraints, then write them to `research/local-first-note-apps/BRIEF.md` before researching. You can also provide everything up front:

> Continue the `local-first-note-apps` research project. Research question: Which local-first note apps support end-to-end encryption and conflict-free offline editing on macOS and Android?

The workflow reads the project's `BRIEF.md`, `REPORT.md`, and `SOURCES.md`, completes an empty brief with you, researches iteratively, records working source notes, and maintains a report with a terminal `## References` section. It edits only that project unless you explicitly request promotion into `insights/` or a selected wiki.

## Keep the workspace current

```bash
llm-wiki workspace upgrade --workspace-only                        # preview root integrations and directories
llm-wiki workspace upgrade --workspace-only --apply                # apply root-only changes
llm-wiki workspace upgrade --wiki example-wiki                     # preview one wiki and the workspace root
llm-wiki workspace upgrade --apply                                 # apply root and every registered wiki after preflight
```

Workspace upgrades preflight their full requested scope. For older workspaces, `--apply` also moves registered root-level wikis into `wikis/<name>/` when it is safe to do so.

To convert a selected wiki corpus to the OKF profile, use:

```bash
llm-wiki workspace migrate-okf --wiki example-wiki                 # preview the content migration
llm-wiki workspace migrate-okf --wiki example-wiki --apply         # apply only after preflight succeeds
```
