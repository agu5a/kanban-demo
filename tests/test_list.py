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


def test_list_open_filter(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Open one",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Closed one",
                "done": True,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--open")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Open one"]


def test_list_done_filter(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Open one",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Closed one",
                "done": True,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--done")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["2 [x] Closed one"]


def test_list_open_and_done_exits_2(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Open one",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", "--open", "--done")
    assert result.returncode == 2
    assert result.stderr.strip() != ""


def test_list_priority_filter(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Low one",
                "done": False,
                "priority": "low",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "High one",
                "done": False,
                "priority": "high",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--priority", "high")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["2 [ ] High one (high)"]


def test_list_priority_filter_repeatable_is_any(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Low one",
                "done": False,
                "priority": "low",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Normal one",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 3,
                "title": "High one",
                "done": False,
                "priority": "high",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--priority", "high", "--priority", "low")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Low one (low)", "3 [ ] High one (high)"]


def test_list_priority_invalid_exits_2(tmp_path):
    result = run_cmd(tmp_path, "list", "--priority", "urgent")
    assert result.returncode == 2
    assert result.stderr.strip() != ""


def test_list_label_filter(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Home one",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": ["home"],
            },
            {
                "id": 2,
                "title": "Money one",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": ["money"],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--label", "home")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Home one #home"]


def test_list_label_filter_repeatable_is_all(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Both",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": ["home", "money"],
            },
            {
                "id": 2,
                "title": "Home only",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": ["home"],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--label", "home", "--label", "money")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Both #home #money"]


def test_list_label_filter_lowercases(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Home one",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": ["home"],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", "--label", "Home")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Home one #home"]


def test_list_label_invalid_exits_2(tmp_path):
    result = run_cmd(tmp_path, "list", "--label", "a b")
    assert result.returncode == 2
    assert result.stderr.strip() != ""


def test_list_search_case_insensitive(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Buy Milk",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Other",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--search", "milk")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Buy Milk"]


def test_list_overdue_matches_past_due(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Past",
                "done": False,
                "priority": "normal",
                "due": "2020-01-01",
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", "--overdue", env_extra={"TODO_TODAY": "2020-01-02"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Past due:2020-01-01"]


def test_list_overdue_excludes_due_today(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Today",
                "done": False,
                "priority": "normal",
                "due": "2020-01-01",
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", "--overdue", env_extra={"TODO_TODAY": "2020-01-01"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "No todos"


def test_list_overdue_excludes_done(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Done past",
                "done": True,
                "priority": "normal",
                "due": "2020-01-01",
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", "--overdue", env_extra={"TODO_TODAY": "2020-01-02"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "No todos"


def test_list_overdue_excludes_no_due(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "No due",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", "--overdue", env_extra={"TODO_TODAY": "2020-01-02"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "No todos"


def test_list_overdue_invalid_today_exits_1(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Past",
                "done": False,
                "priority": "normal",
                "due": "2020-01-01",
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", "--overdue", env_extra={"TODO_TODAY": "bad"})
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid TODO_TODAY: bad"


def test_list_overdue_invalid_today_without_candidates_exits_1(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Done past",
                "done": True,
                "priority": "normal",
                "due": "2020-01-01",
                "labels": [],
            },
            {
                "id": 2,
                "title": "No due",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--overdue", env_extra={"TODO_TODAY": "bad"})
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid TODO_TODAY: bad"


def test_list_overdue_invalid_today_empty_store_exits_1(tmp_path):
    _write_v2(tmp_path, [])
    result = run_cmd(tmp_path, "list", "--overdue", env_extra={"TODO_TODAY": "bad"})
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid TODO_TODAY: bad"


def test_list_overdue_invalid_today_missing_store_exits_1(tmp_path):
    result = run_cmd(tmp_path, "list", "--overdue", env_extra={"TODO_TODAY": "bad"})
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid TODO_TODAY: bad"
    assert not (tmp_path / "todos.json").exists()


def test_list_invalid_today_ignored_without_overdue(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Past",
                "done": False,
                "priority": "normal",
                "due": "2020-01-01",
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", env_extra={"TODO_TODAY": "bad"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Past due:2020-01-01"]


def test_list_filters_combine_with_and(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Match",
                "done": False,
                "priority": "high",
                "due": "2020-01-01",
                "labels": ["home"],
            },
            {
                "id": 2,
                "title": "NoMatch",
                "done": False,
                "priority": "high",
                "due": "2030-01-01",
                "labels": ["home"],
            },
        ],
    )
    result = run_cmd(
        tmp_path,
        "list",
        "--open",
        "--priority",
        "high",
        "--label",
        "home",
        "--search",
        "mat",
        "--overdue",
        env_extra={"TODO_TODAY": "2020-01-02"},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] Match (high) due:2020-01-01 #home"]


def test_list_no_match_prints_no_todos(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Buy milk",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            }
        ],
    )
    result = run_cmd(tmp_path, "list", "--search", "zzzz")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "No todos"


def test_list_filter_does_not_write_store(tmp_path):
    content = json.dumps(
        {
            "version": 2,
            "todos": [
                {
                    "id": 1,
                    "title": "Buy milk",
                    "done": False,
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list", "--open")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "todos.json").read_text() == content


def test_list_filter_unsupported_version_exits_1(tmp_path):
    content = json.dumps({"version": 3, "todos": [{"id": 1, "title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list", "--open")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 3"
    assert (tmp_path / "todos.json").read_text() == content


def test_list_sort_default_is_id(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 2,
                "title": "Two",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 1,
                "title": "One",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] One", "2 [ ] Two"]


def test_list_sort_id(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 2,
                "title": "Two",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 1,
                "title": "One",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--sort", "id")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] One", "2 [ ] Two"]


def test_list_sort_priority_order(tmp_path):
    _write_v2(
        tmp_path,
        [
            {"id": 1, "title": "Low", "done": False, "priority": "low", "due": None, "labels": []},
            {
                "id": 2,
                "title": "High",
                "done": False,
                "priority": "high",
                "due": None,
                "labels": [],
            },
            {
                "id": 3,
                "title": "Normal",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--sort", "priority")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == [
        "2 [ ] High (high)",
        "3 [ ] Normal",
        "1 [ ] Low (low)",
    ]


def test_list_sort_priority_ties_by_id(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Third",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 1,
                "title": "First",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Second",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--sort", "priority")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["1 [ ] First", "2 [ ] Second", "3 [ ] Third"]


def test_list_sort_priority_unknown_value_ranks_normal(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "High",
                "done": False,
                "priority": "high",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Unknown",
                "done": False,
                "priority": "urgent",
                "due": None,
                "labels": [],
            },
            {
                "id": 3,
                "title": "Normal",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {"id": 4, "title": "Low", "done": False, "priority": "low", "due": None, "labels": []},
        ],
    )
    result = run_cmd(tmp_path, "list", "--sort", "priority")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == [
        "1 [ ] High (high)",
        "2 [ ] Unknown",
        "3 [ ] Normal",
        "4 [ ] Low (low)",
    ]


def test_list_sort_due_earliest_first(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Later",
                "done": False,
                "priority": "normal",
                "due": "2026-02-02",
                "labels": [],
            },
            {
                "id": 2,
                "title": "Earlier",
                "done": False,
                "priority": "normal",
                "due": "2026-01-01",
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--sort", "due")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == [
        "2 [ ] Earlier due:2026-01-01",
        "1 [ ] Later due:2026-02-02",
    ]


def test_list_sort_due_none_last(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "No due",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Due",
                "done": False,
                "priority": "normal",
                "due": "2026-01-01",
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--sort", "due")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["2 [ ] Due due:2026-01-01", "1 [ ] No due"]


def test_list_sort_due_ties_by_id(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 3,
                "title": "Third",
                "done": False,
                "priority": "normal",
                "due": "2026-01-01",
                "labels": [],
            },
            {
                "id": 1,
                "title": "First",
                "done": False,
                "priority": "normal",
                "due": "2026-01-01",
                "labels": [],
            },
            {
                "id": 2,
                "title": "Second",
                "done": False,
                "priority": "normal",
                "due": "2026-01-01",
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--sort", "due")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == [
        "1 [ ] First due:2026-01-01",
        "2 [ ] Second due:2026-01-01",
        "3 [ ] Third due:2026-01-01",
    ]


def test_list_sort_invalid_exits_2(tmp_path):
    result = run_cmd(tmp_path, "list", "--sort", "foo")
    assert result.returncode == 2
    assert result.stderr.strip() != ""


def test_list_sort_does_not_write_store(tmp_path):
    content = json.dumps(
        {
            "version": 2,
            "todos": [
                {
                    "id": 2,
                    "title": "Later",
                    "done": False,
                    "priority": "normal",
                    "due": "2026-02-02",
                    "labels": [],
                },
                {
                    "id": 1,
                    "title": "Earlier",
                    "done": False,
                    "priority": "normal",
                    "due": "2026-01-01",
                    "labels": [],
                },
            ],
        }
    )
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list", "--sort", "due")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "todos.json").read_text() == content


def test_list_sort_unsupported_version_exits_1(tmp_path):
    content = json.dumps({"version": 3, "todos": [{"id": 1, "title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "list", "--sort", "id")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 3"
    assert (tmp_path / "todos.json").read_text() == content


def test_list_filter_then_sort(tmp_path):
    _write_v2(
        tmp_path,
        [
            {
                "id": 1,
                "title": "Open normal",
                "done": False,
                "priority": "normal",
                "due": None,
                "labels": [],
            },
            {
                "id": 2,
                "title": "Done high",
                "done": True,
                "priority": "high",
                "due": None,
                "labels": [],
            },
            {
                "id": 3,
                "title": "Open high",
                "done": False,
                "priority": "high",
                "due": None,
                "labels": [],
            },
        ],
    )
    result = run_cmd(tmp_path, "list", "--open", "--sort", "priority")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == [
        "3 [ ] Open high (high)",
        "1 [ ] Open normal",
    ]
