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


def test_label_add(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    result = run_cmd(tmp_path, "label", "1", "add", "Work")
    assert result.returncode == 0
    assert result.stdout == ""
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["labels"] == ["work"]


def test_label_add_keeps_sorted(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    run_cmd(tmp_path, "label", "1", "add", "zebra")
    run_cmd(tmp_path, "label", "1", "add", "apple")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["labels"] == ["apple", "zebra"]


def test_label_add_lowercases(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    run_cmd(tmp_path, "label", "1", "add", "MiXeD-1")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["labels"] == ["mixed-1"]
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "label", "1", "add", "MIXED-1")
    assert result.returncode == 0
    assert (tmp_path / "todos.json").read_text() == original


def test_label_add_existing_leaves_file_unchanged(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    run_cmd(tmp_path, "label", "1", "add", "work")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "label", "1", "add", "work")
    assert result.returncode == 0
    assert result.stdout == ""
    assert (tmp_path / "todos.json").read_text() == original


def test_label_rm(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    run_cmd(tmp_path, "label", "1", "add", "work")
    result = run_cmd(tmp_path, "label", "1", "rm", "work")
    assert result.returncode == 0
    assert result.stdout == ""
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["labels"] == []


def test_label_rm_missing_leaves_file_unchanged(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "label", "1", "rm", "nope")
    assert result.returncode == 0
    assert result.stdout == ""
    assert (tmp_path / "todos.json").read_text() == original


def test_label_does_not_affect_other_todos(tmp_path):
    run_cmd(tmp_path, "add", "First")
    run_cmd(tmp_path, "add", "Second")
    before = json.loads((tmp_path / "todos.json").read_text())
    run_cmd(tmp_path, "label", "1", "add", "work")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["labels"] == ["work"]
    assert data["todos"][1] == before["todos"][1]


def test_label_migrates_v1_store(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_cmd(tmp_path, "label", "1", "add", "work")
    assert result.returncode == 0
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 2,
        "todos": [
            {
                "id": 1,
                "title": "Buy milk",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": ["work"],
            }
        ],
    }


def test_label_unknown_id_exits_1(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "label", "99", "add", "x")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 99"
    assert (tmp_path / "todos.json").read_text() == original


def test_label_unknown_id_missing_file(tmp_path):
    result = run_cmd(tmp_path, "label", "99", "add", "x")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 99"
    assert not (tmp_path / "todos.json").exists()


def test_label_name_with_space_exits_2(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "label", "1", "add", "a b")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_label_empty_name_exits_2(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "label", "1", "add", "")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_label_21_chars_exits_2(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "label", "1", "add", "a" * 21)
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_label_20_chars_ok(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    name = "a" * 20
    result = run_cmd(tmp_path, "label", "1", "add", name)
    assert result.returncode == 0
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["labels"] == [name]


def test_label_unknown_action_exits_2(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "label", "1", "rename", "x")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_label_unsupported_version_exits_1(tmp_path):
    content = json.dumps({"version": 3, "todos": [{"id": 1, "title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "label", "1", "add", "x")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 3"
    assert (tmp_path / "todos.json").read_text() == content
