import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import todo


def run_move(tmp_path, monkeypatch, todo_id, status, extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "todo.py"),
        "move",
        str(todo_id),
        str(status),
    ]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)


def env_for(tmp_path):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    return env


def run_cmd(tmp_path, *args):
    env = env_for(tmp_path)
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


@pytest.mark.parametrize("status", ["todo", "in-progress", "done"])
def test_move_sets_status(tmp_path, monkeypatch, status):
    start = "todo" if status != "todo" else "done"
    (tmp_path / "todos.json").write_text(
        json.dumps({"version": 3, "todos": [{"id": 3, "title": "Task", "status": start}]})
    )
    result = run_move(tmp_path, monkeypatch, 3, status)
    assert result.returncode == 0, result.stderr
    todos = todo.load_todos(str(tmp_path / "todos.json"))
    assert todos[0]["status"] == status


def test_move_no_stdout(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Task"}]))
    result = run_move(tmp_path, monkeypatch, 1, "done")
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_move_does_not_affect_other_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            [
                {"id": 1, "title": "One"},
                {"id": 2, "title": "Two"},
            ]
        )
    )
    result = run_move(tmp_path, monkeypatch, 1, "in-progress")
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["status"] == "in-progress"
    assert data["todos"][1]["status"] == "todo"


def test_move_migrates_v2_store(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps({"version": 2, "todos": [{"id": 1, "title": "Task", "done": True}]})
    )
    result = run_move(tmp_path, monkeypatch, 1, "todo")
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["version"] == 3
    assert data["todos"][0]["status"] == "todo"
    assert "done" not in data["todos"][0]


def test_move_same_status_does_not_write(tmp_path, monkeypatch):
    content = json.dumps({"version": 2, "todos": [{"id": 1, "title": "Task"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_move(tmp_path, monkeypatch, 1, "todo")
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert (tmp_path / "todos.json").read_text() == content


def test_move_unknown_id_exits_1(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Task"}]))
    result = run_move(tmp_path, monkeypatch, 999, "done")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 999"


def test_move_missing_store_unknown_id(tmp_path, monkeypatch):
    result = run_move(tmp_path, monkeypatch, 1, "done")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 1"
    assert not (tmp_path / "todos.json").exists()


def test_move_invalid_status_exits_2(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Task"}]))
    original = (tmp_path / "todos.json").read_text()
    result = run_move(tmp_path, monkeypatch, 1, "doing")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_move_non_int_id_exits_2(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Task"}]))
    original = (tmp_path / "todos.json").read_text()
    result = run_move(tmp_path, monkeypatch, "abc", "done")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_move_unsupported_version_exits_1(tmp_path, monkeypatch):
    content = json.dumps({"version": 4, "todos": [{"id": 1, "title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_move(tmp_path, monkeypatch, 1, "done")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 4"
    assert (tmp_path / "todos.json").read_text() == content


def test_move_invalid_item_exits_1(tmp_path, monkeypatch):
    content = json.dumps({"version": 3, "todos": [{"title": "no id"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_move(tmp_path, monkeypatch, 1, "done")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: missing id"
    assert (tmp_path / "todos.json").read_text() == content


def test_move_todo_returns_changed_flag():
    todos = [{"id": 1, "title": "Task", "status": "todo"}]
    assert todo.move_todo(todos, 1, "done") is True
    assert todos[0]["status"] == "done"
    assert todo.move_todo(todos, 1, "done") is False


def test_move_todo_unknown_id_raises():
    todos = [{"id": 1, "title": "Task", "status": "todo"}]
    with pytest.raises(todo.UnknownTodoId):
        todo.move_todo(todos, 999, "done")
