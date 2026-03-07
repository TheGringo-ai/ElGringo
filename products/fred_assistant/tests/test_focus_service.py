"""Tests for focus_service — Focus Mode sessions."""

from products.fred_assistant.services import focus_service, task_service


def test_start_focus_no_task():
    session = focus_service.start_focus(planned_minutes=25)
    assert session["id"]
    assert session["planned_minutes"] == 25
    assert session["task_id"] is None
    assert session["completed"] is False


def test_start_focus_with_task():
    task = task_service.create_task({"board_id": "work", "title": "Test task"})
    session = focus_service.start_focus(task_id=task["id"], planned_minutes=50)
    assert session["task_id"] == task["id"]
    assert session["task_title"] == "Test task"
    assert session["planned_minutes"] == 50


def test_get_active_session():
    assert focus_service.get_active_session() is None
    focus_service.start_focus(planned_minutes=25)
    active = focus_service.get_active_session()
    assert active is not None
    assert active["planned_minutes"] == 25


def test_end_focus():
    session = focus_service.start_focus(planned_minutes=25)
    ended = focus_service.end_focus(session_id=session["id"], completed=True, notes="Great session")
    assert ended["ended_at"] is not None
    assert ended["completed"] is True
    assert ended["notes"] == "Great session"
    assert focus_service.get_active_session() is None


def test_end_focus_auto_finds_active():
    focus_service.start_focus(planned_minutes=25)
    ended = focus_service.end_focus()
    assert ended is not None
    assert ended["ended_at"] is not None


def test_end_focus_no_active():
    result = focus_service.end_focus()
    assert result is None


def test_focus_stats_empty():
    stats = focus_service.get_focus_stats(days=7)
    assert stats["total_sessions"] == 0
    assert stats["total_minutes"] == 0


def test_list_sessions():
    focus_service.start_focus(planned_minutes=25)
    focus_service.end_focus()
    sessions = focus_service.list_sessions(days=7)
    assert len(sessions) >= 1
