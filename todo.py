#!/usr/bin/env python3
"""Minimal todo CLI: add, list, done, undone, rm, edit, clear, priority, due, label, export."""

import sys

from todolib import cli, model, render, store

# Re-export public names so existing callers/tests keep working.
UnsupportedStoreVersion = store.UnsupportedStoreVersion
InvalidStoreItem = store.InvalidStoreItem
store_path = store.store_path
normalize_todo = store.normalize_todo
load_todos = store.load_todos
save_todos = store.save_todos
_next_id = model._next_id
_is_done = model._is_done
find_todo = model.find_todo
_date_type = model._date_type
_due_date_value = model._due_date_value
filter_todos = model.filter_todos
sort_todos = model.sort_todos
today = model.today
todo_suffixes = render.todo_suffixes
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
