#!/usr/bin/env python3
"""Minimal todo CLI: add, list, done, undone, rm, edit, clear, priority, due, label, export, stats."""

import sys

from todolib import cli, model, render, store

# Re-export public names so existing callers/tests keep working.
UnsupportedStoreVersion = store.UnsupportedStoreVersion
InvalidStoreItem = store.InvalidStoreItem
STATUSES = store.STATUSES
store_path = store.store_path
normalize_todo = store.normalize_todo
load_todos = store.load_todos
save_todos = store.save_todos
_next_id = model._next_id
is_open = model.is_open
is_overdue = model.is_overdue
find_todo = model.find_todo
move_todo = model.move_todo
UnknownTodoId = model.UnknownTodoId
_date_type = model._date_type
_due_date_value = model._due_date_value
filter_todos = model.filter_todos
sort_todos = model.sort_todos
today = model.today
todo_suffixes = render.todo_suffixes
status_mark = render.status_mark
PRIORITIES = cli.PRIORITIES
_title_type = cli._title_type
parse_label = cli.parse_label
_due_type = cli._due_type
add_filter_args = cli.add_filter_args
add_sort_arg = cli.add_sort_arg
build_parser = cli.build_parser
main = cli.main


if __name__ == "__main__":
    sys.exit(main() or 0)
