"""Read-only web board: render the store as HTML over HTTP."""

import html
import http.server
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from todolib.model import UnknownTodoId, move_todo
from todolib.render import todo_suffixes
from todolib.store import (
    InvalidStoreItem,
    UnsupportedStoreVersion,
    load_todos,
    save_todos,
    store_path,
)

STATUSES = ("todo", "in-progress", "done")
HEADINGS = {
    "todo": "To do",
    "in-progress": "In progress",
    "done": "Done",
}

# Static files directory (relative to this file)
STATIC_DIR = Path(__file__).parent / "static"


def _render_todo(todo):
    todo_id = todo.get("id")
    title = todo.get("title", "")
    text = f"#{todo_id} {html.escape(title)}{html.escape(todo_suffixes(todo))}"
    status = todo.get("status") if isinstance(todo, dict) else None
    if status not in STATUSES:
        status = "todo"
    options = "".join(
        f'<option value="{s}"{" selected" if s == status else ""}>{s}</option>' for s in STATUSES
    )
    form = (
        f'<form method="post" action="/move">'
        f'<input type="hidden" name="id" value="{todo_id}">'
        f'<select class="form-select form-select-sm" name="status">{options}</select>'
        f'<button type="submit" class="btn btn-sm btn-outline-primary">Move</button>'
        f"</form>"
    )
    return f'<article class="list-group-item" data-id="{todo_id}">{text}{form}</article>'


def render_board(todos):
    sections = []
    for status in STATUSES:
        items = [t for t in todos if isinstance(t, dict) and t.get("status") == status]
        items.sort(key=lambda t: t.get("id") if isinstance(t.get("id"), int) else 0)
        articles = "".join(_render_todo(t) for t in items)
        sections.append(
            f'<section class="card" style="width: 20rem" data-status="{status}">'
            f'<h2 class="card-header h5">{HEADINGS[status]}</h2>'
            f'<div class="list-group list-group-flush">{articles}</div>'
            f"</section>"
        )
    sections_html = "".join(sections)
    return (
        "<!DOCTYPE html>\n"
        '<html><head><meta charset="utf-8"><title>Board</title>'
        '<link rel="stylesheet" href="/static/bootstrap.min.css">'
        "</head>"
        f'<body><main class="d-flex align-items-start gap-3 p-3" style="flex-wrap: nowrap">{sections_html}</main></body></html>\n'
    )


class BoardRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path

        # Serve static files
        if path.startswith("/static/"):
            self._serve_static(path)
            return

        if path != "/":
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        try:
            todos = load_todos(store_path())
        except UnsupportedStoreVersion as exc:
            message = f"Unsupported store version: {exc}"
            self._send_error_text(500, message)
            return
        except InvalidStoreItem as exc:
            message = f"Invalid store item {exc}"
            self._send_error_text(500, message)
            return

        body = render_board(todos).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path):
        # Only GET allowed
        if self.command != "GET":
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Extract filename from path
        filename = path[len("/static/") :]
        if not filename or filename == "/":
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # URL decode
        filename = unquote(filename)

        # Prevent path traversal
        try:
            requested_path = (STATIC_DIR / filename).resolve()
            static_dir_resolved = STATIC_DIR.resolve()
            # Check if requested path is within static directory
            if not requested_path.is_relative_to(static_dir_resolved):
                raise ValueError("Path traversal")
        except ValueError, OSError:
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Check if file exists and is a file (not directory)
        if not requested_path.is_file():
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(requested_path))
        if content_type is None:
            content_type = "application/octet-stream"
        elif content_type.startswith("text/"):
            content_type += "; charset=utf-8"

        # Read and serve file
        try:
            body = requested_path.read_bytes()
        except OSError:
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_text(self, status, message):
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/move":
            body = b"Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        length = 0
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except TypeError, ValueError:
            length = 0
        raw = self.rfile.read(length).decode("utf-8", "replace")
        fields = parse_qs(raw, keep_blank_values=True)

        id_values = fields.get("id")
        status_values = fields.get("status")
        if not id_values or not status_values:
            self._send_error_text(400, "")
            return
        id_raw = id_values[0]
        status = status_values[0]

        if not id_raw or not id_raw.isdigit() or not id_raw.isascii() or status not in STATUSES:
            self._send_error_text(400, "")
            return

        todo_id = int(id_raw)

        try:
            todos = load_todos(store_path())
        except UnsupportedStoreVersion as exc:
            message = f"Unsupported store version: {exc}"
            self._send_error_text(500, message)
            return
        except InvalidStoreItem as exc:
            message = f"Invalid store item {exc}"
            self._send_error_text(500, message)
            return

        try:
            changed = move_todo(todos, todo_id, status)
        except UnknownTodoId as exc:
            self._send_error_text(404, f"Unknown id: {exc.todo_id}")
            return

        if changed:
            save_todos(store_path(), todos)

        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Content-Length", "0")
        self.end_headers()


def make_server(host, port):
    return http.server.ThreadingHTTPServer((host, port), BoardRequestHandler)
