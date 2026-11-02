---
name: card-write
description: Draft a GitHub issue (card) that an agent can implement without asking back, check it against the Definition of Ready, and create it with gh issue create after the user approves. Use when asked to write, draft or create a card, issue or ticket.
argument-hint: <short task description>
---

# Write a card: $ARGUMENTS

1. Read `AGENTS.md` (schema, conventions) and the code the task touches, so the card uses real names.
2. Ask the user at most 3 questions, only for what the code and AGENTS.md cannot answer.
3. Draft the card with exactly these headings (same as `.github/ISSUE_TEMPLATE/card.yml`):
   `### Goal`, `### Acceptance criteria`, `### Tests`, `### Files likely touched`, `### Out of scope`.
4. Check the Definition of Ready; every item must hold:
   - Goal: 1-2 sentences, user-visible outcome.
   - Each acceptance criterion is checkable: exact command, stdout/stderr, exit code, resulting store JSON.
   - Error paths are stated (unknown id, empty or missing store, invalid input).
   - Schema change is explicit, or the card says "no schema change".
   - Tests: file and cases named, plus "Keep existing tests".
   - Files likely touched and out-of-scope items are listed.
   - Small: one command or one refactor. Otherwise propose a split into several cards.
   - Does not depend on another card's unmerged work.
5. Show the draft and the DoR check. After the user approves, create it:
   `gh issue create --title "<title>" --body-file -` with the body on stdin. Print the URL.
