import json
import os
import subprocess
import sys
from pathlib import Path


def run_rm(tmp_path, monkeypatch, todo_id, extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "todo.py"),
        "rm",
        str(todo_id),
    ]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)


def test_rm_removes_todo(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_rm(tmp_path, monkeypatch, 1)
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {"version": 2, "todos": []}


def test_rm_removes_correct_todo(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            [
                {"id": 1, "title": "First"},
                {"id": 2, "title": "Second"},
            ]
        )
    )
    result = run_rm(tmp_path, monkeypatch, 1)
    assert result.returncode == 0, result.stderr
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 2,
        "todos": [
            {
                "id": 2,
                "title": "Second",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    }


def test_rm_unknown_id_exits_1(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    result = run_rm(tmp_path, monkeypatch, 999)
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def test_rm_unknown_id_missing_file(tmp_path, monkeypatch):
    result = run_rm(tmp_path, monkeypatch, 999)
    assert result.returncode == 1
    assert result.stderr.strip() != ""
