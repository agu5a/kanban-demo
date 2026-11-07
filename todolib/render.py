"""Rendering: `list` lines, todo suffixes and the export formats (json, csv, md)."""

import csv
import json

from todolib.model import _is_done


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


def list_line(todo):
    """One `list` output line, e.g. `3 [x] Write report (high)`."""
    mark = "x" if _is_done(todo) else " "
    return f"{todo.get('id')} [{mark}] {todo.get('title', '')}{todo_suffixes(todo)}"


def export_json(todos, out):
    print(json.dumps(todos, indent=2), file=out)


def export_csv(todos, out):
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["id", "title", "done", "priority", "due", "labels"])
    for todo in todos:
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


def export_md(todos, out):
    for todo in todos:
        mark = "x" if _is_done(todo) else " "
        print(f"- [{mark}] {todo['title']}{todo_suffixes(todo)}", file=out)


EXPORTERS = {"json": export_json, "csv": export_csv, "md": export_md}
