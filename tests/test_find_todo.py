import todo


def test_find_todo_found():
    todos = [{"id": 1, "title": "Buy milk"}]
    result = todo.find_todo(todos, 1)
    assert result is todos[0]


def test_find_todo_missing_id():
    todos = [{"id": 1, "title": "Buy milk"}]
    assert todo.find_todo(todos, 999) is None


def test_find_todo_skips_non_dict_items():
    todos = [42, "not a todo", None, {"id": 1, "title": "Buy milk"}]
    result = todo.find_todo(todos, 1)
    assert result == {"id": 1, "title": "Buy milk"}


def test_find_todo_does_not_match_string_id():
    todos = [{"id": "1", "title": "string id"}]
    assert todo.find_todo(todos, 1) is None
