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
PRE_CARD_SCHEMA = """
CREATE TABLE todos (
    id INTEGER NOT NULL UNIQUE,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    due TEXT,
    labels TEXT NOT NULL
)
"""


def run_cmd(path, *args):
    env = dict(os.environ)
    env["TODO_FILE"] = str(path)
    return subprocess.run(
        [sys.executable, str(TODO_PY), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def stored(path):
    return json.loads(path.read_text())["todos"]


@pytest.fixture
def store_file(tmp_path):
    path = tmp_path / "todos.json"
    for title in ("Buy milk", "Walk the dog"):
        assert run_cmd(path, "add", title).returncode == 0
    return path


def test_assign_sets_and_trims(store_file):
    result = run_cmd(store_file, "assign", "1", "  Anna ")
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    item = stored(store_file)[0]
    assert item["assignee"] == "Anna"
    assert list(item) == ["id", "title", "status", "priority", "due", "labels", "assignee"]


def test_assign_blank_name_usage_error(store_file):
    before = store_file.read_bytes()
    result = run_cmd(store_file, "assign", "1", "   ")
    assert result.returncode == 2
    assert "assignee must not be empty" in result.stderr
    assert store_file.read_bytes() == before


def test_assign_too_long_usage_error(store_file):
    before = store_file.read_bytes()
    result = run_cmd(store_file, "assign", "1", "x" * 41)
    assert result.returncode == 2
    assert "assignee too long" in result.stderr
    assert store_file.read_bytes() == before
    assert run_cmd(store_file, "assign", "1", "y" * 40).returncode == 0


def test_unassign_removes_the_key(store_file):
    run_cmd(store_file, "assign", "1", "Anna")
    result = run_cmd(store_file, "unassign", "1")
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert list(stored(store_file)[0]) == ["id", "title", "status", "priority", "due", "labels"]


@pytest.mark.parametrize("cmd", [["assign", "9", "Anna"], ["unassign", "9"]])
def test_assign_unknown_id(store_file, cmd):
    before = store_file.read_bytes()
    result = run_cmd(store_file, *cmd)
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 9"
    assert store_file.read_bytes() == before


def test_add_with_assignee(tmp_path):
    path = tmp_path / "todos.json"
    assert run_cmd(path, "add", "Plan trip", "--assignee", " Bence ").returncode == 0
    assert run_cmd(path, "add", "No one").returncode == 0
    first, second = stored(path)
    assert first["assignee"] == "Bence"
    assert "assignee" not in second
    result = run_cmd(path, "add", "X", "--assignee", "")
    assert result.returncode == 2
    assert "assignee must not be empty" in result.stderr


def test_list_shows_assignee_suffix(tmp_path):
    path = tmp_path / "todos.json"
    run_cmd(path, "add", "Buy milk", "--priority", "high", "--label", "home", "--assignee", "Anna")
    result = run_cmd(path, "list")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["1 [ ] Buy milk (high) #home @Anna"]


@pytest.mark.parametrize(
    "value,expected",
    [("anna", ["1 [ ] A @Anna"]), ("ANNA", ["1 [ ] A @Anna"]), ("none", ["3 [ ] C"])],
)
def test_list_filter_by_assignee(tmp_path, value, expected):
    path = tmp_path / "todos.json"
    run_cmd(path, "add", "A", "--assignee", "Anna")
    run_cmd(path, "add", "B", "--assignee", "Annabel")
    run_cmd(path, "add", "C")
    result = run_cmd(path, "list", "--assignee", value)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == expected


@pytest.mark.parametrize("fmt", ["json", "csv", "md"])
def test_export_includes_assignee(tmp_path, fmt):
    path = tmp_path / "todos.json"
    run_cmd(path, "add", "A", "--assignee", "Anna")
    run_cmd(path, "add", "B")
    result = run_cmd(path, "export", "--format", fmt)
    assert result.returncode == 0, result.stderr
    if fmt == "json":
        first, second = json.loads(result.stdout)
        assert first["assignee"] == "Anna"
        assert "assignee" not in second
    elif fmt == "csv":
        assert result.stdout.splitlines() == [
            "id,title,status,priority,due,labels,assignee",
            "1,A,todo,normal,,,Anna",
            "2,B,todo,normal,,,",
        ]
    else:
        assert result.stdout.splitlines() == ["- [ ] A @Anna", "- [ ] B"]


def test_sqlite_assignee_round_trip(tmp_path):
    path = tmp_path / "todos.db"
    todos = [
        {
            "id": 1,
            "title": "A",
            "status": "todo",
            "priority": "normal",
            "due": None,
            "labels": [],
            "assignee": "Anna",
        },
        {"id": 2, "title": "B", "status": "done", "priority": "high", "due": None, "labels": ["x"]},
    ]
    store.save_todos(path, todos)
    assert store.load_todos(path) == todos
    assert run_cmd(path, "unassign", "1").returncode == 0
    assert "assignee" not in store.load_todos(path)[0]


def test_sqlite_database_without_column_reads_and_upgrades(tmp_path):
    path = tmp_path / "todos.db"
    conn = sqlite3.connect(path)
    with conn:
        conn.execute(PRE_CARD_SCHEMA)
        conn.execute(
            "INSERT INTO todos (id, position, title, status, priority, due, labels) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, 1, "Old", "todo", "normal", None, "[]"),
        )
        conn.execute("PRAGMA user_version = 3")
    conn.close()
    before = path.read_bytes()

    assert store.load_todos(path) == [
        {"id": 1, "title": "Old", "status": "todo", "priority": "normal", "due": None, "labels": []}
    ]
    assert run_cmd(path, "list").stdout.splitlines() == ["1 [ ] Old"]
    assert path.read_bytes() == before  # reads do not add the column

    assert run_cmd(path, "assign", "1", "Anna").returncode == 0
    conn = sqlite3.connect(path)
    columns = [row[1] for row in conn.execute("PRAGMA table_info(todos)")]
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()
    assert columns[-1] == "assignee"
    assert version == 3
    assert store.load_todos(path)[0]["assignee"] == "Anna"


def test_demo_db_has_assignees():
    path = REPO / "data" / "todos.db"
    before = path.read_bytes()
    todos = store.load_todos(path)
    assert path.read_bytes() == before
    assert sorted(t["assignee"] for t in todos if "assignee" in t) == ["Anna", "Bence"]
