# kanban-demo

Minimal todo CLI (`todo.py`, stdlib only) used as a practice ground for board-driven agent work.

## Commands

- `mise trust && mise run setup` – create `.venv`, install dev deps, install Chromium, install git hooks (once per worktree)
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

- `todo.py` – thin entry point: calls `todolib.cli.main()` under `if __name__ == "__main__":` and re-exports the
  names tests import; no command logic
- `todolib/store.py` – store path, load/save, `normalize_todo`, migration, store exceptions
- `todolib/model.py` – lookup (`find_todo`, `_next_id`), `filter_todos`, `sort_todos` and sort keys, the open/done
  decision, date helpers (`today`, `_date_type`, `_due_date_value`)
- `todolib/render.py` – `list` lines, `todo_suffixes`, export formats (json, csv, md)
- `todolib/web.py` – read-only web board (serve)
- `todolib/cli.py` – `cmd_<name>(args)` per subcommand, argparse types, `build_parser()`, `main()`
- `todolib/static/` – vendored static files served at `/static/<name>` (now Bootstrap 5.3.8 `bootstrap.min.css`,
  unchanged from the official dist; replace the file, never edit it)
- `tests/test_<command>.py` – one file per command, pytest style, runs `todo.py` via subprocess
- Store: JSON file at `$TODO_FILE` (default `todos.json`); tests point `TODO_FILE` at `tmp_path`

## Data schema

The store is a JSON object: `{"version": 3, "todos": [{"id": int, "title": str, "status": str, "priority": str, "due": str or null, "labels": [str]}]}`.
v1 files are JSON lists and v2 files are version 2 objects; both are read/migrated on first write. Each item carries
all six fields in order: `id`, `title`, `status`, `priority`, `due`, `labels`. Missing `status` defaults to `"todo"`;
other missing fields get defaults (`priority="normal"`, `due=null`, `labels=[]`). v2 `done: true` (exactly JSON true)
migrates to `status: "done"`; anything else migrates to `"todo"`. `id` is always an `int` (argparse uses `type=int`);
never compare ids as strings. Look up items through one shared helper, not a per-command loop.

## Working rules

- The GitHub issue is the spec: read it with `gh issue view <n>`. Do only what it asks; list anything else as a follow-up.
- Work only inside the current working directory (a git worktree). Never read or edit the main checkout
  or other worktrees, and never search outside the repo (no `find /`, no `~`).
- Add pytest tests for every new behaviour. Keep all existing tests; never delete or weaken one.
- Run `mise run check` before finishing and report the result.
- Commit only when the human asks for it in the session; never push. Headless workers never commit.
- Finish with a short summary: what changed, which tests were added, what was left out.
