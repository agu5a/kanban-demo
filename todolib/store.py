"""Storage layer: store path, load/save with validation and migration."""

import json
import os
import sqlite3
from pathlib import Path

STATUSES = ("todo", "in-progress", "done")


class UnsupportedStoreVersion(Exception):
    pass


class InvalidStoreItem(Exception):
    pass


def store_path():
    return os.environ.get("TODO_FILE", "data/todos.db")


def normalize_todo(todo):
    """Return an item with exactly the six v3 fields, in the required order."""
    return {
        "id": todo.get("id"),
        "title": todo.get("title"),
        "status": todo.get("status", "todo"),
        "priority": todo.get("priority", "normal"),
        "due": todo.get("due", None),
        "labels": todo.get("labels", []),
    }


def _is_sqlite_path(path):
    return Path(path).suffix.lower() == ".db"


def load_todos(path):
    if _is_sqlite_path(path):
        return _load_todos_sqlite(path)
    return _load_todos_json(path)


def _load_todos_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return []
    if not text.strip():
        return []
    data = json.loads(text)
    if isinstance(data, list):
        version = 1
        items = data
    elif isinstance(data, dict):
        version = data.get("version")
        if type(version) is not int or version not in (2, 3):
            raise UnsupportedStoreVersion(version)
        items = data.get("todos", [])
        if not isinstance(items, list):
            items = []
    else:
        return []
    # v1 (JSON list) and v2 items carry `done`; they are read as v3 (only JSON `true` means done)
    migrate = version in (1, 2)
    result = []
    seen_ids = set()
    for position, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        if "id" not in item:
            raise InvalidStoreItem(f"{position}: missing id")
        item_id = item["id"]
        if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 1:
            raise InvalidStoreItem(f"{position}: invalid id")
        if item_id in seen_ids:
            raise InvalidStoreItem(f"{position}: duplicate id")
        if "title" not in item:
            raise InvalidStoreItem(f"{position}: missing title")
        title = item["title"]
        if not isinstance(title, str) or title == "":
            raise InvalidStoreItem(f"{position}: invalid title")
        if not migrate and "status" in item and item["status"] not in STATUSES:
            # v3: validate status if present, checked after id and title
            raise InvalidStoreItem(f"{position}: invalid status")
        seen_ids.add(item_id)
        if migrate:
            migrated = dict(item)
            migrated["status"] = "done" if item.get("done") is True else "todo"
            migrated.pop("done", None)
            result.append(normalize_todo(migrated))
        else:
            result.append(normalize_todo(item))
    return result


def _load_todos_sqlite(path):
    # If file doesn't exist, return empty list (don't create it)
    if not Path(path).exists():
        return []

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        # Check user_version for schema version
        cursor = conn.execute("PRAGMA user_version")
        user_version = cursor.fetchone()[0]
        if user_version != 3:
            raise UnsupportedStoreVersion(user_version)

        # Check if table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='todos'")
        if not cursor.fetchone():
            return []

        # Load todos
        cursor = conn.execute(
            "SELECT id, title, status, priority, due, labels FROM todos ORDER BY id"
        )
        rows = cursor.fetchall()

        result = []
        for row in rows:
            item = dict(row)
            # labels is stored as JSON string
            if item["labels"]:
                item["labels"] = json.loads(item["labels"])
            else:
                item["labels"] = []
            # Validate status
            if item["status"] not in STATUSES:
                raise InvalidStoreItem(f"invalid status: {item['status']}")
            result.append(normalize_todo(item))
        return result
    except sqlite3.DatabaseError as e:
        # Not a valid SQLite database or corrupted
        raise InvalidStoreItem(f"not a database: {e}") from None
    finally:
        conn.close()


def save_todos(path, todos):
    if _is_sqlite_path(path):
        _save_todos_sqlite(path, todos)
    else:
        _save_todos_json(path, todos)


def _save_todos_json(path, todos):
    normalized = []
    for todo in todos:
        if isinstance(todo, dict):
            normalized.append(normalize_todo(todo))
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 3, "todos": normalized}, f, indent=2)
        f.write("\n")


def _save_todos_sqlite(path, todos):
    # Ensure parent directory exists
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        # Create table with schema if not exists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('todo', 'in-progress', 'done')),
                priority TEXT NOT NULL DEFAULT 'normal',
                due TEXT,
                labels TEXT NOT NULL DEFAULT '[]'
            )
        """)
        # Set user_version to 3
        conn.execute("PRAGMA user_version = 3")

        # Clear existing data
        conn.execute("DELETE FROM todos")

        # Insert todos
        for todo in todos:
            if not isinstance(todo, dict):
                continue
            normalized = normalize_todo(todo)
            labels_json = json.dumps(normalized["labels"])
            conn.execute(
                "INSERT INTO todos (id, title, status, priority, due, labels) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    normalized["id"],
                    normalized["title"],
                    normalized["status"],
                    normalized["priority"],
                    normalized["due"],
                    labels_json,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def init_demo_db(path):
    """Initialize a SQLite database with demo items in every status."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('todo', 'in-progress', 'done')),
                priority TEXT NOT NULL DEFAULT 'normal',
                due TEXT,
                labels TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.execute("PRAGMA user_version = 3")

        conn.execute("DELETE FROM todos")

        demo_items = [
            (1, "Learn SQL", "todo", "high", None, "[]"),
            (2, "Build a schema", "todo", "normal", "2026-01-15", '["sql", "schema"]'),
            (3, "Write queries", "in-progress", "high", "2026-01-10", '["sql", "queries"]'),
            (4, "Add indexes", "in-progress", "normal", None, '["sql", "indexes"]'),
            (5, "Test the app", "done", "high", "2026-01-05", '["testing"]'),
            (6, "Deploy to prod", "done", "normal", None, '["deploy"]'),
        ]

        for item in demo_items:
            conn.execute(
                "INSERT INTO todos (id, title, status, priority, due, labels) VALUES (?, ?, ?, ?, ?, ?)",
                item,
            )
        conn.commit()
    finally:
        conn.close()
