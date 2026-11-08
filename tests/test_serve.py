import json
import os
import re
import signal
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest


def _write_store(data):
    path = Path(os.environ["TODO_FILE"])
    path.write_text(json.dumps(data), encoding="utf-8")


def test_get_root_returns_html_with_title(board_server):
    with urllib.request.urlopen(board_server + "/") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "text/html; charset=utf-8"
        body = resp.read().decode("utf-8")
    assert "<title>Board</title>" in body


def test_columns_in_order_with_data_status(board_server):
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")

    positions = []
    for status in ("todo", "in-progress", "done"):
        idx = body.find(f'data-status="{status}"')
        assert idx != -1
        positions.append(idx)
    assert positions == sorted(positions)
    assert "To do" in body
    assert "In progress" in body
    assert "Done" in body


def test_items_in_their_status_column(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                },
                {
                    "id": 2,
                    "title": "B",
                    "status": "in-progress",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                },
                {
                    "id": 3,
                    "title": "C",
                    "status": "done",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                },
            ],
        }
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    # each article appears after its section heading; check section contains
    import re

    for status, title in (("todo", "A"), ("in-progress", "B"), ("done", "C")):
        m = re.search(rf'<section data-status="{status}">(.*?)</section>', body, re.DOTALL)
        assert m, status
        assert f">{title}<" not in m.group(1) or True
        assert (
            f"#{ {1: 1, 2: 2, 3: 3}[{'todo': 1, 'in-progress': 2, 'done': 3}[status]] }"
            in m.group(1)
            or True
        )
    # simpler
    m1 = re.search(r'<section data-status="todo">(.*?)</section>', body, re.DOTALL).group(1)
    assert 'data-id="1"' in m1
    m2 = re.search(r'<section data-status="in-progress">(.*?)</section>', body, re.DOTALL).group(1)
    assert 'data-id="2"' in m2
    m3 = re.search(r'<section data-status="done">(.*?)</section>', body, re.DOTALL).group(1)
    assert 'data-id="3"' in m3


def test_items_sorted_by_id(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 3,
                    "title": "C",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                },
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                },
                {
                    "id": 2,
                    "title": "B",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                },
            ],
        }
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    m = (
        __import__("re")
        .search(r'<section data-status="todo">(.*?)</section>', body, __import__("re").S)
        .group(1)
    )
    ids = __import__("re").findall(r'data-id="(\d+)"', m)
    assert ids == ["1", "2", "3"]


def test_item_text_has_list_suffixes(board_server, monkeypatch):
    monkeypatch.setenv("TODO_TODAY", "2026-01-01")
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 3,
                    "title": "Write report",
                    "status": "todo",
                    "priority": "high",
                    "due": "2026-12-01",
                    "labels": ["work"],
                },
            ],
        }
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    assert "#3 Write report (high) due:2026-12-01 #work" in body


def test_title_and_labels_escaped(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "<b>x</b>",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": ["<tag>"],
                },
            ],
        }
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    assert "&lt;b&gt;x&lt;/b&gt;" in body
    assert "#&lt;tag&gt;" in body


def test_no_script_or_external_resources(board_server):
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    assert "<script" not in body.lower()
    assert "<link" not in body.lower()


def test_store_reread_each_request(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "First",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                },
            ],
        }
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body1 = resp.read().decode("utf-8")
    assert "First" in body1
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 2,
                    "title": "Second",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                },
            ],
        }
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body2 = resp.read().decode("utf-8")
    assert "Second" in body2
    assert "First" not in body2


def test_get_does_not_write_store(board_server):
    # v1 list store (pre-migration format)
    path = Path(os.environ["TODO_FILE"])
    path.write_text(json.dumps([{"id": 1, "title": "X", "done": True}]), encoding="utf-8")
    before = path.read_text()
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    after = path.read_text()
    assert before == after
    assert body  # board rendered


def test_missing_store_empty_board(board_server):
    path = Path(os.environ["TODO_FILE"])
    if path.exists():
        path.unlink()
    with urllib.request.urlopen(board_server + "/") as resp:
        assert resp.status == 200
        body = resp.read().decode("utf-8")
    assert body.count("data-status=") == 3
    assert "<article" not in body


def test_unsupported_version_returns_500_with_message(board_server):
    Path(os.environ["TODO_FILE"]).write_text(
        json.dumps({"version": 4, "todos": []}), encoding="utf-8"
    )
    try:
        urllib.request.urlopen(board_server + "/")
    except urllib.error.HTTPError as exc:
        assert exc.code == 500
        assert exc.headers.get("Content-Type") == "text/plain; charset=utf-8"
        body = exc.read().decode("utf-8")
        assert body == "Unsupported store version: 4"
    else:
        raise AssertionError("expected 500")


def test_invalid_item_returns_500_with_message(board_server):
    Path(os.environ["TODO_FILE"]).write_text(
        json.dumps({"version": 3, "todos": [{"id": 1}]}), encoding="utf-8"
    )
    # item missing title -> invalid item 1? Actually position 1
    try:
        urllib.request.urlopen(board_server + "/")
    except urllib.error.HTTPError as exc:
        assert exc.code == 500
        body = exc.read().decode("utf-8")
        assert body == "Invalid store item 1: missing title"
    else:
        raise AssertionError("expected 500")


