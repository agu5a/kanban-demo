import json
import os
import subprocess
import sys
from pathlib import Path


def run_edit(tmp_path, monkeypatch, todo_id, title, extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "todo.py"),
        "edit",
        str(todo_id),
        title,
    ]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)


def test_edit_changes_title(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_edit(tmp_path, monkeypatch, 1, "Buy bread")
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 3,
        "todos": [
            {
                "id": 1,
                "title": "Buy bread",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    }


def test_edit_unknown_id_returns_error(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    result = run_edit(tmp_path, monkeypatch, 999, "New title")
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def test_edit_does_not_affect_other_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            [
                {"id": 1, "title": "First"},
                {"id": 2, "title": "Second"},
            ]
        )
    )
    result = run_edit(tmp_path, monkeypatch, 1, "Changed")
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["title"] == "Changed"
    assert data["todos"][1]["title"] == "Second"


def test_edit_preserves_done_flag(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk", "done": True}]))
    result = run_edit(tmp_path, monkeypatch, 1, "Buy bread")
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0] == {
        "id": 1,
        "title": "Buy bread",
        "status": "done",
        "priority": "normal",
        "due": None,
        "labels": [],
    }


def test_edit_unknown_id_missing_file(tmp_path, monkeypatch):
    result = run_edit(tmp_path, monkeypatch, 999, "New title")
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def test_edit_empty_title_usage_error(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    original = (tmp_path / "todos.json").read_text()
    result = run_edit(tmp_path, monkeypatch, 1, "")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original
