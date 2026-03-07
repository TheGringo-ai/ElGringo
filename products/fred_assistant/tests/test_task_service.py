"""Tests for task_service — task + board management."""

import json
from datetime import date

from products.fred_assistant.services import task_service


# ── Board tests ───────────────────────────────────────────────────

def test_create_board():
    board = task_service.create_board("Test Board")
    assert board["name"] == "Test Board"
    assert board["id"] == "test_board"
    assert "todo" in board["columns"]


def test_list_boards_empty():
    boards = task_service.list_boards()
    # init_db seeds default boards (Work, Personal, etc.)
    assert isinstance(boards, list)


def test_get_board():
    board = task_service.create_board("Lookup Board")
    fetched = task_service.get_board(board["id"])
    assert fetched is not None
    assert fetched["name"] == "Lookup Board"


def test_get_board_not_found():
    assert task_service.get_board("nonexistent") is None


def test_board_task_count():
    board = task_service.create_board("Count Board")
    task_service.create_task({"title": "T1", "board_id": board["id"]})
    task_service.create_task({"title": "T2", "board_id": board["id"]})
    refreshed = task_service.get_board(board["id"])
    assert refreshed["task_count"] == 2


# ── Task CRUD ────────────────────────────────────────────────────

def test_create_task_minimal():
    task = task_service.create_task({"title": "Buy milk"})
    assert task["title"] == "Buy milk"
    assert task["status"] == "todo"
    assert task["board_id"] == "work"
    assert task["id"]


def test_create_task_all_fields():
    task = task_service.create_task({
        "title": "Full task",
        "description": "Everything set",
        "board_id": "personal",
        "status": "in_progress",
        "priority": 1,
        "category": "dev",
        "due_date": "2026-03-01",
        "due_time": "09:00",
        "tags": ["urgent", "code"],
        "notes": "Some notes",
    })
    assert task["title"] == "Full task"
    assert task["board_id"] == "personal"
    assert task["status"] == "in_progress"
    assert task["priority"] == 1
    assert task["tags"] == ["urgent", "code"]


def test_create_task_tags_stored_as_json():
    task = task_service.create_task({"title": "Tagged", "tags": ["a", "b"]})
    assert task["tags"] == ["a", "b"]


def test_get_task():
    task = task_service.create_task({"title": "Fetch me"})
    fetched = task_service.get_task(task["id"])
    assert fetched["title"] == "Fetch me"


def test_get_task_not_found():
    assert task_service.get_task("nonexistent") is None


def test_update_task_status():
    task = task_service.create_task({"title": "Update me"})
    updated = task_service.update_task(task["id"], {"status": "in_progress"})
    assert updated["status"] == "in_progress"


def test_update_task_title():
    task = task_service.create_task({"title": "Old title"})
    updated = task_service.update_task(task["id"], {"title": "New title"})
    assert updated["title"] == "New title"


def test_update_task_done_sets_completed_at():
    task = task_service.create_task({"title": "Complete me"})
    updated = task_service.update_task(task["id"], {"status": "done"})
    assert updated["completed_at"] is not None


def test_update_task_tags():
    task = task_service.create_task({"title": "Tag me", "tags": ["old"]})
    updated = task_service.update_task(task["id"], {"tags": ["new", "fresh"]})
    assert updated["tags"] == ["new", "fresh"]


def test_delete_task():
    task = task_service.create_task({"title": "Delete me"})
    task_service.delete_task(task["id"])
    assert task_service.get_task(task["id"]) is None


def test_delete_task_nonexistent():
    # Should not raise
    task_service.delete_task("nonexistent_id")


# ── Listing + filtering ──────────────────────────────────────────

def test_list_tasks_empty():
    assert task_service.list_tasks() == []


def test_list_tasks_returns_all():
    task_service.create_task({"title": "A"})
    task_service.create_task({"title": "B"})
    assert len(task_service.list_tasks()) == 2


def test_list_tasks_filter_by_board():
    task_service.create_task({"title": "Work task", "board_id": "work"})
    task_service.create_task({"title": "Personal task", "board_id": "personal"})
    work_tasks = task_service.list_tasks(board_id="work")
    assert len(work_tasks) == 1
    assert work_tasks[0]["title"] == "Work task"


def test_list_tasks_filter_by_status():
    task_service.create_task({"title": "Todo task", "status": "todo"})
    task_service.create_task({"title": "Done task", "status": "done"})
    todo = task_service.list_tasks(status="todo")
    assert all(t["status"] == "todo" for t in todo)


def test_list_tasks_filter_by_due_date():
    task_service.create_task({"title": "Due today", "due_date": "2026-03-01"})
    task_service.create_task({"title": "Due tomorrow", "due_date": "2026-03-02"})
    results = task_service.list_tasks(due_date="2026-03-01")
    assert len(results) == 1
    assert results[0]["title"] == "Due today"


# ── _row_to_task edge cases ──────────────────────────────────────

def test_row_to_task_double_encoded_tags():
    """Double-encoded JSON string should be decoded properly."""
    from products.fred_assistant.database import get_conn
    task = task_service.create_task({"title": "Double encoded"})
    # Manually double-encode the tags in the DB
    double_encoded = json.dumps(json.dumps(["a", "b"]))
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET tags=? WHERE id=?", (double_encoded, task["id"]))
    fetched = task_service.get_task(task["id"])
    assert fetched["tags"] == ["a", "b"]


def test_row_to_task_malformed_tags():
    """Malformed JSON tags should return empty list."""
    from products.fred_assistant.database import get_conn
    task = task_service.create_task({"title": "Bad tags"})
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET tags=? WHERE id=?", ("not json at all{{{", task["id"]))
    fetched = task_service.get_task(task["id"])
    assert fetched["tags"] == []


def test_row_to_task_plain_list_tags():
    """Normal JSON list tags should parse correctly."""
    task = task_service.create_task({"title": "Normal", "tags": ["x", "y"]})
    fetched = task_service.get_task(task["id"])
    assert fetched["tags"] == ["x", "y"]


# ── Dashboard stats ──────────────────────────────────────────────

def test_get_dashboard_stats_empty():
    stats = task_service.get_dashboard_stats()
    assert stats["total_tasks"] == 0
    assert stats["completed_today"] == 0
    assert stats["overdue"] == 0


def test_get_dashboard_stats_with_tasks():
    task_service.create_task({"title": "Active"})
    task_service.create_task({"title": "In progress", "status": "in_progress"})
    stats = task_service.get_dashboard_stats()
    assert stats["total_tasks"] == 2
    assert stats["in_progress"] == 1


def test_get_today_tasks():
    today = date.today().isoformat()
    task_service.create_task({"title": "Due today", "due_date": today})
    task_service.create_task({"title": "In progress", "status": "in_progress"})
    today_tasks = task_service.get_today_tasks()
    assert len(today_tasks) >= 1
