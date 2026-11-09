#!/usr/bin/env bash
# Rebuild the committed demo store data/todos.db from scratch with the CLI only (no hand-written SQL).
# Run from anywhere; uses the repo's .venv. Commit the result.
set -euo pipefail

cd "$(dirname "$0")/.."
export TODO_FILE=data/todos.db
todo() { .venv/bin/python todo.py "$@" >/dev/null; }

rm -f "$TODO_FILE"
todo add "Write the README" --priority high
todo add "Add a dark theme" --label ui
todo add "Store todos in SQLite" --label storage
todo add "Board columns side by side" --label ui
todo add "Export to CSV" --due 2026-12-01
todo add "Set up CI"
todo move 3 in-progress
todo move 5 in-progress
todo done 4
todo done 6

.venv/bin/python todo.py list
