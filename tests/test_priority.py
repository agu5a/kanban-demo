import json
import os
import subprocess
import sys
from pathlib import Path


def run_cmd(tmp_path, *args):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_priority_sets_level(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    result = run_cmd(tmp_path, "priority", "1", "low")
    assert result.returncode == 0
    assert result.stdout == ""
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["priority"] == "low"


def test_priority_does_not_affect_other_todos(tmp_path):
    run_cmd(tmp_path, "add", "First")
    run_cmd(tmp_path, "add", "Second")
    before = json.loads((tmp_path / "todos.json").read_text())
    run_cmd(tmp_path, "priority", "1", "high")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0] == {**before["todos"][0], "priority": "high"}
    assert data["todos"][1] == before["todos"][1]


def test_priority_migrates_v1_store(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_cmd(tmp_path, "priority", "1", "high")
    assert result.returncode == 0
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 2,
        "todos": [
            {
                "id": 1,
                "title": "Buy milk",
                "done": False,
                "priority": "high",
                "due": None,
                "labels": [],
            }
        ],
    }


def test_priority_unknown_id_exits_1(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "priority", "99", "high")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 99"
    assert (tmp_path / "todos.json").read_text() == original


def test_priority_unknown_id_missing_file(tmp_path):
    result = run_cmd(tmp_path, "priority", "99", "high")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 99"
    assert not (tmp_path / "todos.json").exists()


def test_priority_invalid_level_exits_2(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "priority", "1", "urgent")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_priority_invalid_id_exits_2(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "priority", "abc", "high")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_priority_unsupported_version_exits_1(tmp_path):
    content = json.dumps({"version": 3, "todos": [{"id": 1, "title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "priority", "1", "low")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 3"
    assert (tmp_path / "todos.json").read_text() == content
