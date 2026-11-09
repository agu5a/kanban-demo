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


# New tests for Bootstrap 5.3.8 layout


@pytest.mark.ui
def test_bootstrap_css_loads(board_server):
    _seed_store(
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

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(board_server)

        # Check that the static CSS file loads successfully
        response = page.request.get(board_server + "/static/bootstrap.min.css")
        assert response.status == 200

        # Check that body font-family contains system-ui (Bootstrap's default)
        body_font_family = page.evaluate("() => window.getComputedStyle(document.body).fontFamily")
        assert "system-ui" in body_font_family

        browser.close()


@pytest.mark.ui
def test_columns_side_by_side(board_server):
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
        page.set_viewport_size({"width": 1600, "height": 900})
        page.goto(board_server)

        todo_section = page.locator('section[data-status="todo"]')
        in_progress_section = page.locator('section[data-status="in-progress"]')
        done_section = page.locator('section[data-status="done"]')

        # Get bounding boxes
        todo_box = todo_section.bounding_box()
        in_progress_box = in_progress_section.bounding_box()
        done_box = done_section.bounding_box()

        assert todo_box is not None
        assert in_progress_box is not None
        assert done_box is not None

        # Same top (±2 px)
        assert abs(todo_box["y"] - in_progress_box["y"]) <= 2
        assert abs(in_progress_box["y"] - done_box["y"]) <= 2

        # Increasing left edges (side by side)
        assert todo_box["x"] < in_progress_box["x"]
        assert in_progress_box["x"] < done_box["x"]

        # No overlap
        assert todo_box["x"] + todo_box["width"] <= in_progress_box["x"]
        assert in_progress_box["x"] + in_progress_box["width"] <= done_box["x"]

        # Each 300-340 px wide (20rem ≈ 320px)
        assert 300 <= todo_box["width"] <= 340
        assert 300 <= in_progress_box["width"] <= 340
        assert 300 <= done_box["width"] <= 340

        browser.close()


@pytest.mark.ui
def test_board_starts_left_and_does_not_fill_width(board_server):
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
        page.set_viewport_size({"width": 1600, "height": 900})
        page.goto(board_server)

        todo_section = page.locator('section[data-status="todo"]')
        done_section = page.locator('section[data-status="done"]')

        todo_box = todo_section.bounding_box()
        done_box = done_section.bounding_box()

        assert todo_box is not None
        assert done_box is not None

        # First section's left edge < 50 px
        assert todo_box["x"] < 50

        # Last section's right edge < 1200 px
        done_right_edge = done_box["x"] + done_box["width"]
        assert done_right_edge < 1200

        browser.close()


@pytest.mark.ui
def test_no_navigation(board_server):
    _seed_store(
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

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(board_server)

        # No nav element
        assert page.locator("nav").count() == 0

        # No element with class navbar
        assert page.locator(".navbar").count() == 0

        browser.close()
