import threading

import pytest

from todolib.web import make_server


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    """Every test gets its own store; nothing touches the committed data/todos.db by accident."""
    monkeypatch.setenv("TODO_FILE", str(tmp_path / "todos.json"))


@pytest.fixture
def board_server(tmp_path, monkeypatch):
    store = tmp_path / "todos.json"
    monkeypatch.setenv("TODO_FILE", str(store))
    server = make_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    yield base_url
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
