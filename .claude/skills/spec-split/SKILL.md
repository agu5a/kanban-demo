---
name: spec-split
description: Split a spec in docs/spec/ into Definition-of-Ready cards with dependencies, review them with the user, and create them with gh issue create after approval. Use when asked to split, break down or plan a spec into cards, issues or tickets.
argument-hint: <docs/spec/file.md>
---

# Split a spec into cards: $ARGUMENTS

1. Read `AGENTS.md`, the spec, `.claude/skills/card-write/SKILL.md` (card headings and Definition of Ready) and the code
   the spec touches, so cards use real names.
2. Plan the split and show it as a table before writing any card: card title, spec section(s), depends on,
   size. Rules:
   - One card = one command or one refactor, small enough for one agent session (card-write DoR "Small").
   - A shared change several sections need (schema, helper, loader) is its own card and comes first.
   - Follow the spec's delivery order; cards with no dependency between them stay independent so they can run in
     parallel.
   - Every spec requirement lands in exactly one card. List requirements you could not place.
   Ask the user to approve or change the plan. Wait.
3. Draft every card with the card-write headings. In addition:
   - First line of `### Goal`: `Spec: docs/spec/<file>.md §<n>` (the sections the card implements, not the whole spec).
   - Under the goal, `Depends on: <card titles>` when it has dependencies; omit the line otherwise.
   - Copy the exact rules the card needs from the spec into the acceptance criteria (commands, output, exit codes,
     store JSON). The card must be implementable from the card plus the named section, without reading the rest.
   - `### Tests`: file and backticked `test_*` names for every criterion, including error paths, plus
     "Keep existing tests". Name any existing test whose expected output the card changes.
4. Check each card against the card-write Definition of Ready, except "Does not depend on another card's unmerged
   work": that one holds when its dependencies are merged. Show all drafts with the DoR check, one card per
   block, numbered. The user approves, edits or rejects each one. Count the cards the user changed or rejected
   and report the count at the end.
5. After approval, create the cards in dependency order so the `Depends on:` lines can use real numbers:
   `gh issue create --title "<title>" --body-file -` with the body on stdin; replace titles with `#<n>` in later
   cards before creating them. Print a table: number, title, depends on, URL.
6. Do not move cards on the board and do not start implementation; the human does both.
