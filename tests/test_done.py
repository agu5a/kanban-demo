import json
import os
import subprocess
import sys
from pathlib import Path


def run_done(tmp_path, monkeypatch, todo_id, extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "todo.py"),
        "done",
        str(todo_id),
    ]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)


def test_done_marks_todo_done(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_done(tmp_path, monkeypatch, 1)
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0].get("status") == "done"


def test_done_unknown_id_returns_error(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    result = run_done(tmp_path, monkeypatch, 999)
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def test_done_does_not_affect_other_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            [
                {"id": 1, "title": "Open one"},
                {"id": 2, "title": "Other"},
            ]
        )
    )
    result = run_done(tmp_path, monkeypatch, 1)
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0].get("status") == "done"
    assert data["todos"][1]["status"] == "todo"


def test_done_missing_file_unknown_id(tmp_path, monkeypatch):
    result = run_done(tmp_path, monkeypatch, 1)
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def test_done_from_in_progress(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps([{"id": 1, "title": "Task", "status": "in-progress"}])
    )
    result = run_done(tmp_path, monkeypatch, 1)
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["status"] == "done"
