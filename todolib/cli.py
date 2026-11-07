"""CLI commands and argument parsing for the todo application."""

import argparse
import os
import re
import sys

from todolib.model import (
    _date_type,
    _next_id,
    filter_todos,
    find_todo,
    is_open,
    is_overdue,
    sort_todos,
    today,
)
from todolib.render import EXPORTERS, list_line
from todolib.store import (
    InvalidStoreItem,
    UnsupportedStoreVersion,
    load_todos,
    normalize_todo,
    save_todos,
    store_path,
)

PRIORITIES = ("low", "normal", "high")


def _title_type(value):
    if value == "":
        raise argparse.ArgumentTypeError("title must not be empty")
    return value


def parse_label(value):
    name = value.lower()
    if re.fullmatch(r"[a-z0-9-]{1,20}", name) is None:
        raise argparse.ArgumentTypeError(f"invalid label: {value}")
    return name


def _due_type(value):
    """Argparse type for `due`'s <date|none> positional."""
    if value == "none":
        return None
    return _date_type(value)


def cmd_add(args):
    path = store_path()
    todos = load_todos(path)
    todo_id = _next_id(todos)
    due = args.due.isoformat() if args.due is not None else None
    labels = sorted(set(args.label or []))
    todos.append(
        normalize_todo(
            {
                "id": todo_id,
                "title": args.title,
                "priority": args.priority,
                "due": due,
                "labels": labels,
            }
        )
    )
    save_todos(path, todos)
    print(todo_id)
    return 0


