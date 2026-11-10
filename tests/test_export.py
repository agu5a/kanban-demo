import json
import os
import subprocess
import sys
from pathlib import Path


def _write_v2(tmp_path, todos):
    (tmp_path / "todos.json").write_text(json.dumps({"version": 3, "todos": todos}))


def run_cmd(tmp_path, *args, env_extra=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent.parent / "todo.py"), *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_export_default_format_is_json(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Buy milk",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "export")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        {
            "id": 1,
            "title": "Buy milk",
            "status": "todo",
            "priority": "normal",
            "due": None,
            "labels": [],
        }
    ]


def test_export_json_all_six_fields(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Buy milk",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert list(data[0].keys()) == ["id", "title", "status", "priority", "due", "labels"]


def test_export_json_empty_prints_brackets(tmp_path):
    (tmp_path / "todos.json").write_text("[]")
    result = run_cmd(tmp_path, "export")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


def test_export_csv_header_and_row(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Buy milk",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "csv")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "id,title,status,priority,due,labels,assignee",
        "1,Buy milk,todo,normal,,,",
    ]


def test_export_csv_done_true_false(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Open",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Closed",
                "status": "done",
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "csv")
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[1].split(",")[2] == "todo"
    assert lines[2].split(",")[2] == "done"


def test_export_csv_empty_due_field(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "No due",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "csv")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1] == "1,No due,todo,normal,,,"


def test_export_csv_labels_joined(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "T",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": ["a", "b"],
            }
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "csv")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1] == "1,T,todo,normal,,a;b,"


def test_export_csv_quotes_commas_and_quotes(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": 'a, "b"',
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "csv")
    assert result.returncode == 0, result.stderr
    assert '"a, ""b"""' in result.stdout


def test_export_csv_uses_newline_terminator(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "T",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "csv")
    assert result.returncode == 0, result.stderr
    assert "\r" not in result.stdout
    assert result.stdout.endswith("\n")


def test_export_csv_empty_prints_header(tmp_path):
    (tmp_path / "todos.json").write_text("[]")
    result = run_cmd(tmp_path, "export", "--format", "csv")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "id,title,status,priority,due,labels,assignee"


def test_export_md_open_and_done_lines(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Open",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Closed",
                "status": "done",
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "md")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["- [ ] Open", "- [x] Closed"]


def test_export_md_suffixes_match_list(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Pay rent",
                "status": "todo",
                "priority": "high",
                "due": "2026-12-01",
                "labels": ["home", "money"],
            }
        ],
    )
    result = run_cmd(tmp_path, "export", "--format", "md")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "- [ ] Pay rent (high) due:2026-12-01 #home #money"


def test_export_md_empty_prints_nothing(tmp_path):
    (tmp_path / "todos.json").write_text("[]")
    result = run_cmd(tmp_path, "export", "--format", "md")
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_export_invalid_format_exits_2(tmp_path):
    result = run_cmd(tmp_path, "export", "--format", "yaml")
    assert result.returncode == 2


def test_export_filters_apply(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Open high",
                "status": "todo",
                "priority": "high",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Done low",
                "status": "done",
                "priority": "low",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "export", "--open")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert [t["id"] for t in data] == [1]


def test_export_sort_applies(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Later",
                "status": "todo",
                "priority": "normal",
                "due": "2026-02-02",
                "labels": [],
            },
            {
                "id": 2,
                "title": "Earlier",
                "status": "todo",
                "priority": "normal",
                "due": "2026-01-01",
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "export", "--sort", "due")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert [t["id"] for t in data] == [2, 1]


def test_export_filter_then_sort(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 2,
                "title": "Open B",
                "status": "todo",
                "priority": "low",
                "due": None,
                "labels": [],
            },
            {
                "id": 1,
                "title": "Done A",
                "status": "done",
                "priority": "high",
                "due": None,
                "labels": [],
            },
            {
                "id": 3,
                "title": "Open A",
                "status": "todo",
                "priority": "high",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "export", "--open", "--sort", "priority")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert [t["id"] for t in data] == [3, 2]


def test_export_open_and_done_exits_2(tmp_path):
    result = run_cmd(tmp_path, "export", "--open", "--done")
    assert result.returncode == 2


def test_export_overdue_invalid_today_exits_1(tmp_path):
    result = run_cmd(tmp_path, "export", "--overdue", env_extra={"TODO_TODAY": "bad"})
    assert result.returncode == 1
    assert "Invalid TODO_TODAY: bad" in result.stderr


def test_export_missing_file_is_empty(tmp_path):
    result = run_cmd(tmp_path, "export")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


def test_export_v1_store_not_migrated(tmp_path):
    content = json.dumps([{"id": 1, "title": "x"}])
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "export", "--format", "json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        {
            "id": 1,
            "title": "x",
            "status": "todo",
            "priority": "normal",
            "due": None,
            "labels": [],
        }
    ]
    assert (tmp_path / "todos.json").read_text() == content


def test_export_does_not_write_store(tmp_path):
    content = json.dumps(
        {
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
    )
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "export", "--format", "md")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "todos.json").read_text() == content


def test_export_unsupported_version_exits_1(tmp_path):
    content = json.dumps({"version": 4, "todos": [{"id": 1, "title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "export")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 4"
    assert (tmp_path / "todos.json").read_text() == content


def test_export_json_has_status_not_done(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            {
                "version": 3,
                "todos": [
                    {
                        "id": 1,
                        "title": "Task",
                        "status": "in-progress",
                        "priority": "normal",
                        "due": None,
                        "labels": [],
                    }
                ],
            }
        )
    )
    result = run_cmd(tmp_path, "export", "--format", "json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert "status" in data[0]
    assert "done" not in data[0]


def test_export_csv_status_column(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps(
            {
                "version": 3,
                "todos": [
                    {
                        "id": 2,
                        "title": "Write report",
                        "status": "in-progress",
                        "priority": "high",
                        "due": None,
                        "labels": [],
                    }
                ],
            }
        )
    )
    result = run_cmd(tmp_path, "export", "--format", "csv")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[1].split(",")[2] == "in-progress"


def test_export_md_in_progress_mark(tmp_path):
    (tmp_path / "todos.json").write_text(
        json.dumps({"version": 3, "todos": [{"id": 1, "title": "Task", "status": "in-progress"}]})
    )
    result = run_cmd(tmp_path, "export", "--format", "md")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "- [~] Task"


def test_export_does_not_migrate_v2(tmp_path):
    content = json.dumps({"version": 2, "todos": [{"id": 1, "title": "Buy milk", "done": True}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "export", "--format", "json")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "todos.json").read_text() == content


def test_export_status_filter(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Todo one",
                "status": "todo",
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Done one",
                "status": "done",
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "export", "--status", "done")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert [t["id"] for t in data] == [2]


def test_export_status_with_open_exits_2(tmp_path):
    result = run_cmd(tmp_path, "export", "--status", "todo", "--open")
    assert result.returncode == 2
