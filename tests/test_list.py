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
        check=False,
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
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
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


def _write_v2(tmp_path, todos):
    (tmp_path / "todos.json").write_text(json.dumps({"version": 2, "todos": todos}))


def test_list_priority_high_suffix(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": False,
                "priority": "high",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [ ] Pay rent (high)"


def test_list_priority_low_suffix(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": False,
                "priority": "low",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [ ] Pay rent (low)"


def test_list_priority_normal_no_suffix(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [ ] Pay rent"


def test_list_due_suffix(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": False,
                "priority": "normal",
                "due": "2026-12-01",
                "labels": [],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [ ] Pay rent due:2026-12-01"


def test_list_no_due_no_suffix(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [ ] Pay rent"


def test_list_labels_suffix_in_stored_order(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": ["home", "money"],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [ ] Pay rent #home #money"


def test_list_full_line_suffix_order(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": False,
                "priority": "high",
                "due": "2026-12-01",
                "labels": ["home", "money"],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [ ] Pay rent (high) due:2026-12-01 #home #money"


def test_list_done_item_with_suffixes(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": True,
                "priority": "high",
                "due": "2026-12-01",
                "labels": ["home", "money"],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [x] Pay rent (high) due:2026-12-01 #home #money"


def test_list_v1_item_no_suffix(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1 [ ] Buy milk"


def test_list_with_suffixes_does_not_write_store(tmp_path, monkeypatch):
    content = json.dumps(
        {
            "version": 2,
            "todos": [
                {
                    "id": 3,
                    "title": "Pay rent",
                    "done": False,
                    "priority": "high",
                    "due": "2026-12-01",
                    "labels": ["home", "money"],
                }
            ],
        }
    )
    (tmp_path / "todos.json").write_text(content)
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "todos.json").read_text() == content


def test_list_unsupported_version_exits_1(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text(json.dumps({"version": 3}))
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 3"


def test_list_unknown_priority_no_suffix(tmp_path, monkeypatch):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Pay rent",
                "done": False,
                "priority": "urgent",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "3 [ ] Pay rent"


def test_list_zero_byte_store_prints_no_todos(tmp_path, monkeypatch):
    (tmp_path / "todos.json").write_text("")
    result = run_list(tmp_path, monkeypatch)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "No todos"
    assert (tmp_path / "todos.json").read_text() == ""
