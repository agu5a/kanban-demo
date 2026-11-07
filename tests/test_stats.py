import json
import os
import subprocess
import sys
from pathlib import Path


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


def _write_v2(tmp_path, todos):
    (tmp_path / "todos.json").write_text(json.dumps({"version": 2, "todos": todos}))


def _item(id, title, done=False, due=None):
    return {"id": id, "title": title, "done": done, "priority": "normal", "due": due, "labels": []}


def test_stats_counts(tmp_path):
    _write_v2(
        tmp_path,
        [
            _item(1, "a", done=False, due="2020-01-01"),
            _item(2, "b", done=True),
            _item(3, "c", done=False, due="2020-01-01"),
            _item(4, "d", done=False),
            _item(5, "e", done=True),
        ],
    )
    result = run_cmd(tmp_path, "stats", env_extra={"TODO_TODAY": "2020-01-02"})
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["open: 3", "done: 2", "overdue: 2", "total: 5"]


def test_stats_matches_list_filters(tmp_path):
    _write_v2(
        tmp_path,
        [
            _item(1, "past", done=False, due="2020-01-01"),
            _item(2, "today", done=False, due="2020-01-02"),
            _item(3, "done past", done=True, due="2020-01-01"),
            _item(4, "open no due", done=False),
        ],
    )
    env_extra = {"TODO_TODAY": "2020-01-02"}
    stats = run_cmd(tmp_path, "stats", env_extra=env_extra)
    assert stats.returncode == 0, stats.stderr
    lines = stats.stdout.splitlines()
    open_count = int(lines[0].split(": ")[1])
    done_count = int(lines[1].split(": ")[1])
    overdue_count = int(lines[2].split(": ")[1])

    def count_lines(*args):
        r = run_cmd(tmp_path, *args, env_extra=env_extra)
        assert r.returncode == 0, r.stderr
        out = r.stdout.strip()
        if out == "No todos" or out == "":
            return 0
        return len(out.splitlines())

    assert open_count == count_lines("list", "--open")
    assert done_count == count_lines("list", "--done")
    assert overdue_count == count_lines("list", "--overdue")


def test_stats_overdue_uses_todo_today(tmp_path):
    _write_v2(tmp_path, [_item(1, "past", done=False, due="2020-01-01")])
    r1 = run_cmd(tmp_path, "stats", env_extra={"TODO_TODAY": "2020-01-01"})
    assert r1.returncode == 0
    assert "overdue: 0" in r1.stdout
    r2 = run_cmd(tmp_path, "stats", env_extra={"TODO_TODAY": "2020-01-02"})
    assert r2.returncode == 0
    assert "overdue: 1" in r2.stdout


def test_stats_due_today_not_overdue(tmp_path):
    _write_v2(tmp_path, [_item(1, "today", done=False, due="2020-01-01")])
    result = run_cmd(tmp_path, "stats", env_extra={"TODO_TODAY": "2020-01-01"})
    assert result.returncode == 0
    assert "overdue: 0" in result.stdout


def test_stats_done_item_not_overdue(tmp_path):
    _write_v2(tmp_path, [_item(1, "done past", done=True, due="2020-01-01")])
    result = run_cmd(tmp_path, "stats", env_extra={"TODO_TODAY": "2020-01-02"})
    assert result.returncode == 0
    assert "overdue: 0" in result.stdout


def test_stats_invalid_today_exits_1(tmp_path):
    _write_v2(tmp_path, [_item(1, "past", done=False, due="2020-01-01")])
    result = run_cmd(tmp_path, "stats", env_extra={"TODO_TODAY": "bad"})
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid TODO_TODAY: bad"


def test_stats_invalid_today_missing_store_exits_1(tmp_path):
    result = run_cmd(tmp_path, "stats", env_extra={"TODO_TODAY": "bad"})
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid TODO_TODAY: bad"
    assert not (tmp_path / "todos.json").exists()


def test_stats_empty_store_all_zero(tmp_path):
    (tmp_path / "todos.json").write_text("")
    result = run_cmd(tmp_path, "stats")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["open: 0", "done: 0", "overdue: 0", "total: 0"]


def test_stats_missing_store_all_zero(tmp_path):
    result = run_cmd(tmp_path, "stats")
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["open: 0", "done: 0", "overdue: 0", "total: 0"]


def test_stats_does_not_write_store(tmp_path):
    # v1 (plain list): any write would migrate it, so byte identity proves stats never writes
    content = json.dumps([{"id": 1, "title": "x", "done": True}, {"id": 2, "title": "y"}])
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "stats")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "todos.json").read_text() == content


def test_stats_unsupported_version_exits_1(tmp_path):
    content = json.dumps({"version": 4, "todos": [{"id": 1, "title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "stats")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 4"
    assert (tmp_path / "todos.json").read_text() == content


def test_stats_invalid_item_exits_1(tmp_path):
    content = json.dumps({"version": 2, "todos": [{"title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "stats")
    assert result.returncode == 1
    assert result.stderr.strip() == "Invalid store item 1: missing id"


def test_stats_extra_arg_exits_2(tmp_path):
    result = run_cmd(tmp_path, "stats", "foo")
    assert result.returncode == 2
