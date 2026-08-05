# Wiki Schema

## Project Overview

This is an LLM-maintained knowledge wiki built on the [LLM Wiki pattern](llm-wiki.md). Its purpose is to act as a research assistant for the topics defined in the [TOPIC file](TOPIC.md)

**Human role:** Source curation, questions, direction.  
**LLM role:** Research, ingest, synthesize, cross-reference, maintain.

---

## Directory Structure

```
raw/             # Immutable source docs — human adds, LLM reads only, never modifies
Clippings/       # Obsidian Web Clipper exports — ingest on explicit request only
wiki/
  index.md              # Content catalog: every page with link, summary, metadata
  log.md                # Append-only chronological record of operations
  sources/              # Per-source summary pages
  concepts/             # Concept definition pages
  entities/             # Named entity pages
  outputs/              # Best practices by topic
  insights/             # Human-authored notes (your judgment layer)
```

---

## Frontmatter Schema

Every file written in `wiki/` must include this YAML frontmatter:

```yaml
---
title: "<Page Title>"
type: concept | source-summary | entity
tags: [tag-one, tag-two]
sources:                # one item per line; see formatting rule below
  - "[[slug|Title]]"            # wiki/sources page
  - "[Title](URL)"             # web source
  - "[[filename.ext]]"          # raw vault file
related:                # Obsidian wiki links to related wiki pages only — no plain titles
  - "[[slug|Title]]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

**Formatting rule — `sources:` and `related:` MUST use a block list with each item double-quoted** (one `  - "..."` per line, as shown above). Do **not** use YAML flow syntax (`sources: [ ... ]`) for these fields: any item containing a link begins with `[`, which YAML parses as a nested sequence and chokes on the trailing `(url)` or text — corrupting the entire frontmatter block (Obsidian renders it as red error text). The surrounding double quotes keep each `[...](...)` / `[[...]]` value as a literal string. If a list is empty, write `sources: []`. The `tags:` field holds plain strings, so inline `[a, b]` is fine there.

Always update the `updated:` field whenever a page is edited.

---

## Link Conventions

- **Internal links** (between wiki files): Obsidian wiki syntax — `[[filename|Display Text]]` where `filename` is the file's slug without the `.md` extension (e.g., `[[concept-1-topic-page|Concept 1 Topic]]`). The filename is the link target Obsidian resolves; the display text is the human-readable title after the pipe.
- **External links** (web sources): standard markdown — `[text](url)`
- Source URLs belong in the frontmatter `sources:` field AND may appear inline where relevant

---

## Writing Style

Wiki pages are working documents for people, not LLM scratch notes. Write every page in clear English, with complete sentences and paragraphs, the way a colleague would explain the topic out loud. Use bullet lists only for content that is genuinely a list (steps, options, enumerated features) and not as a substitute for prose.

Avoid the common tells of default LLM output:

- Bold a key term sparingly when the reader should anchor on it. Don't bold whole phrases or sentences, and keep it to one or two bold terms per paragraph.
- Avoid em dashes as connectors. Use commas, periods, or parentheses instead, and save the em dash for a rare genuine aside.
- Don't string three or more items together with commas or semicolons inside a sentence. Make it a real bulleted list instead.
- Drop rhetorical contrast tics like "not X, it's Y" or "isn't just X, it's Y." State the point directly.
- Cut throat-clearing phrases ("It's worth noting that...", "It's important to understand that..."). Say the thing once, plainly.
- Write multipliers as `2x` and `3x`, not `2×` and `3×`.

A person unfamiliar with LLMs should be able to read any wiki page and not notice it was written by one.

Follow the `prose-voice` skill (`.claude/skills/prose-voice/SKILL.md` in Claude Code or `.agents/skills/prose-voice/SKILL.md` in Codex).

---

## Knowledge Integration

The wiki and best practices present the current synthesized understanding. When new research or raw input files change that understanding, revise the affected page in place. Merge the new evidence where it belongs:

- Explanations
- Tables
- Recommendations
- Risks
- Mappings

Do not append update-history material inside content pages. This includes:

- Dated update notes
- Running commentary
- "New findings" sections
- Mini changelogs

Use `wiki/log.md` for operation history, and git history for diffs. If an older statement is superseded, replace it or qualify it in the prose rather than preserving both versions as a history report.

---

## Operations

### Ingest

Triggered by: "ingest [source]" or "process [file]"

1. Read the source file in full
2. Briefly discuss key takeaways with the user
3. Create or update `wiki/sources/<slug>.md` with a structured summary
4. Create or update relevant pages as appropriate, integrating source findings into the current synthesis
5. Add or update `[[wiki links]]` bidirectionally between all touched pages
6. Check for contradictions with existing wiki content:
   - Flag on the relevant wiki page with a blockquote: `> **Contradiction noted:** [description] — see also [[Other Page]]`
   - If multiple items need human clarification, add an **## Items Requiring Close Review** section to the source summary page listing each item
   - Walk through flagged items with the user one at a time, prompting for the correct answer
   - As each item is resolved, apply the correction, remove the blockquote flag from the relevant wiki page, and remove the item from the review section
   - Once all items are resolved, delete the **## Items Requiring Close Review** section entirely
7. Update `wiki/index.md` with any new pages
8. Prepend a one-line entry to `wiki/log.md` (directly below the `# Wiki Log` heading — newest first):
   ```
   ## [YYYY-MM-DD] ingest | <Source Title>
   <One-line summary of pages created/updated>
   ```

### Query

Triggered by: any question directed at the wiki

1. Read `wiki/index.md` to identify relevant pages
2. Read the relevant pages and synthesize an answer with `[[citations]]`
3. If the wiki lacks sufficient information: perform web research (see Web Research below), integrate findings into the wiki, then answer
4. **Always file valuable answers as a new wiki page in the appropriate category** — questions are invitations to grow the wiki, not one-off answers. Treat each question as an opportunity to document reusable knowledge.
5. Prepend a one-line entry to `wiki/log.md` (directly below the `# Wiki Log` heading — newest first):
   ```
   ## [YYYY-MM-DD] query | <question summary>
   <One-line summary of answer / pages created>
   ```

### Web Research

Triggered by: a query gap, or explicit request like "research [topic]"

1. Search the web for authoritative sources on the topic
2. Create a source summary page in `wiki/sources/`
3. Update relevant `concepts/`, `sources/`, `outputs/`, or `entities/` pages with new information
4. Follow the full Ingest cross-linking and consistency steps
5. Record source URLs in frontmatter `sources:` fields

### Lint

Triggered by: "lint the wiki"

1. Scan all wiki pages for:
   - Contradictions between pages
   - Stale claims superseded by newer sources
   - Orphan pages with no inbound `[[links]]`
   - Concepts mentioned but lacking their own dedicated page
   - Missing bidirectional cross-references
   - Data gaps that could be filled with web research
2. Report all findings to the user
3. Fix issues with user approval
4. Suggest topics for web research
5. Prepend a one-line entry to `wiki/log.md` (directly below the `# Wiki Log` heading — newest first):
   ```
   ## [YYYY-MM-DD] lint | <summary of issues found/fixed>
   ```

---

## Consistency Rules

- **Bidirectional links:** Whenever a new page is created or a link is added, find the target page and add a reciprocal `[[link]]` back
- **Contradiction handling:** Never silently overwrite conflicting information — flag it with the blockquote format above and surface it to the user
- **Integrated content:** Wiki pages and best practices should read as current synthesized guidance, not as update logs. Put operational history in `wiki/log.md`, not in the body of content pages.
- **Frontmatter discipline:** Always include complete frontmatter; always update `updated:` on edit
- **Log every operation:** Ingest, query, lint, and analyze all get a log entry. Prepend it (newest first, directly below the `# Wiki Log` heading) and keep it to **one line** — a pointer for navigation, not a record of everything that happened. Don't read the rest of the log to write a new entry.

---

## index.md Format

```markdown
# Wiki Index
_Last updated: YYYY-MM-DD_

## Concepts
- [[Concept Page]] — Brief description of concept
- ...

## Entities
- ...

## Outputs
- ...

## Sources
- [[source-slug]] — Brief description | ingested YYYY-MM-DD
- ...
```

---

## log.md Format

The log is **newest-first**: each new entry is prepended directly below the `# Wiki Log` heading, pushing earlier entries down. Each entry is a heading line plus **exactly one line** of summary — a pointer so a reader can find the relevant pages/commit, not a narrative of the work. Don't restate page contents, list every cross-link touched, or explain reasoning; the pages and `git log` already have that.

```markdown
# Wiki Log

## [YYYY-MM-DD] ingest | <Source Title>
Created/updated [[Page A]], [[Page B]] from this source.

## [YYYY-MM-DD] query | <question summary>
Answered from [[Page A]], [[Page B]]; filed as [[New Page]].

## [YYYY-MM-DD] lint | <summary>
3 orphan pages, 2 missing cross-links — fixed. Research suggested: topic X.

## [YYYY-MM-DD] revise | <what changed>
<one line — the prior, longer entries predate this convention>
```

## Extra Rules to Follow
- You MUST NOT attempt any git operations
