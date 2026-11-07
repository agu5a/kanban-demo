import os
import subprocess
import sys
from pathlib import Path

import pytest

import todo
import todolib.cli
import todolib.model
import todolib.render
import todolib.store


def test_todo_reexports_public_names():
    assert todo.load_todos is todolib.store.load_todos
    assert todo.save_todos is todolib.store.save_todos
    assert todo.normalize_todo is todolib.store.normalize_todo
    assert todo.find_todo is todolib.model.find_todo
    assert todo.today is todolib.model.today
    assert todo.build_parser is todolib.cli.build_parser
    assert todo.main is todolib.cli.main


def test_todo_py_defines_no_commands():
    cmd_funcs = [name for name in dir(todo) if name.startswith("cmd_")]
    assert cmd_funcs == []


@pytest.mark.parametrize(
    "module", ["todolib.store", "todolib.model", "todolib.render", "todolib.cli"]
)
def test_todolib_modules_import(module):
    # a fresh interpreter, so each module must import on its own (no cycle, no reliance on todo.py)
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_entry_point_runs(tmp_path):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "missing.json")
    result = subprocess.run(
        [sys.executable, "todo.py", "list"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        env=env,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "No todos"
