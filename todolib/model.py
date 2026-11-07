"""Model helpers: lookup, filtering, sorting, dates."""

import argparse
import datetime
import os
import sys


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


def _date_type(value):
    """Strict argparse type for a YYYY-MM-DD calendar date."""
    try:
        parsed = datetime.date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date: {value}") from None
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError(f"invalid date: {value}")
    return parsed


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
