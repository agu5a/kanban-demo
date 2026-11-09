"""Storage layer: store path, load/save with validation and migration.

Two backends behind `load_todos(path)` / `save_todos(path, todos)`, picked by the file suffix: SQLite for `.db`,
`.sqlite`, `.sqlite3`, the JSON file store for anything else.
"""

import json
import os
import sqlite3
from pathlib import Path

STATUSES = ("todo", "in-progress", "done")
SQLITE_SUFFIXES = (".db", ".sqlite", ".sqlite3")
# The repo root (the directory of todo.py), not the current directory
DEFAULT_STORE = Path(__file__).resolve().parent.parent / "data" / "todos.db"
SQLITE_VERSION = 3
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER NOT NULL UNIQUE,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    due TEXT,
    labels TEXT NOT NULL
)
"""


class UnsupportedStoreVersion(Exception):
    pass


class InvalidStoreItem(Exception):
    pass


class InvalidStoreFile(Exception):
    """A SQLite-suffixed store that is not a SQLite database; the message is the path."""


def store_path():
    return os.environ.get("TODO_FILE", str(DEFAULT_STORE))


def is_sqlite(path):
    return Path(path).suffix.lower() in SQLITE_SUFFIXES


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


def load_todos(path):
    if is_sqlite(path):
        return _load_sqlite(path)
    return _load_json(path)


def save_todos(path, todos):
    normalized = [normalize_todo(todo) for todo in todos if isinstance(todo, dict)]
    if is_sqlite(path):
        _save_sqlite(path, normalized)
    else:
        _save_json(path, normalized)


def _check_item(position, item, seen_ids, check_status):
    """Raise InvalidStoreItem for the first problem: id, then title, then status (if check_status)."""
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
    if check_status and "status" in item and item["status"] not in STATUSES:
        raise InvalidStoreItem(f"{position}: invalid status")
    seen_ids.add(item_id)


def _load_json(path):
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
        # v3: status is validated if present, after id and title; v1/v2 items migrate it from `done`
        _check_item(position, item, seen_ids, check_status=not migrate)
        if migrate:
            migrated = dict(item)
            migrated["status"] = "done" if item.get("done") is True else "todo"
            migrated.pop("done", None)
            result.append(normalize_todo(migrated))
        else:
            result.append(normalize_todo(item))
    return result


def _save_json(path, normalized):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 3, "todos": normalized}, f, indent=2)
        f.write("\n")


def _connect(path):
    """Open an existing or new SQLite store; a file that is not SQLite raises InvalidStoreFile."""
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA user_version").fetchone()
    except sqlite3.DatabaseError:
        conn.close()
        raise InvalidStoreFile(str(path)) from None
    return conn


def _sqlite_version(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version not in (0, SQLITE_VERSION):  # 0: a new, empty database
        raise UnsupportedStoreVersion(version)
    return version


def _load_sqlite(path):
    if not Path(path).exists():  # read-only commands must not create the database
        return []
    conn = _connect(path)
    try:
        if _sqlite_version(conn) == 0:
            return []
        rows = conn.execute(
            "SELECT id, title, status, priority, due, labels FROM todos ORDER BY position"
        ).fetchall()
    except sqlite3.DatabaseError:
        raise InvalidStoreFile(str(path)) from None
    finally:
        conn.close()
    result = []
    seen_ids = set()
    for position, row in enumerate(rows, start=1):
        item = dict(zip(("id", "title", "status", "priority", "due", "labels"), row, strict=True))
        # a NULL id or title (a database not written by save_todos) counts as missing
        item = {key: value for key, value in item.items() if value is not None or key == "due"}
        _check_item(position, item, seen_ids, check_status=True)
        try:
            labels = json.loads(item.get("labels"))
        except TypeError, ValueError:
            raise InvalidStoreItem(f"{position}: invalid labels") from None
        if not isinstance(labels, list):
            raise InvalidStoreItem(f"{position}: invalid labels")
        item["labels"] = labels
        result.append(normalize_todo(item))
    return result


def _save_sqlite(path, normalized):
    if not Path(path).parent.is_dir():  # like the JSON store: never create directories
        raise FileNotFoundError(f"No such directory: {Path(path).parent}")
    conn = _connect(path)
    try:
        _sqlite_version(conn)
        with conn:  # one transaction: all rows replaced, or none
            conn.execute(SQLITE_SCHEMA)
            conn.execute(f"PRAGMA user_version = {SQLITE_VERSION}")
            conn.execute("DELETE FROM todos")
            conn.executemany(
                "INSERT INTO todos (id, position, title, status, priority, due, labels)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        t["id"],
                        position,
                        t["title"],
                        t["status"],
                        t["priority"],
                        t["due"],
                        json.dumps(t["labels"]),
                    )
                    for position, t in enumerate(normalized, start=1)
                ],
            )
    except sqlite3.DatabaseError:
        raise InvalidStoreFile(str(path)) from None
    finally:
        conn.close()
