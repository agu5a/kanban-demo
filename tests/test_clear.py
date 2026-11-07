import json
import os
import subprocess
import sys
from pathlib import Path


def run_clear(tmp_path, monkeypatch, extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent.parent / "todo.py"),
        "clear",
    ]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)


def test_clear_removes_done_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps([{"id": 1, "title": "A", "done": True}, {"id": 2, "title": "B"}])
    )
    result = run_clear(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "1\n"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 3,
        "todos": [
            {
                "id": 2,
                "title": "B",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    }


def test_clear_keeps_open_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            [
                {"id": 1, "title": "A", "done": True},
                {"id": 2, "title": "B"},
                {"id": 3, "title": "C", "status": "todo"},
            ]
        )
    )
    result = run_clear(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "1\n"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 3,
        "todos": [
            {
                "id": 2,
                "title": "B",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 3,
                "title": "C",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    }


def test_clear_removes_multiple_done(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            [
                {"id": 1, "title": "A", "done": True},
                {"id": 2, "title": "B", "done": True},
                {"id": 3, "title": "C"},
            ]
        )
    )
    result = run_clear(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "2\n"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 3,
        "todos": [
            {
                "id": 3,
                "title": "C",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    }


def test_clear_empty_store(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("[]")
    result = run_clear(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "0\n"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == []


def test_clear_no_done(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps([{"id": 1, "title": "A"}, {"id": 2, "title": "B", "status": "todo"}])
    )
    original = (tmp_path / "todos.json").read_text()
    result = run_clear(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "0\n"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == [{"id": 1, "title": "A"}, {"id": 2, "title": "B", "status": "todo"}]
    assert (tmp_path / "todos.json").read_text() == original


def test_clear_missing_file_errors(tmp_path, monkeypatch):
    path = tmp_path / "todos.json"
    result = run_clear(tmp_path, monkeypatch)
    assert result.returncode == 1
    assert result.stderr.strip() == f"No todos file: {path}"
    assert not path.exists()


def test_clear_counts_removed(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "A", "done": True}]))
    result = run_clear(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "1\n"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {"version": 3, "todos": []}


def test_clear_extra_args_usage_error(tmp_path, monkeypatch):
    original = json.dumps([{"id": 1, "title": "A", "done": True}])
    (tmp_path / "todos.json").write_text(original)
    result = run_clear(tmp_path, monkeypatch, extra=["foo"])
    assert result.returncode == 2
    assert "usage:" in result.stderr
    assert (tmp_path / "todos.json").read_text() == original


def test_clear_keeps_in_progress(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            {
                "version": 3,
                "todos": [
                    {"id": 1, "title": "A", "status": "in-progress"},
                    {"id": 2, "title": "B", "status": "done"},
                ],
            }
        )
    )
    result = run_clear(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "1\n"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert [t["id"] for t in data["todos"]] == [1]
