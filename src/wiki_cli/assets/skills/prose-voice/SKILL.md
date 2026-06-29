---
name: prose-voice
description: Write or revise .md files in a clear human consultant voice, free of LLM-speak (decorative bold, em-dash sprawl, comma/semicolon pseudo-lists, colon-led fragments, rhetorical tics). Use whenever creating or editing .md files.
---

# Writing deliverables in a human voice

These files are consulting deliverables read by client executives and
practitioners. They must read like a person wrote them, not like default LLM output.
Follow the voice guide below, then run the drafting process before calling a file done.

## Voice guide

Each rule has a real before/after drawn from consultant deliverables.

### 1. Bold only key terms, never phrases or whole sentences

Bold marks a term the reader should anchor on, used sparingly. It is not emphasis
spray. Never bold a full sentence, and keep at most one or two bold terms per
paragraph. A bolded label that leads a list item (e.g. `- **Greenfield first.**`)
is fine; a bolded clause buried in prose is not.

- Bad: `**The single most valuable thing leadership can do is agree, in advance, that the dip is planned.**`
- Good: `The most valuable thing leadership can do is agree, in advance, that the dip is planned.`

### 2. Default connectors are commas, periods, and parentheses, not em dashes

The em dash is the single biggest LLM tell. Prefer two short sentences, or a comma,
or parentheses. Reserve the em dash for the rare genuine aside, roughly one per page.

- Bad: `AI adoption produces a temporary productivity dip before the gains — the "tuition cost of transformation" — driven mostly by the verification tax.`
- Good: `AI adoption produces a temporary productivity dip before the gains. This is the tuition cost of transformation, driven mostly by the verification tax (the effort of reviewing more AI-generated code).`

### 3. Three or more items is a list, not a comma run

When you find yourself joining items with commas or semicolons inside a sentence or
a table cell, stop and make a real bulleted list. This is the worst offender in
table cells, where it produces unreadable walls.

- Bad (one table cell): `constitution standard, spec right-sizing, /clarify+/checklist discipline, the Figma-Make keep, a metrics baseline captured now, tool standardization, and change-management groundwork`
- Good: a bulleted list, or a short cell ("Establish one repeatable SDD process") that links to a section where the items are bulleted.

### 4. Drop staged contrast tics

State the point plainly instead of staging a contrast.

- Bad: `This is not a reason to wait; it is a reason to sequence.`
- Good: `We should sequence greenfield work first rather than wait.`
- Bad: `LSP is navigation, not policy. It tells the agent how the code is wired, but it does not enforce that the agent respects the architecture.`
- Good: `LSP navigation tells the agent how the code is wired, but it does not enforce that the agent respects the architecture.`

### 5. Plain, declarative consultant register

Cut breathless intensifiers ("enormously," "the single most," "real and evidenced").
Cut throat-clearing ("It is worth noting that"). Say the thing once, directly. Lead
with the recommendation, then the reason.

### 6. Write multipliers with a plain letter x, not the math sign

The `×` multiplication sign reads as math notation, not prose.

- Bad: `2× and then 3× R&D output`, `a swing of roughly 4×`
- Good: `2x and then 3x R&D output`, `a swing of roughly 4x`

### 7. Headings and titles: short Title Case, no flourishes

Headings and the frontmatter `title:` use Title Case, stay short (six words or
fewer), carry no comma/subtitle flourish, and end without a period. Write a label,
not a sentence.

- Bad: `## The business case, stated honestly` -> Good: `## The Business Case`
- Bad: `## What we ask of leadership` -> Good: `## Requested Leadership Actions`

### 8. Never use "ask" as a noun

"Ask" is a verb. Using it as a noun ("the ask," "a reasonable ask," "the core ask")
is jargon that reads unprofessional in a deliverable. Replace it with "request,"
"requirement," "expectation," or whatever the context actually means.

- Bad: `The ask from leadership is modest.`
- Good: `The requirement from leadership is modest.`

### 9. Do not use colons to stage the sentence

Default LLM prose often uses a colon as a hinge after a label, count, or dramatic
setup phrase. Fold the relationship into the sentence instead. Let the verb carry
the point, or use a comma when the second half explains the first.

- Bad: `Three things are still undefined: the standard operating procedure, the constitution model, and the QA/DevOps integration.`
- Good: `The standard operating procedure, the constitution model, and the QA/DevOps integration are still undefined.`
- Bad: `DORA's central finding: AI amplifies. It does not fix.`
- Good: `DORA's central finding is that AI amplifies existing practices but does not inherently fix them.`
- Bad: `SDD inverts the source of truth: the **spec**, not the code, becomes the artifact teams argue over and maintain.`
- Good: `SDD inverts the source of truth, making the spec the artifact teams argue over and maintain rather than the code.`

## Drafting process

Run this before you consider any deliverable .md file finished.

1. **Draft** the content following the voice guide above.
2. **Lint** the file(s) you wrote:
   ```
   python3 "${CLAUDE_PROJECT_DIR}/.claude/skills/prose-voice/lint-prose.py" <file>.md
   ```
   To scan a full directory instead of a single file:
   ```
   python3 "${CLAUDE_PROJECT_DIR}/.claude/skills/prose-voice/lint-prose.py" --dir <deliverables-dir>/
   ```
   Work through the flagged lines and fix the mechanical tells. The linter is
   advisory (it never blocks and always exits 0), and some hits are acceptable
   (e.g. a bolded list-item label, a single intentional dash). Use judgment, but
   the default is to fix.
3. **Judgment review pass.** Spawn a subagent to read the draft as its target
   audience (an executive sponsor, a practitioner, etc.) and critique for clarity
   and human voice. Ask it specifically:
   - Does every bold term earn its emphasis, or is bold decorative?
   - Does any sentence still read like LLM default register?
   - Are there dense paragraphs that should be tightened or broken into lists?
   - Would a busy human reader get the point on one pass?

   Apply the worthwhile feedback. (This mirrors the project's split: mechanical
   rules go to the linter, judgment goes to a subagent.)

## Notes

- This skill owns the full writing standard. The linter enforces only the
  mechanical subset and is deliberately advisory, not a blocking hook.
- The standard applies to new and edited deliverable content. There is no bulk
  rewrite of existing files unless asked.