# Make invalid item position 2 for message "2: missing title"
def test_invalid_item_2_returns_500(board_server):
    Path(os.environ["TODO_FILE"]).write_text(
        json.dumps(
            {
                "version": 3,
                "todos": [
                    {
                        "id": 1,
                        "title": "ok",
                        "status": "todo",
                        "priority": "normal",
                        "due": None,
                        "labels": [],
                    },
                    {"id": 2},
                ],
            }
        ),
        encoding="utf-8",
    )
    try:
        urllib.request.urlopen(board_server + "/")
    except urllib.error.HTTPError as exc:
        assert exc.code == 500
        body = exc.read().decode("utf-8")
        assert body == "Invalid store item 2: missing title"
    else:
        raise AssertionError("expected 500")


def test_unknown_path_returns_404(board_server):
    try:
        urllib.request.urlopen(board_server + "/x")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("expected 404")
    try:
        urllib.request.urlopen(board_server + "/favicon.ico")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("expected 404")


def test_items_have_move_form(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    assert '<form method="post" action="/move">' in body
    assert '<input type="hidden" name="id" value="1">' in body
    assert '<select name="status">' in body
    for s in ("todo", "in-progress", "done"):
        assert f'<option value="{s}"' in body
    assert '<button type="submit">Move</button>' in body


def test_move_form_selects_current_status(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "in-progress",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    assert '<option value="in-progress" selected>in-progress</option>' in body
    assert '<option value="todo">todo</option>' in body
    assert '<option value="done">done</option>' in body


def _no_redirect_opener():
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    return urllib.request.build_opener(NoRedirect)


def test_post_move_redirects_303_to_root(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    data = urllib.parse.urlencode({"id": "1", "status": "done"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 303
        assert exc.headers.get("Location") == "/"
    else:
        raise AssertionError("expected 303")


def test_post_move_updates_store(board_server):
    path = Path(os.environ["TODO_FILE"])
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    data = urllib.parse.urlencode({"id": "1", "status": "done"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 303
    import json as _json

    store = _json.loads(path.read_text())
    assert store["todos"][0]["status"] == "done"


def test_post_move_then_get_shows_new_column(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    data = urllib.parse.urlencode({"id": "1", "status": "done"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError:
        pass
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    m = re.search(r'<section data-status="done">(.*?)</section>', body, re.DOTALL)
    assert m and 'data-id="1"' in m.group(1)
    m2 = re.search(r'<section data-status="todo">(.*?)</section>', body, re.DOTALL)
    assert m2 and 'data-id="1"' not in m2.group(1)


def test_post_move_same_status_does_not_write(board_server):
    path = Path(os.environ["TODO_FILE"])
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    before = path.read_text()
    data = urllib.parse.urlencode({"id": "1", "status": "todo"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 303
    after = path.read_text()
    assert before == after


def test_post_move_unknown_id_404(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    data = urllib.parse.urlencode({"id": "999", "status": "done"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
        assert exc.read().decode() == "Unknown id: 999"
    else:
        raise AssertionError("expected 404")


def test_post_move_missing_store_404(board_server):
    path = Path(os.environ["TODO_FILE"])
    if path.exists():
        path.unlink()
    data = urllib.parse.urlencode({"id": "999", "status": "done"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
        assert exc.read().decode() == "Unknown id: 999"
    else:
        raise AssertionError("expected 404")


@pytest.mark.parametrize("missing", ["id", "status"])
def test_post_move_missing_field_400(board_server, missing):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    params = {"id": "1", "status": "done"}
    params.pop(missing)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("expected 400")


@pytest.mark.parametrize("bad", ["", "abc", "1.5", "-1"])
def test_post_move_bad_id_400(board_server, bad):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    data = urllib.parse.urlencode({"id": bad, "status": "done"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("expected 400")


def test_post_move_bad_status_400(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "A",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )
    data = urllib.parse.urlencode({"id": "1", "status": "nope"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 400
    else:
        raise AssertionError("expected 400")


def test_post_move_store_error_500(board_server):
    Path(os.environ["TODO_FILE"]).write_text(
        json.dumps({"version": 3, "todos": [{"id": 1}]}), encoding="utf-8"
    )
    data = urllib.parse.urlencode({"id": "1", "status": "done"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 500
        body = exc.read().decode("utf-8")
        assert body == "Invalid store item 1: missing title"
    else:
        raise AssertionError("expected 500")


def test_post_unknown_path_404(board_server):
    data = b""
    req = urllib.request.Request(
        board_server + "/nope",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("expected 404")


def test_make_server_port_0_binds_free_port():
    from todolib.web import make_server

    server = make_server("127.0.0.1", 0)
    assert server.server_port != 0
    server.server_close()


def test_serve_cli_prints_url_and_exits_0_on_sigint(tmp_path):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    proc = subprocess.Popen(
        [sys.executable, "todo.py", "serve", "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        env=env,
    )
    # read the serving line
    line = proc.stdout.readline()
    assert line.startswith("Serving on http://")
    assert line.strip().endswith("/")
    # send SIGINT
    proc.send_signal(signal.SIGINT)
    proc.wait(timeout=10)
    assert proc.returncode == 0


def test_serve_invalid_port_exits_2(tmp_path):
    env = dict(os.environ)
    env["TODO_FILE"] = str(tmp_path / "todos.json")
    result = subprocess.run(
        [sys.executable, "todo.py", "serve", "--port", "abc"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(Path(__file__).resolve().parent.parent),
        env=env,
    )
    assert result.returncode == 2
