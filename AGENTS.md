# kanban-demo

Minimal todo CLI (`todo.py`, stdlib only) used as a practice ground for board-driven agent work.

## Commands

- `mise trust && mise run setup` – create `.venv`, install dev deps, install git hooks (once per worktree)
- `mise run check` – lint + tests; must pass before you report a task done
- `mise run test` – `pytest -q`
- `mise run lint` – `ruff check .` + `ruff format --check .`
- `mise run fmt` – auto-fix formatting and lint findings

## Card workflow (human only)

Agents must not run these; they push, merge and edit the board.

- `scripts/wt-new.sh <n> [slug]` – branch `<n>-<slug>` via `gh issue develop`, worktree in `../kanban-demo.worktrees/`,
  `mise run setup`, board "In Progress"; prints the `cd` command
- `scripts/wt-done.sh <n>` – needs a clean worktree; rebase on `origin/main`, `mise run check`, push, PR (`Closes #<n>`),
  wait for CI, remove the worktree, squash merge
- `scripts/board-move.sh <n> <Todo|In Progress|Done>` – move the card, adding it to the board if missing

## Layout

- `todo.py` – the whole CLI: `cmd_<name>(args)` per subcommand, wired in `build_parser()`
- `tests/test_<command>.py` – one file per command, pytest style, runs `todo.py` via subprocess
- Store: JSON file at `$TODO_FILE` (default `todos.json`); tests point `TODO_FILE` at `tmp_path`

## Data schema

The store is a JSON list of objects: `{"id": int, "title": str, "done": bool}`.
`done` may be missing on old items and means `false`. `id` is always an `int` (argparse uses `type=int`);
never compare ids as strings. Look up items through one shared helper, not a per-command loop.

## Working rules

- The GitHub issue is the spec: read it with `gh issue view <n>`. Do only what it asks; list anything else as a follow-up.
- Work only inside the current working directory (a git worktree). Never read or edit the main checkout
  or other worktrees, and never search outside the repo (no `find /`, no `~`).
- Add pytest tests for every new behaviour. Keep all existing tests; never delete or weaken one.
- Run `mise run check` before finishing and report the result.
- Do not commit or push; the human commits.
- Finish with a short summary: what changed, which tests were added, what was left out.
