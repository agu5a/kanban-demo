#!/usr/bin/env python3
"""Minimal todo CLI: add, list, done, undone, rm, edit, clear, priority, due, label, export."""

import argparse
import csv
import datetime
import json
import os
import re
import sys

PRIORITIES = ("low", "normal", "high")


class UnsupportedStoreVersion(Exception):
    pass


def store_path():
    return os.environ.get("TODO_FILE", "todos.json")


def normalize_todo(todo):
    """Return an item with exactly the six v2 fields, in the required order."""
    return {
        "id": todo.get("id"),
        "title": todo.get("title"),
        "done": todo.get("done", False),
        "priority": todo.get("priority", "normal"),
        "due": todo.get("due", None),
        "labels": todo.get("labels", []),
    }


def load_todos(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return []
    if not text.strip():
        return []
    data = json.loads(text)
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        version = data.get("version")
        if type(version) is not int or version != 2:
            raise UnsupportedStoreVersion(version)
        items = data.get("todos", [])
        if not isinstance(items, list):
            items = []
    else:
        return []
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(normalize_todo(item))
    return result


def save_todos(path, todos):
    normalized = []
    for todo in todos:
        if isinstance(todo, dict):
            normalized.append(normalize_todo(todo))
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 2, "todos": normalized}, f, indent=2)
        f.write("\n")


def _next_id(todos):
    return max((t.get("id", 0) for t in todos if isinstance(t, dict)), default=0) + 1


def _is_done(todo):
    if not isinstance(todo, dict):
        return False
    return bool(todo.get("done"))


def find_todo(todos, todo_id):
    for todo in todos:
        if isinstance(todo, dict) and todo.get("id") == todo_id:
            return todo
    return None


def _title_type(value):
    if value == "":
        raise argparse.ArgumentTypeError("title must not be empty")
    return value


def parse_label(value):
    name = value.lower()
    if re.fullmatch(r"[a-z0-9-]{1,20}", name) is None:
        raise argparse.ArgumentTypeError(f"invalid label: {value}")
    return name


def _date_type(value):
    """Strict argparse type for a YYYY-MM-DD calendar date."""
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date: {value}") from None
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError(f"invalid date: {value}")
    return parsed


def _due_type(value):
    """Argparse type for `due`'s <date|none> positional."""
    if value == "none":
        return None
    return _date_type(value)


def today():
    """Return today's date as a datetime.date, honouring TODO_TODAY."""
    raw = os.environ.get("TODO_TODAY")
    if raw is None:
        return datetime.date.today()
    try:
        return _date_type(raw)
    except argparse.ArgumentTypeError:
        print(f"Invalid TODO_TODAY: {raw}", file=sys.stderr)
        raise SystemExit(1) from None


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


def todo_suffixes(todo):
    """Return the priority/due/label suffix string for a todo."""
    suffix = ""
    priority = todo.get("priority")
    if priority == "high":
        suffix += " (high)"
    elif priority == "low":
        suffix += " (low)"
    due = todo.get("due")
    if due is not None:
        suffix += f" due:{due}"
    labels = todo.get("labels")
    if isinstance(labels, list):
        for label in labels:
            suffix += f" #{label}"
    return suffix


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


def _due_date_value(todo):
    """Return the stored due date, or None when it is absent or malformed."""
    due = todo.get("due")
    if not isinstance(due, str):
        return None
    try:
        return datetime.date.fromisoformat(due)
    except ValueError:
        return None


def filter_todos(todos, args):
    """Return the todos matching every filter set by add_filter_args."""
    # Up front, so a bad TODO_TODAY fails even when no item reaches the date comparison.
    cutoff = today() if args.overdue else None
    result = []
    for todo in todos:
        if args.open and _is_done(todo):
            continue
        if args.done and not _is_done(todo):
            continue
        if args.priority and todo.get("priority") not in args.priority:
            continue
        if args.label:
            todo_labels = todo.get("labels")
            if not isinstance(todo_labels, list):
                todo_labels = []
            if not all(label in todo_labels for label in args.label):
                continue
        if args.search is not None:
            title = todo.get("title")
            title = title if isinstance(title, str) else ""
            if args.search.lower() not in title.lower():
                continue
        if args.overdue:
            if _is_done(todo):
                continue
            due_date = _due_date_value(todo)
            if due_date is None or due_date >= cutoff:
                continue
        result.append(todo)
    return result


def _todo_id(todo):
    """Return the id as a sort key; a non-integer id in a hand-edited store counts as 0."""
    todo_id = todo.get("id")
    return todo_id if isinstance(todo_id, int) else 0


def _priority_rank(todo):
    priority = todo.get("priority")
    if priority == "high":
        return 0
    if priority == "low":
        return 2
    return 1


def _due_sort_key(todo):
    due_date = _due_date_value(todo)
    if due_date is None:
        return (1, 0, _todo_id(todo))
    return (0, due_date.toordinal(), _todo_id(todo))


def sort_todos(todos, key):
    """Return a new list of todos ordered by key: "id", "priority" or "due"."""
    if key == "priority":
        return sorted(todos, key=lambda todo: (_priority_rank(todo), _todo_id(todo)))
    if key == "due":
        return sorted(todos, key=_due_sort_key)
    return sorted(todos, key=_todo_id)


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
        todo_id = todo.get("id")
        title = todo.get("title", "")
        mark = "x" if _is_done(todo) else " "
        print(f"{todo_id} [{mark}] {title}{todo_suffixes(todo)}")
    return 0


def cmd_export(args):
    path = store_path()
    todos = load_todos(path)
    filtered = filter_todos(todos, args)
    ordered = sort_todos(filtered, args.sort)
    if args.format == "json":
        print(json.dumps(ordered, indent=2))
    elif args.format == "csv":
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow(["id", "title", "done", "priority", "due", "labels"])
        for todo in ordered:
            labels = todo["labels"] if isinstance(todo["labels"], list) else []
            writer.writerow(
                [
                    todo["id"],
                    todo["title"],
                    "true" if _is_done(todo) else "false",
                    todo["priority"],
                    todo["due"],
                    ";".join(str(label) for label in labels),
                ]
            )
    else:
        for todo in ordered:
            mark = "x" if _is_done(todo) else " "
            print(f"- [{mark}] {todo['title']}{todo_suffixes(todo)}")
    return 0


def cmd_done(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    todo["done"] = True
    save_todos(path, todos)
    return 0


def cmd_undone(args):
    path = store_path()
    todos = load_todos(path)
    todo = find_todo(todos, args.id)
    if todo is None:
        print(f"Unknown id: {args.id}", file=sys.stderr)
        return 1
    todo["done"] = False
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
    kept = [todo for todo in todos if not _is_done(todo)]
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
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UnsupportedStoreVersion as exc:
        print(f"Unsupported store version: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
