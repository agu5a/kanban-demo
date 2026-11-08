import json
import os
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


def _seed_store(data):
    path = Path(os.environ["TODO_FILE"])
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.ui
def test_board_shows_columns_and_items(board_server):
    _seed_store(
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

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(board_server)
        headings = page.locator("section h2").all_text_contents()
        assert headings == ["To do", "In progress", "Done"]

        todo_section = page.locator('section[data-status="todo"]')
        in_progress_section = page.locator('section[data-status="in-progress"]')
        done_section = page.locator('section[data-status="done"]')

        assert 'data-id="1"' in (todo_section.inner_html())
        assert 'data-id="2"' in (in_progress_section.inner_html())
        assert 'data-id="3"' in (done_section.inner_html())
        browser.close()


@pytest.mark.ui
def test_move_form_moves_item(board_server):
    _seed_store(
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

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(board_server)
        page.locator('article[data-id="1"] select[name="status"]').select_option("done")
        with page.expect_navigation():
            page.locator('article[data-id="1"] button[type="submit"]').click()

        done_section = page.locator('section[data-status="done"]')
        todo_section = page.locator('section[data-status="todo"]')
        assert 'data-id="1"' in done_section.inner_html()
        assert 'data-id="1"' not in todo_section.inner_html()

        store = json.loads(Path(os.environ["TODO_FILE"]).read_text())
        assert store["todos"][0]["status"] == "done"
        browser.close()


@pytest.mark.ui
def test_html_title_shown_as_text(board_server):
    _seed_store(
        {
            "version": 3,
            "todos": [
                {
                    "id": 1,
                    "title": "<b>bold</b>",
                    "status": "todo",
                    "priority": "normal",
                    "due": None,
                    "labels": [],
                }
            ],
        }
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(board_server)
        article = page.locator('article[data-id="1"]')
        assert "<b>bold</b>" in (article.text_content() or "")
        assert article.locator("b").count() == 0
        browser.close()
