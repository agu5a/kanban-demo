import json
import os
import subprocess
import sys
from pathlib import Path


def run_undone(tmp_path, monkeypatch, todo_id, extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "todo.py"),
        "undone",
        str(todo_id),
    ]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)


def test_undone_marks_todo_open(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk", "done": True}]))
    result = run_undone(tmp_path, monkeypatch, 1)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0].get("done") is False


def test_undone_unknown_id_returns_error(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    result = run_undone(tmp_path, monkeypatch, 999)
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 999"


def test_undone_does_not_affect_other_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            [
                {"id": 1, "title": "Done one", "done": True},
                {"id": 2, "title": "Other"},
            ]
        )
    )
    result = run_undone(tmp_path, monkeypatch, 1)
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0].get("done") is False
    assert data["todos"][1]["done"] is False


def test_undone_missing_file_unknown_id(tmp_path, monkeypatch):
    result = run_undone(tmp_path, monkeypatch, 1)
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 1"
    assert not (tmp_path / "todos.json").exists()


def test_undone_idempotent(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_undone(tmp_path, monkeypatch, 1)
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0].get("done") is False


def test_undone_invalid_id_argparse_error(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    result = run_undone(tmp_path, monkeypatch, "abc")
    assert result.returncode != 0
    assert result.stderr.strip() != ""
