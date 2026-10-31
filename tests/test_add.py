import json
import os
import subprocess
import sys
from pathlib import Path


def run_add(tmp_path, monkeypatch, title, extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    monkeypatch.setenv("TODO_FILE", env["TODO_FILE"])
    cmd = [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), "add", title]
    if extra:
        cmd.extend(extra)
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def test_add_prints_id(tmp_path, monkeypatch):
    result = run_add(tmp_path, monkeypatch, "Buy milk")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1"


def test_add_stores_todo(tmp_path, monkeypatch):
    run_add(tmp_path, monkeypatch, "Buy milk")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == [{"id": 1, "title": "Buy milk"}]


def test_add_increments_id(tmp_path, monkeypatch):
    run_add(tmp_path, monkeypatch, "First")
    run_add(tmp_path, monkeypatch, "Second")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert [t["id"] for t in data] == [1, 2]


def test_add_respects_env_path(tmp_path, monkeypatch):
    custom = tmp_path / "custom.json"
    monkeypatch.setenv("TODO_FILE", str(custom))
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), "add", "X"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert custom.exists()


def test_add_uses_cwd_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TODO_FILE", raising=False)
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), "add", "Y"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "todos.json").exists()
