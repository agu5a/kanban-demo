---
name: card-implement
description: Implement one GitHub issue (card) in the current worktree - read the card, plan briefly, write tests first, implement, run mise run check, summarize. Use when asked to implement or work on issue #<n>.
argument-hint: <issue-number>
---

# Implement card #$ARGUMENTS

1. Read the card: `gh issue view $ARGUMENTS`. The card is the spec. If acceptance criteria are missing,
   ambiguous or contradict AGENTS.md, stop and list your questions; do not guess.
2. Read `AGENTS.md` and only the files the card names. Do not explore outside the repo.
3. Write a plan of 3-6 bullets: functions to add or change, tests to add (file and test names).
   Continue without waiting for approval unless step 1 raised questions.
4. Tests first: add tests for each acceptance criterion in `tests/test_<command>.py`. Run `mise run test`
   and confirm the new tests fail for the expected reason.
5. Implement the smallest change that passes. Reuse existing helpers (`find_todo`, `load_todos`,
   `save_todos`, `store_path`). Keep `cmd_*` functions and subparsers in the same order.
6. Run `mise run fmt`, then `mise run check` until green. Never delete or weaken an existing test.
7. Review `git diff`: revert anything the card did not ask for and list it as a follow-up instead.
8. Finish with a summary: what changed, tests added, `mise run check` result, follow-ups.
   Do not commit or push.
