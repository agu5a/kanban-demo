"""Storage layer: store path, load/save with validation and migration."""

import json
import os


class UnsupportedStoreVersion(Exception):
    pass


class InvalidStoreItem(Exception):
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
        seen_ids.add(item_id)
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
