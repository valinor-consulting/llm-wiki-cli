# llm-wiki-cli

`llm-wiki` scaffolds an LLM-maintained knowledge wiki for use with [Claude Code](https://claude.com/claude-code). It writes a complete wiki tree, a `CLAUDE.md` that teaches Claude how to maintain it, and a `.claude/` directory wired with the prose-voice skill, a `/define-topic` slash command, and three guard hooks.

## Install / run

The command is named `llm-wiki` but the distribution is named `llm-wiki-cli`, so `uvx` needs `--from` to map between them.

Run it once without installing:

```bash
uvx --from git+https://github.com/valinor-consulting/llm-wiki-cli.git llm-wiki init my-wiki
```

Pin to a released tag for reproducibility:

```bash
uvx --from git+https://github.com/valinor-consulting/llm-wiki-cli.git@v0.1.0 llm-wiki init my-wiki
```

Install it as a persistent tool on your PATH:

```bash
uv tool install --from git+https://github.com/valinor-consulting/llm-wiki-cli.git llm-wiki-cli
llm-wiki init my-wiki
```

## What `llm-wiki init` produces

`init` copies a bundled template into the target directory. Nothing is downloaded at runtime and no git operation is performed.

```
my-wiki/
  CLAUDE.md            # how Claude maintains this wiki (schema, operations, style)
  TOPIC.md             # the wiki's subject — fill it via /define-topic
  llm-wiki.md          # the LLM Wiki pattern this build follows
  README.md            # per-wiki readme
  .gitignore
  raw/                 # immutable source docs you add; Claude reads, never edits
  Clippings/           # Obsidian Web Clipper exports
  wiki/
    index.md           # content catalog (seeded headings)
    log.md             # append-only operation log
    sources/  concepts/  entities/  outputs/  insights/
  .claude/
    settings.json      # wires the three guard hooks as PreToolUse
    commands/define-topic.md
    skills/prose-voice/{SKILL.md, lint-prose.py}
    hooks/guard-blank-edits.py
    hooks/guard-immutable-dirs.py
    hooks/guard-wiki-links.py
```

The prose-voice skill and all three guard hooks are installed into `.claude/` by default. Pass `--no-skills` to skip them. Pass `--force` to scaffold into a non-empty directory.

## Next step

Open the new directory in Claude Code and run `/define-topic`. Claude interviews you one question at a time, then writes a structured `TOPIC.md` describing the subject, the sub-topics to cover, per-topic instructions, and what's out of scope. From there, ask Claude to ingest sources and answer questions, and it maintains the wiki under `wiki/`.

If you want version control, run `git init` yourself inside the new wiki. The tool never touches git.

## Versioning

Releases are tagged `vX.Y.Z`. Use the `@vX.Y.Z` suffix on the git URL (shown above) to pin a wiki to a specific version of the scaffolder.
