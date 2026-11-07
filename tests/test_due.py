import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import todo

TODO = Path(__file__).resolve().parent.parent / "todo.py"


def run_cmd(tmp_path, *args, env_overrides=None):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(TODO), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_due_sets_date(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    result = run_cmd(tmp_path, "due", "1", "2026-12-01")
    assert result.returncode == 0
    assert result.stdout == ""
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["due"] == "2026-12-01"


def test_due_none_clears_date(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk", "--due", "2026-12-01")
    result = run_cmd(tmp_path, "due", "1", "none")
    assert result.returncode == 0
    assert result.stdout == ""
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0]["due"] is None


def test_due_does_not_affect_other_todos(tmp_path):
    run_cmd(tmp_path, "add", "First")
    run_cmd(tmp_path, "add", "Second")
    before = json.loads((tmp_path / "todos.json").read_text())
    run_cmd(tmp_path, "due", "1", "2026-12-01")
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data["todos"][0] == {**before["todos"][0], "due": "2026-12-01"}
    assert data["todos"][1] == before["todos"][1]


def test_due_migrates_v1_store(tmp_path):
    (tmp_path / "todos.json").write_text(json.dumps([{"id": 1, "title": "Buy milk"}]))
    result = run_cmd(tmp_path, "due", "1", "2026-12-01")
    assert result.returncode == 0
    data = json.loads((tmp_path / "todos.json").read_text())
    assert data == {
        "version": 3,
        "todos": [
            {
                "id": 1,
                "title": "Buy milk",
                "status": "todo",
                "priority": "normal",
                "due": "2026-12-01",
                "labels": [],
            }
        ],
    }


def test_due_unknown_id_exits_1(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "due", "99", "2026-12-01")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 99"
    assert (tmp_path / "todos.json").read_text() == original


def test_due_unknown_id_missing_file(tmp_path):
    result = run_cmd(tmp_path, "due", "99", "2026-12-01")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unknown id: 99"
    assert not (tmp_path / "todos.json").exists()


def test_due_invalid_calendar_date_exits_2(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "due", "1", "2026-02-30")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_due_non_date_exits_2(tmp_path):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "due", "1", "tomorrow")
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


@pytest.mark.parametrize("value", ["20261201", "2026-W49-2"])
def test_due_compact_iso_exits_2(tmp_path, value):
    run_cmd(tmp_path, "add", "Buy milk")
    original = (tmp_path / "todos.json").read_text()
    result = run_cmd(tmp_path, "due", "1", value)
    assert result.returncode == 2
    assert result.stderr.strip() != ""
    assert (tmp_path / "todos.json").read_text() == original


def test_due_unsupported_version_exits_1(tmp_path):
    content = json.dumps({"version": 4, "todos": [{"id": 1, "title": "x"}]})
    (tmp_path / "todos.json").write_text(content)
    result = run_cmd(tmp_path, "due", "1", "2026-12-01")
    assert result.returncode == 1
    assert result.stderr.strip() == "Unsupported store version: 4"
    assert (tmp_path / "todos.json").read_text() == content


def test_today_uses_env(monkeypatch):
    monkeypatch.setenv("TODO_TODAY", "2026-12-01")
    assert todo.today() == datetime.date(2026, 12, 1)


def test_today_defaults_to_system_date(monkeypatch):
    monkeypatch.delenv("TODO_TODAY", raising=False)
    assert todo.today() == datetime.date.today()


@pytest.mark.parametrize("value", ["not-a-date", "2026-02-30", "20261201"])
def test_today_invalid_env_exits_1(monkeypatch, capsys, value):
    monkeypatch.setenv("TODO_TODAY", value)
    with pytest.raises(SystemExit) as exc:
        todo.today()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert captured.err.strip() == f"Invalid TODO_TODAY: {value}"
