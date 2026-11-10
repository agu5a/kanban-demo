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
        m = re.search(
            rf'<section [^>]*data-status="{status}"[^>]*>(.*?)</section>', body, re.DOTALL
        )
        assert m, status
        assert f">{title}<" not in m.group(1) or True
        assert (
            f"#{ {1: 1, 2: 2, 3: 3}[{'todo': 1, 'in-progress': 2, 'done': 3}[status]] }"
            in m.group(1)
            or True
        )
    # simpler
    m1 = re.search(r'<section [^>]*data-status="todo"[^>]*>(.*?)</section>', body, re.DOTALL).group(
        1
    )
    assert 'data-id="1"' in m1
    m2 = re.search(
        r'<section [^>]*data-status="in-progress"[^>]*>(.*?)</section>', body, re.DOTALL
    ).group(1)
    assert 'data-id="2"' in m2
    m3 = re.search(r'<section [^>]*data-status="done"[^>]*>(.*?)</section>', body, re.DOTALL).group(
        1
    )
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
        .search(r'<section [^>]*data-status="todo"[^>]*>(.*?)</section>', body, __import__("re").S)
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
    assert body.lower().count("<script") == 1
    assert '<script src="/static/board.js" defer></script>' in body
    # Only local bootstrap link allowed
    assert body.count('<link rel="stylesheet" href="/static/bootstrap.min.css">') == 1
    # No external URLs
    assert "http://" not in body
    assert "https://" not in body


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
    m = re.search(r'<section [^>]*data-status="done"[^>]*>(.*?)</section>', body, re.DOTALL)
    assert m and 'data-id="1"' in m.group(1)
    m2 = re.search(r'<section [^>]*data-status="todo"[^>]*>(.*?)</section>', body, re.DOTALL)
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


# Static file tests


def test_static_bootstrap_css_served(board_server):
    with urllib.request.urlopen(board_server + "/static/bootstrap.min.css") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "text/css; charset=utf-8"
        body = resp.read()
    # Compare with the actual file
    static_path = (
        Path(__file__).resolve().parent.parent / "todolib" / "static" / "bootstrap.min.css"
    )
    expected = static_path.read_bytes()
    assert body == expected


def test_static_asset_is_bootstrap_5_3_8():
    static_path = (
        Path(__file__).resolve().parent.parent / "todolib" / "static" / "bootstrap.min.css"
    )
    content = static_path.read_text(encoding="utf-8")
    # Check header matches Bootstrap v5.3.8
    import re

    assert re.search(r"Bootstrap\s+v5\.3\.8", content), "Bootstrap 5.3.8 header not found"


def test_static_unknown_file_404(board_server):
    req = urllib.request.Request(board_server + "/static/unknown.css")
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
        assert exc.headers.get("Content-Type") == "text/plain; charset=utf-8"
        body = exc.read().decode("utf-8")
        assert body == "Not Found"
    else:
        raise AssertionError("expected 404")


@pytest.mark.parametrize(
    "path",
    [
        "/static/../web.py",
        "/static/%2e%2e/web.py",
        "/static/%2e%2e%2fweb.py",
    ],
)
def test_static_path_traversal_404(board_server, path):
    req = urllib.request.Request(board_server + path)
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError(f"expected 404 for {path}")


def test_static_dir_listing_404(board_server):
    req = urllib.request.Request(board_server + "/static/")
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("expected 404 for /static/")


