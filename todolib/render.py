"""Rendering: `list` lines, todo suffixes and the export formats (json, csv, md)."""

import csv
import json


def status_mark(todo):
    """Map a todo's status to its list/export mark character."""
    if not isinstance(todo, dict):
        return " "
    status = todo.get("status")
    if status == "done":
        return "x"
    if status == "in-progress":
        return "~"
    return " "


def todo_suffixes(todo):
    """Return the priority/due/label/assignee suffix string for a todo."""
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
    assignee = todo.get("assignee")
    if assignee:
        suffix += f" @{assignee}"
    return suffix


def list_line(todo):
    """One `list` output line, e.g. `3 [~] Write report (high)`."""
    mark = status_mark(todo)
    return f"{todo.get('id')} [{mark}] {todo.get('title', '')}{todo_suffixes(todo)}"


def export_json(todos, out):
    print(json.dumps(todos, indent=2), file=out)


def export_csv(todos, out):
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["id", "title", "status", "priority", "due", "labels", "assignee"])
    for todo in todos:
        labels = todo["labels"] if isinstance(todo["labels"], list) else []
        writer.writerow(
            [
                todo["id"],
                todo["title"],
                todo.get("status", "todo"),
                todo["priority"],
                todo["due"],
                ";".join(str(label) for label in labels),
                todo.get("assignee") or "",
            ]
        )


def export_md(todos, out):
    for todo in todos:
        mark = status_mark(todo)
        print(f"- [{mark}] {todo['title']}{todo_suffixes(todo)}", file=out)


EXPORTERS = {"json": export_json, "csv": export_csv, "md": export_md}
