import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from todolib import store

REPO = Path(__file__).resolve().parent.parent
TODO_PY = REPO / "todo.py"
COLUMNS = ["id", "position", "title", "status", "priority", "due", "labels"]


def run_cmd(path, *args, cwd=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(path)
    return subprocess.run(
        [sys.executable, str(TODO_PY), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
        check=False,
    )


def make_db(path, rows, version=3):
    conn = sqlite3.connect(path)
    with conn:
        conn.execute(store.SQLITE_SCHEMA)
        conn.executemany(
            "INSERT INTO todos (id, position, title, status, priority, due, labels) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.execute(f"PRAGMA user_version = {version}")
    conn.close()


def item(todo_id, title, status="todo", priority="normal", due=None, labels=None):
    return {
        "id": todo_id,
        "title": title,
        "status": status,
        "priority": priority,
        "due": due,
        "labels": labels or [],
    }


def test_default_store_path_is_repo_data_db(tmp_path, monkeypatch):
    monkeypatch.delenv("TODO_FILE")
    monkeypatch.chdir(tmp_path)
    assert store.store_path() == str(REPO / "data" / "todos.db")
    monkeypatch.setenv("TODO_FILE", "x.json")
    assert store.store_path() == "x.json"


@pytest.mark.parametrize(
    ("name", "sqlite"),
    [
        ("todos.db", True),
        ("todos.sqlite", True),
        ("todos.sqlite3", True),
        ("todos.DB", True),
        ("todos.json", False),
        ("todos", False),
    ],
)
def test_backend_chosen_by_suffix(tmp_path, name, sqlite):
    path = tmp_path / name
    store.save_todos(path, [item(1, "A")])
    head = path.read_bytes()[:16]
    if sqlite:
        assert head == b"SQLite format 3\x00"
    else:
        assert json.loads(path.read_text()) == {"version": 3, "todos": [item(1, "A")]}
    assert store.load_todos(path) == [item(1, "A")]


def test_sqlite_round_trip_keeps_order_and_fields(tmp_path):
    path = tmp_path / "todos.db"
    todos = [
        item(3, "Third", "done", "high", "2026-01-02", ["x", "y"]),
        item(1, "First"),
        item(2, "Second", "in-progress", "low", None, ["a"]),
    ]
    store.save_todos(path, todos)
    loaded = store.load_todos(path)
    assert loaded == todos
    assert [list(t) for t in loaded] == [list(store.normalize_todo({}))] * 3
    store.save_todos(path, loaded[1:])  # a second save replaces every row
    assert store.load_todos(path) == todos[1:]


def test_sqlite_schema_and_user_version(tmp_path):
    path = tmp_path / "todos.db"
    store.save_todos(path, [item(1, "A")])
    conn = sqlite3.connect(path)
    columns = [(row[1], row[2], row[3]) for row in conn.execute("PRAGMA table_info(todos)")]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()
    assert columns == [
        ("id", "INTEGER", 1),
        ("position", "INTEGER", 1),
        ("title", "TEXT", 1),
        ("status", "TEXT", 1),
        ("priority", "TEXT", 1),
        ("due", "TEXT", 0),
        ("labels", "TEXT", 1),
    ]
    assert version == 3


@pytest.mark.parametrize("cmd", [["list"], ["stats"], ["export"]])
def test_sqlite_missing_file_reads_empty_and_is_not_created(tmp_path, cmd):
    path = tmp_path / "todos.db"
    result = run_cmd(path, *cmd)
    assert result.returncode == 0, result.stderr
    assert not path.exists()


def test_sqlite_new_empty_database_reads_empty(tmp_path):
    path = tmp_path / "todos.db"
    sqlite3.connect(path).close()  # an empty file: user_version 0
    assert store.load_todos(path) == []
    assert run_cmd(path, "add", "A").returncode == 0
    assert store.load_todos(path) == [item(1, "A")]


@pytest.mark.parametrize("cmd", [["list"], ["add", "x"]])
def test_sqlite_unsupported_version_fails(tmp_path, cmd):
    path = tmp_path / "todos.db"
    make_db(path, [(1, 1, "A", "todo", "normal", None, "[]")], version=4)
    result = run_cmd(path, *cmd)
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 4"
    conn = sqlite3.connect(path)  # the database is left as it was
    assert conn.execute("SELECT count(*) FROM todos").fetchone()[0] == 1
    conn.close()


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([(1, 1, "A", "blocked", "normal", None, "[]")], "Invalid store item 1: invalid status"),
        (
            [(1, 1, "A", "todo", "normal", None, "[]"), (0, 2, "B", "todo", "normal", None, "[]")],
            "Invalid store item 2: invalid id",
        ),
        ([(1, 1, "", "todo", "normal", None, "[]")], "Invalid store item 1: invalid title"),
        ([(1, 1, "A", "todo", "normal", None, "nope")], "Invalid store item 1: invalid labels"),
    ],
)
def test_sqlite_invalid_row_fails(tmp_path, rows, message):
    path = tmp_path / "todos.db"
    make_db(path, rows)
    result = run_cmd(path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == message


def test_sqlite_not_a_database_fails_cleanly(tmp_path):
    path = tmp_path / "todos.db"
    path.write_text("not a database\n" * 10)
    for cmd in (["list"], ["add", "x"]):
        result = run_cmd(path, *cmd)
        assert result.returncode == 1
        assert result.stderr.strip() == f"Invalid store file: {path}"
        assert "Traceback" not in result.stderr
    assert path.read_text() == "not a database\n" * 10


def test_sqlite_save_does_not_create_directories(tmp_path):
    path = tmp_path / "missing" / "todos.db"
    with pytest.raises(FileNotFoundError):
        store.save_todos(path, [item(1, "A")])
    assert not path.parent.exists()


def test_commands_same_on_json_and_sqlite(tmp_path):
    steps = [
        ["add", "Write docs"],
        ["add", "Fix bug", "--priority", "high"],
        ["add", "Ship it"],
        ["move", "2", "in-progress"],
        ["priority", "3", "low"],
        ["due", "1", "2026-03-01"],
        ["label", "1", "add", "docs"],
        ["done", "3"],
        ["edit", "1", "Write the docs"],
        ["add", "Temp"],
        ["rm", "4"],
    ]
    outputs = {}
    for name in ("todos.json", "todos.db"):
        path = tmp_path / name
        for step in steps:
            result = run_cmd(path, *step)
            assert result.returncode == 0, (name, step, result.stderr)
        outputs[name] = [
            run_cmd(path, *cmd).stdout
            for cmd in (["list"], ["export", "--format", "json"], ["stats"])
        ]
    assert outputs["todos.json"] == outputs["todos.db"]
    assert "Write the docs" in outputs["todos.db"][0]


def test_demo_db_has_items_in_every_status():
    path = REPO / "data" / "todos.db"
    before = path.read_bytes()
    todos = store.load_todos(path)
    assert path.read_bytes() == before
    assert len(todos) == 6
    assert {t["status"] for t in todos} == {"todo", "in-progress", "done"}
    assert any(t["priority"] == "high" for t in todos)
    assert any(t["due"] for t in todos)
    assert any(t["labels"] for t in todos)


def test_tests_use_an_isolated_store():
    path = Path(os.environ["TODO_FILE"]).resolve()
    assert not path.is_relative_to(REPO / "data")
