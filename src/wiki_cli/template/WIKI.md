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

## OKF Document Format

Every non-reserved file written in `wiki/` must use parseable YAML frontmatter with a non-empty `type`. `index.md` and `log.md` are reserved files and do not use concept frontmatter (the root `index.md` may declare `okf_version`).

```yaml
---
type: Concept | Reference | Entity
title: "<Page Title>"
tags: [tag-one, tag-two]
sources:
  - resource: https://example.com/source
    title: Source title
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

`sources` is optional and contains external web provenance only. Each source has a required `resource` URL and an optional `title`. Preserve unknown frontmatter keys when editing existing documents.

Always update the `updated:` field whenever a page is edited.

---

## Link Conventions

- **Internal links** (between wiki files): bundle-root Markdown paths — `[Display Text](/concepts/concept-page.md)`.
- **External links** (web sources): standard markdown — `[text](url)`
- Mirror every external `sources` entry in a terminal `## Citations` section.
- Put internal cross-references accumulated for a page in a terminal `## Related Concepts` section.
- Never use Obsidian `[[wiki links]]` in `wiki/` documents.

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

Follow the active `prose-voice` skill for this wiki. In a workspace, select the wiki before applying the shared root skill.

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
5. Add or update standard Markdown links and terminal `## Related Concepts` sections for all touched pages
6. Check for contradictions with existing wiki content:
   - Flag on the relevant wiki page with a blockquote: `> **Contradiction noted:** [description] — see also [Other Page](/concepts/other-page.md)`
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
2. Read the relevant pages and synthesize an answer with standard Markdown citations
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
5. Record external source URLs in structured frontmatter `sources:` entries and terminal `## Citations` sections

### Lint

Triggered by: "lint the wiki"

1. Scan all wiki pages for:
   - Contradictions between pages
   - Stale claims superseded by newer sources
   - Orphan pages with no inbound Markdown links
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

- **Bidirectional links:** Whenever a new page is created or a link is added, find the target page and add a reciprocal standard Markdown link back
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
- [Concept Page](/concepts/concept-page.md) — Brief description of concept
- ...

## Entities
- ...

## Outputs
- ...

## Sources
- [Source](/sources/source-slug.md) — Brief description | ingested YYYY-MM-DD
- ...
```

---

## log.md Format

The log is **newest-first**: each new entry is prepended directly below the `# Wiki Log` heading, pushing earlier entries down. Each entry is a heading line plus **exactly one line** of summary — a pointer so a reader can find the relevant pages/commit, not a narrative of the work. Don't restate page contents, list every cross-link touched, or explain reasoning; the pages and `git log` already have that.

```markdown
# Wiki Log

## [YYYY-MM-DD] ingest | <Source Title>
Created/updated [Page A](/concepts/page-a.md), [Page B](/concepts/page-b.md) from this source.

## [YYYY-MM-DD] query | <question summary>
Answered from [Page A](/concepts/page-a.md), [Page B](/concepts/page-b.md); filed as [New Page](/concepts/new-page.md).

## [YYYY-MM-DD] lint | <summary>
3 orphan pages, 2 missing cross-links — fixed. Research suggested: topic X.

## [YYYY-MM-DD] revise | <what changed>
<one line — the prior, longer entries predate this convention>
```

## Extra Rules to Follow
- You MUST NOT attempt any git operations
