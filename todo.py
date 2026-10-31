#!/usr/bin/env python3
"""Minimal todo CLI: add command."""

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


def cmd_add(args):
    path = store_path()
    todos = load_todos(path)
    todo_id = _next_id(todos)
    todos.append({"id": todo_id, "title": args.title})
    save_todos(path, todos)
    print(todo_id)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="todo.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_parser = subparsers.add_parser("add", help="add a todo")
    add_parser.add_argument("title")
    add_parser.set_defaults(func=cmd_add)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
