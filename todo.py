#!/usr/bin/env python3
"""Minimal todo CLI: add, list, and done commands."""

import argparse
import json
import os
import sys


def store_path():
    return os.environ.get("TODO_FILE", "todos.json")


def load_todos(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    return data if isinstance(data, list) else []


def save_todos(path, todos):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(todos, f, indent=2)
        f.write("\n")


def _next_id(todos):
    return max((t.get("id", 0) for t in todos if isinstance(t, dict)), default=0) + 1


def _is_done(todo):
    if not isinstance(todo, dict):
        return False
    return bool(todo.get("done"))


def cmd_add(args):
    path = store_path()
    todos = load_todos(path)
    todo_id = _next_id(todos)
    todos.append({"id": todo_id, "title": args.title})
    save_todos(path, todos)
    print(todo_id)
    return 0


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
        print(f"{todo_id} [{mark}] {title}")
    return 0

def cmd_done(args):
    path = store_path()
    todos = load_todos(path)
    todo_id = args.id
    for todo in todos:
        if isinstance(todo, dict) and (todo.get("id") == todo_id or str(todo.get("id")) == str(todo_id)):
            todo["done"] = True
            save_todos(path, todos)
            return 0
    print(f"Unknown id: {todo_id}", file=sys.stderr)
    return 1


def build_parser():
    parser = argparse.ArgumentParser(prog="todo.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_parser = subparsers.add_parser("add", help="add a todo")
    add_parser.add_argument("title")
    add_parser.set_defaults(func=cmd_add)
    list_parser = subparsers.add_parser("list", help="list todos")
    list_parser.set_defaults(func=cmd_list)
    done_parser = subparsers.add_parser("done", help="mark a todo done")
    done_parser.add_argument("id", type=int)
    done_parser.set_defaults(func=cmd_done)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
