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


FIELDS = ["id", "title", "status", "priority", "due", "labels"]

ALL_COMMANDS = [
    ["add", "todo"],
    ["list"],
    ["done", "1"],
    ["undone", "1"],
    ["edit", "1", "x"],
    ["rm", "1"],
    ["clear"],
]

EVERY_COMMAND = [
    *ALL_COMMANDS,
    ["priority", "1", "high"],
    ["due", "1", "2026-01-01"],
    ["label", "1", "add", "x"],
    ["export"],
]


def test_add_on_missing_file_writes_v2(tmp_path):
    result = run_cmd(tmp_path, "add", "Pay rent")
    assert result.returncode == 0
    assert result.stdout.strip() == "1"
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 3,
        "todos": [
            {
                "id": 1,
                "title": "Pay rent",
                "status": "todo",
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
            "status": "todo",
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
        "version": 3,
        "todos": [
            {
                "id": 1,
                "title": "Buy milk",
                "status": "done",
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
        "version": 3,
        "todos": [
            {
                "id": 1,
                "title": "x",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
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
    content = json.dumps({"version": 4})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, *cmd_args)
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 4"
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
        {"id": 1, "title": "y", "status": "todo", "priority": "normal", "due": None, "labels": []}
    ]


def test_normalize_todo_fills_missing_fields():
    item = todo.normalize_todo({"id": 1, "title": "x"})
    assert item == {
        "id": 1,
        "title": "x",
        "status": "todo",
        "priority": "normal",
        "due": None,
        "labels": [],
    }
    assert list(item.keys()) == FIELDS


def test_normalize_todo_keeps_invalid_values():
    item = todo.normalize_todo({"id": 1, "title": "x", "priority": "urgent", "status": "yes"})
    assert item["priority"] == "urgent"
    assert item["status"] == "yes"


def test_normalize_todo_drops_unknown_keys():
    item = todo.normalize_todo({"id": 1, "title": "x", "foo": "bar"})
    assert "foo" not in item
    assert set(item.keys()) == set(FIELDS)


def test_item_missing_id_fails(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"title": "x"}]))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: missing id"
    assert result.stdout == ""


@pytest.mark.parametrize("value", ["1", True, None, 1.0, 0, -1], ids=str)
def test_item_invalid_id_fails(tmp_path, value):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": value, "title": "x"}]))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: invalid id"
    assert result.stdout == ""


def test_item_duplicate_id_reports_later_item(tmp_path):
    content = json.dumps(
        {"version": 3, "todos": [{"id": 1, "title": "a"}, {"id": 1, "title": "b"}]}
    )
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 2: duplicate id"
    assert result.stdout == ""
    assert (tmp_path / "todos.json").read_text() == content


def test_item_missing_title_fails(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1}]))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: missing title"
    assert result.stdout == ""


@pytest.mark.parametrize("value", ["", None, 5])
def test_item_invalid_title_fails(tmp_path, value):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": value}]))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: invalid title"
    assert result.stdout == ""


def test_item_id_checked_before_title(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"title": ""}]))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: missing id"
    assert result.stdout == ""
    (tmp_path / "todos.json").write_text(json.dumps([{"id": None, "title": ""}]))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: invalid id"
    assert result.stdout == ""


def test_item_position_counts_non_dict_items(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([42, {"title": "x"}]))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 2: missing id"
    assert result.stdout == ""


def test_first_invalid_item_is_reported(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"title": "x"}, {"id": 2, "title": ""}]))
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: missing id"
    assert result.stdout == ""


