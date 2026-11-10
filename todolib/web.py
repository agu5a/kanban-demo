"""Web board: render the store as HTML over HTTP; move items and add new ones with form posts."""

import argparse
import html
import http.server
import mimetypes
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from todolib.model import (
    UnknownTodoId,
    _date_type,
    _next_id,
    _title_type,
    move_todo,
    parse_labels,
    parse_priority,
)
from todolib.render import todo_suffixes
from todolib.store import (
    InvalidStoreFile,
    InvalidStoreItem,
    UnsupportedStoreVersion,
    load_todos,
    normalize_todo,
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


NEW_TODO_BUTTON = (
    '<div class="px-3 pt-3">'
    '<button type="button" class="btn btn-primary" data-action="new-todo">New todo</button>'
    "</div>"
)

NEW_TODO_DIALOG = (
    '<dialog id="new-todo-dialog">'
    '<form method="post" action="/add">'
    '<label class="form-label" for="new-todo-title">Title</label>'
    '<input class="form-control" id="new-todo-title" name="title" required>'
    '<label class="form-label" for="new-todo-priority">Priority</label>'
    '<select class="form-select" id="new-todo-priority" name="priority">'
    '<option value="low">low</option>'
    '<option value="normal" selected>normal</option>'
    '<option value="high">high</option>'
    "</select>"
    '<label class="form-label" for="new-todo-due">Due</label>'
    '<input class="form-control" type="date" id="new-todo-due" name="due">'
    '<label class="form-label" for="new-todo-labels">Labels</label>'
    '<input class="form-control" id="new-todo-labels" name="labels">'
    '<div class="d-flex gap-2 mt-3">'
    '<button type="submit" class="btn btn-primary">Create</button>'
    '<button type="button" class="btn btn-secondary" data-action="cancel">Cancel</button>'
    "</div>"
    "</form>"
    "</dialog>"
)


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
        '<script src="/static/board.js" defer></script>'
        "</head>"
        f"<body>{NEW_TODO_BUTTON}"
        f'<main class="d-flex align-items-start gap-3 p-3">{sections_html}</main>'
        f"{NEW_TODO_DIALOG}</body></html>\n"
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
            self._send_error_text(404, "Not Found")
            return

        todos = self._load_store()
        if todos is None:
            return

        body = render_board(todos).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _load_store(self):
        """The store's items, or None after sending the 500 for a store error."""
        try:
            return load_todos(store_path())
        except UnsupportedStoreVersion as exc:
            self._send_error_text(500, f"Unsupported store version: {exc}")
        except InvalidStoreItem as exc:
            self._send_error_text(500, f"Invalid store item {exc}")
        except InvalidStoreFile as exc:
            self._send_error_text(500, f"Invalid store file: {exc}")
        return None

    def _redirect_home(self):
        self.send_response(303)
        self.send_header("Location", "/")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _serve_static(self, path):
        # Only GET allowed
        if self.command != "GET":
            self._send_error_text(404, "Not Found")
            return

        # Extract filename from path
        filename = path[len("/static/") :]
        if not filename or filename == "/":
            self._send_error_text(404, "Not Found")
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
            self._send_error_text(404, "Not Found")
            return

        # Check if file exists and is a file (not directory)
        if not requested_path.is_file():
            self._send_error_text(404, "Not Found")
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
            self._send_error_text(404, "Not Found")
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
        if parsed.path not in ("/move", "/add"):
            self._send_error_text(404, "Not Found")
            return

        length = 0
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except TypeError, ValueError:
            length = 0
        raw = self.rfile.read(length).decode("utf-8", "replace")
        fields = parse_qs(raw, keep_blank_values=True)
        if parsed.path == "/add":
            self._add(fields)
            return

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

        todos = self._load_store()
        if todos is None:
            return

        try:
            changed = move_todo(todos, todo_id, status)
        except UnknownTodoId as exc:
            self._send_error_text(404, f"Unknown id: {exc.todo_id}")
            return

        if changed:
            save_todos(store_path(), todos)

        self._redirect_home()

    def _add(self, fields):
        """POST /add: the rules and messages of `todo.py add`; 400 with the message on bad input."""

        def field(name):
            values = fields.get(name)
            return values[0] if values else None

        try:
            title = _title_type(field("title") or "")
            priority = parse_priority(field("priority") if "priority" in fields else "normal")
            due_raw = field("due")
            due = _date_type(due_raw).isoformat() if due_raw else None
            labels = parse_labels(field("labels") or "")
        except argparse.ArgumentTypeError as exc:
            self._send_error_text(400, str(exc))
            return

        todos = self._load_store()
        if todos is None:
            return
        todos.append(
            normalize_todo(
                {
                    "id": _next_id(todos),
                    "title": title,
                    "priority": priority,
                    "due": due,
                    "labels": labels,
                }
            )
        )
        save_todos(store_path(), todos)
        self._redirect_home()


def make_server(host, port):
    return http.server.ThreadingHTTPServer((host, port), BoardRequestHandler)
