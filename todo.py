#!/usr/bin/env python3
"""Minimal todo CLI: add, list, done, undone, rm, edit and clear commands."""

import argparse
import json
import os
import sys


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


def cmd_add(args):
    path = store_path()
    todos = load_todos(path)
    todo_id = _next_id(todos)
    todos.append(normalize_todo({"id": todo_id, "title": args.title}))
    save_todos(path, todos)
    print(todo_id)
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


def cmd_list(args):
    path = store_path()
    todos = load_todos(path)
    if not todos:
        print("No todos")
        return 0
    for todo in todos:
        if not isinstance(todo, dict):
            continue
        todo_id = todo.get("id")
        title = todo.get("title", "")
        mark = "x" if _is_done(todo) else " "
        print(f"{todo_id} [{mark}] {title}{todo_suffixes(todo)}")
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
    add_parser.set_defaults(func=cmd_add)
    list_parser = subparsers.add_parser("list", help="list todos")
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