@pytest.mark.parametrize("cmd_args", EVERY_COMMAND)
def test_invalid_item_fails_every_command(tmp_path, cmd_args):
    content = json.dumps({"version": 3, "todos": [{"title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, *cmd_args)
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: missing id"
    assert result.stdout == ""
    assert (tmp_path / "todos.json").read_text() == content


def test_v1_store_items_validated(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"title": "x"}]))
    with pytest.raises(todo.InvalidStoreItem):
        todo.load_todos(str(tmp_path / "todos.json"))
    # valid v1 loads
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    assert todo.load_todos(str(tmp_path / "todos.json"))[0]["title"] == "Buy milk"


def test_invalid_other_fields_still_load(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps({"version": 3, "todos": [{"id": 1, "title": "x", "priority": "x"}]})
    )
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 0
    assert result.stdout.strip() == "1 [ ] x"
    todos = todo.load_todos(str(tmp_path / "todos.json"))
    assert todos == [
        {"id": 1, "title": "x", "status": "todo", "priority": "x", "due": None, "labels": []}
    ]


def test_unsupported_version_checked_before_items(tmp_path):
    content = json.dumps({"version": 4, "todos": [{"title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 4"
    assert result.stdout == ""
    assert (tmp_path / "todos.json").read_text() == content


def test_v2_done_true_migrates_to_status_done(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps({"version": 2, "todos": [{"id": 1, "title": "Buy milk", "done": True}]})
    )
    todos = todo.load_todos(str(tmp_path / "todos.json"))
    assert todos == [
        {
            "id": 1,
            "title": "Buy milk",
            "status": "done",
            "priority": "normal",
            "due": None,
            "labels": [],
        }
    ]


def test_v2_done_false_or_missing_reads_as_todo(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            {
                "version": 2,
                "todos": [{"id": 1, "title": "a", "done": False}, {"id": 2, "title": "b"}],
            }
        )
    )
    todos = todo.load_todos(str(tmp_path / "todos.json"))
    assert [t["status"] for t in todos] == ["todo", "todo"]


def test_v2_done_truthy_non_true_reads_as_todo(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            {
                "version": 2,
                "todos": [
                    {"id": 1, "title": "a", "done": "yes"},
                    {"id": 2, "title": "b", "done": 1},
                ],
            }
        )
    )
    todos = todo.load_todos(str(tmp_path / "todos.json"))
    assert [t["status"] for t in todos] == ["todo", "todo"]


def test_first_write_migrates_v2_to_v3(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps({"version": 2, "todos": [{"id": 1, "title": "Buy milk", "done": True}]})
    )
    result = run_cmd(tmp_path, "done", "1")
    assert result.returncode == 0
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["version"] == 3
    assert data["todos"][0]["status"] == "done"
    assert "done" not in data["todos"][0]


def test_v3_store_round_trip(tmp_path):
    path = tmp_path / "todos.json"
    todo.save_todos(str(path), [{"id": 1, "title": "a", "status": "in-progress"}])
    data = json.loads(path.read_text())
    assert data["version"] == 3
    assert data["todos"][0]["status"] == "in-progress"


def test_v3_missing_status_defaults_todo(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps({"version": 3, "todos": [{"id": 1, "title": "Buy milk"}]})
    )
    todos = todo.load_todos(str(tmp_path / "todos.json"))
    assert todos[0]["status"] == "todo"


def test_v3_invalid_status_fails_every_command(tmp_path):
    content = json.dumps({"version": 3, "todos": [{"id": 1, "title": "x", "status": "doing"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: invalid status"
    assert (tmp_path / "todos.json").read_text() == content


def test_v3_done_key_dropped_on_save(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            {
                "version": 3,
                "todos": [{"id": 1, "title": "Buy milk", "status": "todo", "done": True}],
            }
        )
    )
    run_cmd(tmp_path, "done", "1")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert "done" not in data["todos"][0]
    assert data["todos"][0]["status"] == "done"


def test_list_does_not_migrate_v2(tmp_path):
    content = json.dumps({"version": 2, "todos": [{"id": 1, "title": "Buy milk", "done": True}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 0
    assert result.stdout == "1 [x] Buy milk\n"
    assert (tmp_path / "todos.json").read_text() == content


def test_version_4_unsupported(tmp_path):
    content = json.dumps({"version": 4})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 4"
    assert (tmp_path / "todos.json").read_text() == content