def test_post_static_404(board_server):
    data = b""
    req = urllib.request.Request(
        board_server + "/static/bootstrap.min.css",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        urllib.request.urlopen(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("expected 404 for POST /static/...")


def test_board_links_local_bootstrap(board_server):
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    # Check for the local bootstrap link
    assert '<link rel="stylesheet" href="/static/bootstrap.min.css">' in body
    # No external URLs
    assert "http://" not in body
    assert "https://" not in body


def test_board_has_no_inline_style_except_column_width(board_server):
    _write_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "Test",
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

    # Find all style attributes
    import re

    styles = re.findall(r'style="([^"]*)"', body)
    # Every style must be exactly "width: 20rem"
    for style in styles:
        assert style == "width: 20rem", f"Unexpected style: {style}"
    # There are exactly three sections (todo, in-progress, done)
    assert len(styles) == 3


@pytest.mark.parametrize(
    "path,method",
    [
        ("/nope", "GET"),
        ("/static/nope.css", "GET"),
        ("/static/", "GET"),
        ("/nope", "POST"),
        ("/static/bootstrap.min.css", "POST"),
    ],
)
def test_not_found_responses_identical(board_server, path, method):
    data = b"" if method == "POST" else None
    req = urllib.request.Request(
        board_server + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/x-www-form-urlencoded"} if method == "POST" else {},
    )
    opener = _no_redirect_opener()
    try:
        opener.open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
        assert exc.headers.get("Content-Type") == "text/plain; charset=utf-8"
        assert exc.headers.get("Content-Length") == "9"
        body = exc.read().decode("utf-8")
        assert body == "Not Found"
    else:
        raise AssertionError(f"expected 404 for {method} {path}")


def test_board_reads_sqlite_store(board_server, tmp_path, monkeypatch):
    from todolib.store import load_todos, save_todos

    path = tmp_path / "board.db"
    monkeypatch.setenv("TODO_FILE", str(path))
    todos = [
        {
            "id": 1,
            "title": "Alpha",
            "status": "todo",
            "priority": "normal",
            "due": None,
            "labels": [],
        },
        {
            "id": 2,
            "title": "Beta",
            "status": "in-progress",
            "priority": "normal",
            "due": None,
            "labels": [],
        },
        {
            "id": 3,
            "title": "Gamma",
            "status": "done",
            "priority": "normal",
            "due": None,
            "labels": [],
        },
    ]
    save_todos(path, todos)
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    for status, title in (("todo", "Alpha"), ("in-progress", "Beta"), ("done", "Gamma")):
        section = re.search(rf'<section[^>]*data-status="{status}".*?</section>', body, re.DOTALL)
        assert section and title in section.group(0)

    data = urllib.parse.urlencode({"id": "1", "status": "done"}).encode()
    req = urllib.request.Request(
        board_server + "/move",
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        _no_redirect_opener().open(req)
    except urllib.error.HTTPError as exc:
        assert exc.code == 303
    assert [t["status"] for t in load_todos(path)] == ["done", "in-progress", "done"]


def _item(todo_id, title="Item", status="todo"):
    return {
        "id": todo_id,
        "title": title,
        "status": status,
        "priority": "normal",
        "due": None,
        "labels": [],
    }


def _post_add(board_server, fields):
    """POST /add form-encoded; returns (status, headers, body) without following the redirect."""
    req = urllib.request.Request(
        board_server + "/add",
        data=urllib.parse.urlencode(fields).encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        resp = _no_redirect_opener().open(req)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read().decode("utf-8")
    return resp.status, resp.headers, resp.read().decode("utf-8")


def _stored():
    return json.loads(Path(os.environ["TODO_FILE"]).read_text())["todos"]


def test_board_has_new_todo_button_and_dialog(board_server):
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    button = (
        '<button type="button" class="btn btn-primary" data-action="new-todo">New todo</button>'
    )
    assert body.count(button) == 1
    assert body.index(button) < body.index("<main")
    assert '<dialog id="new-todo-dialog">' in body
    dialog = body[body.index('<dialog id="new-todo-dialog">') : body.index("</dialog>")]
    assert '<form method="post" action="/add">' in dialog
    assert re.search(r'<input class="form-control"[^>]* name="title" required>', dialog)
    assert re.search(r'<select class="form-select"[^>]* name="priority">', dialog)
    assert re.findall(r'<option value="(\w+)"', dialog) == ["low", "normal", "high"]
    assert '<option value="normal" selected>' in dialog
    assert re.search(r'<input class="form-control" type="date"[^>]* name="due">', dialog)
    assert re.search(r'<input class="form-control"[^>]* name="labels">', dialog)
    assert '<button type="submit" class="btn btn-primary">Create</button>' in dialog
    assert re.search(
        r'<button type="button" class="btn btn-secondary"[^>]*>Cancel</button>', dialog
    )
    assert '<script src="/static/board.js" defer></script>' in body


def test_board_has_no_inline_script(board_server):
    _write_store({"version": 3, "todos": [_item(1)]})
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    for match in re.finditer(r"<script\b[^>]*>(.*?)</script>", body, re.DOTALL | re.IGNORECASE):
        assert match.group(1) == ""
    assert not re.search(r"\son[a-z]+\s*=", body, re.IGNORECASE)


def test_static_board_js_served(board_server):
    with urllib.request.urlopen(board_server + "/static/board.js") as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "text/javascript; charset=utf-8"
        body = resp.read()
    assert body == (Path(__file__).parent.parent / "todolib" / "static" / "board.js").read_bytes()


def test_post_add_creates_todo(board_server):
    _write_store({"version": 3, "todos": [_item(1), _item(3)]})
    status, headers, _ = _post_add(board_server, {"title": "Buy milk"})
    assert status == 303
    assert headers.get("Location") == "/"
    assert _stored()[-1] == {
        "id": 4,
        "title": "Buy milk",
        "status": "todo",
        "priority": "normal",
        "due": None,
        "labels": [],
    }


def test_post_add_with_priority_due_labels(board_server):
    _write_store({"version": 3, "todos": [_item(1)]})
    status, _, _ = _post_add(
        board_server,
        {
            "title": "Gifts",
            "priority": "high",
            "due": "2026-12-24",
            "labels": " Home, urgent ,,home",
        },
    )
    assert status == 303
    item = _stored()[-1]
    assert item["priority"] == "high"
    assert item["due"] == "2026-12-24"
    assert item["labels"] == ["home", "urgent"]


@pytest.mark.parametrize(
    "fields,message",
    [
        ({"title": ""}, "title must not be empty"),
        ({"priority": "high"}, "title must not be empty"),
        ({"title": "X", "priority": "urgent"}, "invalid priority: urgent"),
        ({"title": "X", "due": "2026-02-30"}, "invalid date: 2026-02-30"),
        ({"title": "X", "labels": "bad label"}, "invalid label: bad label"),
    ],
    ids=["empty-title", "missing-title", "bad-priority", "bad-date", "bad-label"],
)
def test_post_add_validation_400(board_server, fields, message):
    _write_store({"version": 3, "todos": [_item(1)]})
    path = Path(os.environ["TODO_FILE"])
    before = path.read_bytes()
    status, headers, body = _post_add(board_server, fields)
    assert status == 400
    assert headers.get("Content-Type") == "text/plain; charset=utf-8"
    assert body == message
    assert path.read_bytes() == before


def test_post_add_missing_store_creates_it(board_server):
    path = Path(os.environ["TODO_FILE"])
    assert not path.exists()
    status, _, _ = _post_add(board_server, {"title": "First"})
    assert status == 303
    assert [(t["id"], t["title"]) for t in _stored()] == [(1, "First")]


def test_post_add_sqlite_store(board_server, tmp_path, monkeypatch):
    from todolib.store import load_todos

    path = tmp_path / "board.db"
    monkeypatch.setenv("TODO_FILE", str(path))
    status, _, _ = _post_add(board_server, {"title": "In the DB", "labels": "demo"})
    assert status == 303
    assert load_todos(path) == [
        {
            "id": 1,
            "title": "In the DB",
            "status": "todo",
            "priority": "normal",
            "due": None,
            "labels": ["demo"],
        }
    ]


def test_items_are_draggable(board_server):
    _write_store(
        {"version": 3, "todos": [_item(1), _item(2, status="in-progress"), _item(5, status="done")]}
    )
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    articles = re.findall(r"<article\b[^>]*>", body)
    assert len(articles) == 3
    for article, todo_id in zip(articles, (1, 2, 5), strict=True):
        assert 'draggable="true"' in article
        assert f'data-id="{todo_id}"' in article


def test_items_have_no_move_form(board_server):
    _write_store({"version": 3, "todos": [_item(1), _item(2, status="done")]})
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    assert 'action="/move"' not in body
    assert not re.search(r'<select[^>]* name="status"', body)
    assert ">Move</button>" not in body


def test_board_shows_assignee(board_server):
    item = _item(1, title="Review")
    item["assignee"] = "<Anna>"
    _write_store({"version": 3, "todos": [item]})
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    assert "#1 Review @&lt;Anna&gt;</article>" in body
    assert "<Anna>" not in body


@pytest.mark.parametrize(
    "value,expected",
    [("Anna", "Anna"), ("  Anna  ", "Anna"), ("   ", None), ("x" * 41, 400)],
    ids=["name", "trimmed", "blank", "too-long"],
)
def test_post_add_with_assignee(board_server, value, expected):
    _write_store({"version": 3, "todos": []})
    path = Path(os.environ["TODO_FILE"])
    before = path.read_bytes()
    status, _, body = _post_add(board_server, {"title": "Task", "assignee": value})
    if expected == 400:
        assert status == 400
        assert body == "assignee too long"
        assert path.read_bytes() == before
        return
    assert status == 303
    item = _stored()[-1]
    if expected is None:
        assert "assignee" not in item
    else:
        assert item["assignee"] == expected


def test_new_todo_dialog_has_assignee_input(board_server):
    with urllib.request.urlopen(board_server + "/") as resp:
        body = resp.read().decode("utf-8")
    dialog = body[body.index('<dialog id="new-todo-dialog">') : body.index("</dialog>")]
    assert re.search(r'<input class="form-control"[^>]* name="assignee">', dialog)
