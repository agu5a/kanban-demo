import json
import os
import subprocess
import sys
from pathlib import Path

import todolib.cli
import todolib.store


def run_add(tmp_path, monkeypatch, title, extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    cmd = [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), "add", title]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)


def test_add_prints_id(tmp_path, monkeypatch):
    result = run_add(tmp_path, monkeypatch, "Buy milk")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"


def test_add_stores_todo(tmp_path, monkeypatch):
    run_add(tmp_path, monkeypatch, "Buy milk")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 3,
        "todos": [
            {
                "id": 1,
                "title": "Buy milk",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    }


def test_add_increments_id(tmp_path, monkeypatch):
    run_add(tmp_path, monkeypatch, "First")
    run_add(tmp_path, monkeypatch, "Second")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert [t["id"] for t in data["todos"]] == [1, 2]


def test_add_respects_env_path(tmp_path, monkeypatch):
    custom = tmp_path / "custom.json"
    monkeypatch.setenv("TODO_FILE", str(custom))
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), "add", "X"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert custom.exists()


def test_add_without_todo_file_uses_repo_default_not_cwd(tmp_path, monkeypatch):
    # #65: the default store moved from ./todos.json to <repo>/data/todos.db; the repo's demo database must stay
    # untouched, so the default is pointed at a stand-in repo here and the command runs in-process
    default = tmp_path / "repo" / "data" / "todos.db"
    default.parent.mkdir(parents=True)
    monkeypatch.setattr(todolib.store, "DEFAULT_STORE", default)
    monkeypatch.delenv("TODO_FILE")
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    assert todolib.cli.main(["add", "Y"]) == 0
    assert [t["title"] for t in todolib.store.load_todos(default)] == ["Y"]
    assert list(cwd.iterdir()) == []


def test_add_empty_title_usage_error(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    original = (tmp_path / "todos.json").read_text()
    result = run_add(tmp_path, monkeypatch, "")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_add_priority_flag(tmp_path, monkeypatch):
    levels = ["high", "low", "normal"]
    for expected_id, level in enumerate(levels, start=1):
        result = run_add(tmp_path, monkeypatch, "X", ["--priority", level])
        assert result.returncode == 0
        assert result.stdout == f"{expected_id}\n"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert [todo["priority"] for todo in data["todos"]] == levels


def test_add_priority_default_normal(tmp_path, monkeypatch):
    run_add(tmp_path, monkeypatch, "X")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["priority"] == "normal"


def test_add_priority_invalid_exits_2(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    original = (tmp_path / "todos.json").read_text()
    result = run_add(tmp_path, monkeypatch, "X", ["--priority", "urgent"])
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_add_due_flag(tmp_path, monkeypatch):
    result = run_add(tmp_path, monkeypatch, "X", ["--due", "2026-12-01"])
    assert result.returncode == 0
    assert result.stdout.strip() == "1"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["due"] == "2026-12-01"


def test_add_due_default_null(tmp_path, monkeypatch):
    run_add(tmp_path, monkeypatch, "X")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["due"] is None


def test_add_due_invalid_exits_2(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    original = (tmp_path / "todos.json").read_text()
    for value in ["2026-02-30", "20261201", "2026-W49-2"]:
        result = run_add(tmp_path, monkeypatch, "X", ["--due", value])
        assert result.returncode == 2
        assert result.stderr.strip() != ""
        assert (tmp_path / "todos.json").read_text() == original


def test_add_due_none_exits_2(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    original = (tmp_path / "todos.json").read_text()
    result = run_add(tmp_path, monkeypatch, "X", ["--due", "none"])
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_add_label_flag_repeatable_sorted_unique(tmp_path, monkeypatch):
    result = run_add(
        tmp_path, monkeypatch, "X", ["--label", "Home", "--label", "money", "--label", "home"]
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "1"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["labels"] == ["home", "money"]


def test_add_label_default_empty(tmp_path, monkeypatch):
    run_add(tmp_path, monkeypatch, "X")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["labels"] == []


def test_add_label_invalid_exits_2(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    original = (tmp_path / "todos.json").read_text()
    result = run_add(tmp_path, monkeypatch, "X", ["--label", "a b"])
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original
