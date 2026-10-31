import json
import os
import subprocess
import sys
from pathlib import Path


def run_list(tmp_path, monkeypatch):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), "list"],
        capture_output=True,
        text=True,
        env=env,
    )


def test_list_empty_prints_no_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "No todos"


def test_list_empty_missing_file_prints_no_todos(tmp_path, monkeypatch):
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "No todos"


def test_list_open_todo(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps([{"id": 1, "title": "Buy milk"}])
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1 [ ] Buy milk"


def test_list_done_todo(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps([{"id": 2, "title": "Done thing", "done": True}])
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "2 [x] Done thing"


def test_list_mixed_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            [
                {"id": 1, "title": "Open one"},
                {"id": 2, "title": "Closed one", "done": True},
            ]
        )
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == [
        "1 [ ] Open one",
        "2 [x] Closed one",
    ]
