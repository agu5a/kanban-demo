import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import todo


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


FIELDS = ["id", "title", "done", "priority", "due", "labels"]

ALL_COMMANDS = [
    ["add", "todo"],
    ["list"],
    ["done", "1"],
    ["undone", "1"],
    ["edit", "1", "x"],
    ["rm", "1"],
    ["clear"],
]


def test_add_on_missing_file_writes_v2(tmp_path):
    result = run_cmd(tmp_path, "add", "Pay rent")
    assert result.returncode == 0
    assert result.stdout.strip() == "1"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 2,
        "todos": [
            {
                "id": 1,
                "title": "Pay rent",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    }


def test_v1_store_read_with_defaults(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    todos = todo.load_todos(str(tmp_path / "todos.json"))
    assert todos == [
        {
            "id": 1,
            "title": "Buy milk",
            "done": False,
            "priority": "normal",
            "due": None,
            "labels": [],
        }
    ]


def test_first_save_migrates_v1_to_v2(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_cmd(tmp_path, "done", "1")
    assert result.returncode == 0
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 2,
        "todos": [
            {
                "id": 1,
                "title": "Buy milk",
                "done": True,
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    }


def test_save_writes_all_six_fields_in_order(tmp_path):
    path = tmp_path / "todos.json"
    todo.save_todos(str(path), [{"id": 1, "title": "x"}])
    data = json.loads(path.read_text())
    assert data == {
        "version": 2,
        "todos": [
            {"id": 1, "title": "x", "done": False, "priority": "normal", "due": None, "labels": []}
        ],
    }
    assert list(data["todos"][0].keys()) == FIELDS


def test_list_does_not_migrate_v1(tmp_path):
    content = json.dumps([{"id": 1, "title": "Buy milk"}])
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 0
    assert result.stdout == "1 [ ] Buy milk\n"
    assert (tmp_path / "todos.json").read_text() == content


def test_clear_nothing_to_remove_does_not_migrate_v1(tmp_path):
    content = json.dumps([{"id": 1, "title": "Buy milk"}])
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "clear")
    assert result.returncode == 0
    assert result.stdout.strip() == "0"
    assert (tmp_path / "todos.json").read_text() == content


@pytest.mark.parametrize("cmd_args", ALL_COMMANDS)
def test_unsupported_version_fails_every_command(tmp_path, cmd_args):
    content = json.dumps({"version": 3})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, *cmd_args)
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 3"
    assert (tmp_path / "todos.json").read_text() == content


@pytest.mark.parametrize("cmd_args", ALL_COMMANDS)
def test_object_without_version_is_unsupported(tmp_path, cmd_args):
    content = json.dumps({})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, *cmd_args)
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: None"
    assert (tmp_path / "todos.json").read_text() == content


def test_version_2_without_todos_is_empty(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps({"version": 2}))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 0
    assert result.stdout.strip() == "No todos"


def test_scalar_store_reads_as_empty(tmp_path):
    (tmp_path / "todos.json").write_text("42")
    assert todo.load_todos(str(tmp_path / "todos.json")) == []


def test_loader_drops_non_dict_items(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([42, "x", None, {"id": 1, "title": "y"}]))
    todos = todo.load_todos(str(tmp_path / "todos.json"))
    assert todos == [
        {"id": 1, "title": "y", "done": False, "priority": "normal", "due": None, "labels": []}
    ]


def test_normalize_todo_fills_missing_fields():
    item = todo.normalize_todo({"id": 1, "title": "x"})
    assert item == {
        "id": 1,
        "title": "x",
        "done": False,
        "priority": "normal",
        "due": None,
        "labels": [],
    }
    assert list(item.keys()) == FIELDS


def test_normalize_todo_keeps_invalid_values():
    item = todo.normalize_todo({"id": 1, "title": "x", "priority": "urgent", "done": "yes"})
    assert item["priority"] == "urgent"
    assert item["done"] == "yes"


def test_normalize_todo_drops_unknown_keys():
    item = todo.normalize_todo({"id": 1, "title": "x", "foo": "bar"})
    assert "foo" not in item
    assert set(item.keys()) == set(FIELDS)
