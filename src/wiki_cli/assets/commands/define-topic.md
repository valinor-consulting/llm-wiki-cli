---
description: Interview the user and write a complete TOPIC.md defining what this wiki covers.
argument-hint: (no arguments — just run it and answer the questions)
---

# Define this wiki's topic

You are setting the scope for a fresh LLM-maintained wiki. Your job is to interview the
user and then write a complete `TOPIC.md` that describes what this wiki is about and how it
should be researched and maintained. This is a one-time setup step.

## Before you ask anything

Read these files so you understand the conventions you're writing into:

- `TOPIC.md` — the file you will rewrite. Note its four headings: `# Topic`,
  `## Topics to Cover`, `## Instructions for Each Topic`, `## Out of Scope`.
- `WIKI.md` — the operating schema for this wiki (directory structure, page types,
  frontmatter, operations). The topic you define has to fit this structure.
- `llm-wiki.md` — background on the LLM Wiki pattern, so the scope you set is realistic for
  what the wiki can actually do.

Do not create or edit any wiki pages, and do not touch `raw/` or `Clippings/`. The only
file you write in this command is `TOPIC.md`.

## How to run the interview

Ask **one question at a time**, in plain language, and wait for the answer before moving
on. Keep it tight: a handful of focused questions, not a long form. Use the user's earlier
answers to skip or shorten later questions. If an answer is vague, ask a single follow-up
rather than accepting filler.

Cover these areas, roughly in this order:

1. **Main subject and purpose.** What is this wiki about, and why does it exist? Who reads
   it, and what should they be able to get from it?
2. **Topics to cover.** Which 3 to 8 sub-topics make up the subject? Get a real list, not a
   single broad bucket.
3. **Per-topic direction.** For the sub-topics that need it: how deep should coverage go,
   what angle or perspective matters, what does "done" look like, and are there preferred or
   off-limits sources?
4. **Out of scope.** What related material should the wiki deliberately *not* cover, so it
   doesn't sprawl?
5. **Expected source types.** What kind of material will feed this wiki (papers, docs, web
   articles, internal notes, transcripts)? This tells the research operations where to look.

## Writing TOPIC.md

When you have enough to work with, play back a short summary of what you heard and ask the
user to confirm or correct it. Only after they confirm, write `TOPIC.md`.

Preserve the four headings exactly (`# Topic`, `## Topics to Cover`,
`## Instructions for Each Topic`, `## Out of Scope`) and remove every `<!-- comment -->`
hint from the template. Fill each section with the user's answers:

- Under `# Topic`, write one or two sentences naming the subject and its purpose/audience.
- Under `## Topics to Cover`, list the agreed sub-topics.
- Under `## Instructions for Each Topic`, capture the per-topic depth, angle, "done"
  criteria, and source preferences. Tie each instruction to the topic it governs.
- Under `## Out of Scope`, list what the wiki will not cover. Note expected source types
  here or under Topic, wherever it reads more naturally.

Write it in clear, human prose following the `prose-voice` skill: complete sentences, bold
only the occasional key term, no em-dash connectors, real bullet lists only for genuine
lists. A reader should not be able to tell an LLM wrote it.

Do not run any git operations. When `TOPIC.md` is written, tell the user it's ready and
point them at the next step: add sources to `raw/` and ask you to ingest them.