def cmd_due(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    todo["due"] = args.date.isoformat() if args.date is not None else None
    save_todos(path, todos)
    return 0


def cmd_priority(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    todo["priority"] = args.level
    save_todos(path, todos)
    return 0


def cmd_label(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    current = todo.get("labels")
    if not isinstance(current, list):
        current = []
    name = args.name
    if args.action == "add":
        if name in current:
            return 0
        todo["labels"] = sorted(set(current) | {name})
    elif args.action == "rm":
        if name not in current:
            return 0
        todo["labels"] = sorted(label for label in current if label != name)
    save_todos(path, todos)
    return 0


def add_filter_args(parser):
    """Register the filter flags that filter_todos applies."""
    state_group = parser.add_mutually_exclusive_group()
    state_group.add_argument("--open", action="store_true", default=False, help="only open todos")
    state_group.add_argument("--done", action="store_true", default=False, help="only done todos")
    parser.add_argument(
        "--priority",
        choices=PRIORITIES,
        action="append",
        default=None,
        help="filter by priority (repeatable: any of the given levels)",
    )
    parser.add_argument(
        "--label",
        type=parse_label,
        action="append",
        default=None,
        help="filter by label (repeatable: all given labels)",
    )
    parser.add_argument("--search", default=None, help="case-insensitive substring match on title")
    parser.add_argument(
        "--overdue", action="store_true", default=False, help="only overdue open todos"
    )


def add_sort_arg(parser):
    """Register the ``--sort`` flag on ``parser``."""
    parser.add_argument(
        "--sort",
        choices=("id", "priority", "due"),
        default="id",
        help="sort order: id (default), priority, or due",
    )


def cmd_list(args):
    path = store_path()
    todos = load_todos(path)
    filtered = filter_todos(todos, args)
    ordered = sort_todos(filtered, args.sort)
    if not ordered:
        print("No todos")
        return 0
    for todo in ordered:
        if not isinstance(todo, dict):
            continue
        print(list_line(todo))
    return 0


def cmd_export(args):
    path = store_path()
    todos = load_todos(path)
    filtered = filter_todos(todos, args)
    ordered = sort_todos(filtered, args.sort)
    EXPORTERS[args.format](ordered, sys.stdout)
    return 0


def cmd_stats(args):
    path = store_path()
    todos = load_todos(path)
    cutoff = today()
    open_count = sum(1 for todo in todos if is_open(todo))
    done_count = sum(1 for todo in todos if not is_open(todo))
    overdue_count = sum(1 for todo in todos if is_overdue(todo, cutoff))
    total_count = len(todos)
    print(f"open: {open_count}")
    print(f"done: {done_count}")
    print(f"overdue: {overdue_count}")
    print(f"total: {total_count}")
    return 0


def cmd_done(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    todo["status"] = "done"
    save_todos(path, todos)
    return 0


def cmd_undone(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    todo["status"] = "todo"
    save_todos(path, todos)
    return 0


def cmd_edit(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    todo["title"] = args.title
    save_todos(path, todos)
    return 0


def cmd_rm(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    todos.remove(todo)
    save_todos(path, todos)
    return 0


def cmd_clear(args):
    path = store_path()
    if not os.path.exists(path):
        print(f"No todos file: {path}", file=sys.stderr)
        return 1
    todos = load_todos(path)
    kept = [todo for todo in todos if is_open(todo)]
    removed = len(todos) - len(kept)
    if removed:
        save_todos(path, kept)
    print(removed)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="todo.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_parser = subparsers.add_parser("add", help="add a todo")
    add_parser.add_argument("title", type=_title_type)
    add_parser.add_argument("--priority", choices=PRIORITIES, default="normal")
    add_parser.add_argument("--due", type=_date_type, default=None)
    add_parser.add_argument("--label", type=parse_label, action="append", default=None)
    add_parser.set_defaults(func=cmd_add)
    list_parser = subparsers.add_parser("list", help="list todos")
    add_filter_args(list_parser)
    add_sort_arg(list_parser)
    list_parser.set_defaults(func=cmd_list)
    done_parser = subparsers.add_parser("done", help="mark a todo done")
    done_parser.add_argument("id", type=int)
    done_parser.set_defaults(func=cmd_done)
    undone_parser = subparsers.add_parser("undone", help="mark a todo undone")
    undone_parser.add_argument("id", type=int)
    undone_parser.set_defaults(func=cmd_undone)
    edit_parser = subparsers.add_parser("edit", help="edit a todo")
    edit_parser.add_argument("id", type=int)
    edit_parser.add_argument("title", type=_title_type)
    edit_parser.set_defaults(func=cmd_edit)
    rm_parser = subparsers.add_parser("rm", help="remove a todo")
    rm_parser.add_argument("id", type=int)
    rm_parser.set_defaults(func=cmd_rm)
    clear_parser = subparsers.add_parser("clear", help="remove all done todos")
    clear_parser.set_defaults(func=cmd_clear)
    priority_parser = subparsers.add_parser("priority", help="set a todo's priority")
    priority_parser.add_argument("id", type=int)
    priority_parser.add_argument("level", choices=PRIORITIES)
    priority_parser.set_defaults(func=cmd_priority)
    due_parser = subparsers.add_parser("due", help="set a todo's due date")
    due_parser.add_argument("id", type=int)
    due_parser.add_argument("date", type=_due_type)
    due_parser.set_defaults(func=cmd_due)
    label_parser = subparsers.add_parser("label", help="add or remove a label")
    label_parser.add_argument("id", type=int)
    label_parser.add_argument("action", choices=("add", "rm"))
    label_parser.add_argument("name", type=parse_label)
    label_parser.set_defaults(func=cmd_label)
    export_parser = subparsers.add_parser("export", help="export todos")
    export_parser.add_argument("--format", choices=("json", "csv", "md"), default="json")
    add_filter_args(export_parser)
    add_sort_arg(export_parser)
    export_parser.set_defaults(func=cmd_export)
    stats_parser = subparsers.add_parser("stats", help="print todo statistics")
    stats_parser.set_defaults(func=cmd_stats)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UnsupportedStoreVersion as exc:
        print(f"Unsupported store version: {exc}", file=sys.stderr)
        return 1
    except InvalidStoreItem as exc:
        print(f"Invalid store item {exc}", file=sys.stderr)
        return 1
