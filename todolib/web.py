"""Read-only web board: render the store as HTML over HTTP."""

import html
import http.server
from urllib.parse import urlsplit

from todolib.render import todo_suffixes
from todolib.store import (
    InvalidStoreItem,
    UnsupportedStoreVersion,
    load_todos,
    store_path,
)

STATUSES = ("todo", "in-progress", "done")
HEADINGS = {
    "todo": "To do",
    "in-progress": "In progress",
    "done": "Done",
}


def _render_todo(todo):
    todo_id = todo.get("id")
    title = todo.get("title", "")
    text = f"#{todo_id} {html.escape(title)}{html.escape(todo_suffixes(todo))}"
    return f'<article data-id="{todo_id}">{text}</article>'


def render_board(todos):
    sections = []
    for status in STATUSES:
        items = [t for t in todos if isinstance(t, dict) and t.get("status") == status]
        items.sort(key=lambda t: t.get("id") if isinstance(t.get("id"), int) else 0)
        articles = "".join(_render_todo(t) for t in items)
        sections.append(
            f'<section data-status="{status}"><h2>{HEADINGS[status]}</h2>{articles}</section>'
        )
    return (
        "<!DOCTYPE html>\n"
        '<html><head><meta charset="utf-8"><title>Board</title></head>'
        f"<body>{''.join(sections)}</body></html>\n"
    )


class BoardRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/":
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

    def _send_error_text(self, status, message):
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()


def make_server(host, port):
    return http.server.ThreadingHTTPServer((host, port), BoardRequestHandler)
