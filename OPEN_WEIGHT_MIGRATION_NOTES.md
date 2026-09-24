# Open-Weight Migration Notes

The wiki architecture is already mostly portable, but the harness layer is not standardized.

`AGENTS.md` and `SKILL.md` cover the durable instruction layer. They do not standardize commands, hooks, permissions, web research, subagents, sandboxing, or tool behavior. Switching to OpenCode would be fairly low-friction. Switching to Pi would require more deliberate integration work.

## What Already Transfers Unchanged

The following should remain canonical and harness-independent:

- `WIKI.md`, `TOPIC.md`, and the wiki directory/schema.
- Research-project files such as `BRIEF.md`, `REPORT.md`, and `SOURCES.md`.
- The workspace dispatcher in `src/wiki_cli/assets/workspace/AGENTS.md`.
- Skills under `.agents/skills/<name>/SKILL.md`.

OpenCode directly discovers `.agents/skills`, and Pi does too. Both support the standard `SKILL.md` shape already in use. OpenAI also describes Skills as compatible with the open Agent Skills standard. See the [OpenCode skills documentation](https://opencode.ai/docs/skills), [Pi skills documentation](https://pi.dev/docs/latest/skills), and [OpenAI Skills documentation](https://developers.openai.com/api/docs/guides/tools-skills).

Both harnesses understand `AGENTS.md`, although discovery and precedence differ. OpenCode V2 recognizes `AGENTS.md` specifically, while Pi can load `AGENTS.md`, `AGENTS.override.md`, or `CLAUDE.md`. See the [OpenCode instructions documentation](https://opencode.ai/v2/docs/instructions) and [Pi configuration documentation](https://pi.dev/docs/latest/configuration).

The existing skill frontmatter uses only `name` and `description`, so it is already in the portable subset.

## What Would Need Adapters

| Concern | Current implementation | OpenCode | Pi |
| --- | --- | --- | --- |
| Project instructions | `AGENTS.md` | Works | Works |
| Skills | `.agents/skills` | Works | Works |
| `/define-topic`, `/research-project` | Claude commands or Codex skills | Needs command aliases or explicit skill invocation | Exposed as `/skill:name`; exact aliases need `.pi/prompts` |
| Edit guards | `.claude/settings.json`, `.codex/hooks.json` | Needs permissions/plugin hook | Needs extension `tool_call` guard |
| Web research | Harness-provided | Built-in web fetch/search, with provider configuration | Requires a skill/extension or shell-based research tooling |
| Subagent review | Required by `prose-voice` | Supported | Requires a Pi package/extension or a self-review fallback |
| Sandboxing and approvals | Codex/Claude-specific | Has configurable permissions | Pi runs with the OS user's authority unless separately isolated |

The generator currently emits explicit Claude and Codex integrations in `src/wiki_cli/_skills.py`. The `.agents` copies are portable, but `.claude` commands and `.codex` hooks are not.

Two particularly concrete incompatibilities stand out:

- The guard script expects Codex's `apply_patch` payload format, including `tool_name == "apply_patch"` and Codex patch syntax. It cannot simply be registered in another harness unchanged.
- The prose skill explicitly requires spawning a subagent. OpenCode supports that pattern; core Pi does not provide it without an extension.

OpenCode plugins can intercept tool execution, and its permissions can deny edits to paths such as `raw/**`; Pi extensions can likewise mutate or block `tool_call` events. See the [OpenCode plugins documentation](https://opencode.ai/v2/docs/build/plugins), [OpenCode permissions documentation](https://opencode.ai/v2/docs/permissions), and [Pi extensions documentation](https://pi.dev/docs/latest/extensions).

Pi's security model is materially different: project trust controls resource loading, but Pi does not sandbox tools or ask before every tool call. For unattended wiki maintenance, run it in a container or add a permission/guard extension. See the [Pi security documentation](https://pi.dev/docs/latest/security).

## Workspace-Specific Issue

When the harness starts at the monorepo root, both OpenCode and Pi discover project skills by walking from the current directory upward. They do not automatically discover every nested `wikis/*/.agents/skills/define-topic/SKILL.md`.

The root `select-wiki`, `research-project`, and `prose-voice` skills are fine because they are installed at the workspace root. The per-wiki `define-topic` workflow would need one of:

- A workspace-aware `define-topic` skill installed at the root.
- Explicit skill paths in harness configuration.
- Opening the selected wiki itself as the harness working directory.

A root, workspace-aware skill is likely the cleanest option.

## The Open-Weight Model Is the Larger Variable

An OpenAI-compatible API does not guarantee equally capable tool use. The model must reliably support:

- Multi-step tool calling.
- Long instruction following.
- Selecting and loading skills.
- Citation discipline.
- Maintaining frontmatter and cross-links.
- Identifying contradictions.
- Staying inside the selected wiki or research project.

OpenCode and Pi both support open-weight models through compatible endpoints. OpenCode supports OpenAI-compatible providers plus Ollama, LM Studio, and vLLM; Pi supports compatible endpoints through `models.json`. See the [OpenCode providers documentation](https://opencode.ai/v2/docs/providers) and [Pi models documentation](https://pi.dev/docs/latest/models).

With a weaker model, move more correctness into deterministic code:

- Make skill invocation explicit for complex operations.
- Shorten and modularize the long `WIKI.md` workflow.
- Turn frontmatter, linking, index, log, and immutable-directory checks into a harness-neutral `llm-wiki validate` command.
- Let each harness hook or extension call that same validator.
- Give Pi a self-review fallback when no subagent tool exists.
- Test representative ingest, query, research, contradiction, and lint tasks against every supported model.

## Recommendation

OpenCode is the easiest next harness for this project. The current `AGENTS.md` and `.agents/skills` structure should work immediately, while its web tools, subagents, permissions, and plugin hooks cover most Codex behavior.

Pi can work well, but it is deliberately more minimal. For research-heavy usage, it needs web search, edit guards, and possibly subagents supplied through extensions or packages, along with appropriate isolation.

No schema or conceptual rewrite is needed, but this is not fully "write once, run everywhere." Treat `AGENTS.md`, `WIKI.md`, and `.agents/skills` as the portable core, then maintain small harness adapters for commands, guardrails, tools, and security.
