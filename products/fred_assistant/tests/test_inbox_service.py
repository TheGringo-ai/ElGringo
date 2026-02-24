"""Tests for inbox_service — unified prioritized inbox."""

import pytest
from datetime import date, timedelta

from products.fred_assistant.services import inbox_service, task_service, crm_service, calendar_service, coach_service


# ── Empty inbox ──────────────────────────────────────────────────

def test_get_inbox_empty():
    items = inbox_service.get_inbox()
    assert items == []


def test_get_inbox_count_empty():
    counts = inbox_service.get_inbox_count()
    assert counts["total"] == 0
    assert counts["by_type"] == {}


# ── Overdue tasks appear in inbox ─────────────────────────────────

def test_inbox_shows_overdue_tasks():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    task_service.create_task({"title": "Overdue task", "due_date": yesterday, "status": "todo"})
    items = inbox_service.get_inbox()
    overdue = [i for i in items if i["type"] == "overdue_task"]
    assert len(overdue) >= 1
    assert overdue[0]["title"] == "Overdue task"
    assert overdue[0]["priority"] == 1


def test_inbox_excludes_done_overdue_tasks():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    task_service.create_task({"title": "Done overdue", "due_date": yesterday, "status": "done"})
    items = inbox_service.get_inbox()
    overdue = [i for i in items if i["type"] == "overdue_task" and i["title"] == "Done overdue"]
    assert len(overdue) == 0


# ── Followup-due leads appear in inbox ────────────────────────────

def test_inbox_shows_followup_due_leads():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    crm_service.create_lead({
        "name": "Important Lead",
        "company": "Acme",
        "next_followup": yesterday,
        "pipeline_stage": "contacted",
    })
    items = inbox_service.get_inbox()
    followups = [i for i in items if i["type"] == "followup_due"]
    assert len(followups) >= 1


# ── Calendar conflicts ────────────────────────────────────────────

def test_inbox_detects_calendar_conflicts():
    today = date.today().isoformat()
    calendar_service.create_event({
        "title": "Meeting A",
        "start_date": today,
        "start_time": "10:00",
        "end_time": "11:00",
    })
    calendar_service.create_event({
        "title": "Meeting B",
        "start_date": today,
        "start_time": "10:30",
        "end_time": "11:30",
    })
    items = inbox_service.get_inbox()
    conflicts = [i for i in items if i["type"] == "calendar_conflict"]
    assert len(conflicts) >= 1


def test_inbox_no_conflict_when_no_overlap():
    today = date.today().isoformat()
    calendar_service.create_event({
        "title": "Morning",
        "start_date": today,
        "start_time": "09:00",
        "end_time": "10:00",
    })
    calendar_service.create_event({
        "title": "Afternoon",
        "start_date": today,
        "start_time": "14:00",
        "end_time": "15:00",
    })
    items = inbox_service.get_inbox()
    conflicts = [i for i in items if i["type"] == "calendar_conflict"]
    assert len(conflicts) == 0


# ── Stale goals ──────────────────────────────────────────────────

def test_inbox_shows_stale_goals():
    from products.fred_assistant.database import get_conn
    goal = coach_service.create_goal({"title": "Stale goal"})
    # Manually backdate the updated_at to 30 days ago
    old_date = (date.today() - timedelta(days=30)).isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE goals SET updated_at=? WHERE id=?", (old_date, goal["id"]))
    items = inbox_service.get_inbox()
    stale = [i for i in items if i["type"] == "stale_goal"]
    assert len(stale) >= 1


# ── Sort by priority ─────────────────────────────────────────────

def test_inbox_sorted_by_priority():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    task_service.create_task({"title": "Overdue", "due_date": yesterday, "status": "todo"})  # priority 1
    # Create a stale goal for priority 3
    from products.fred_assistant.database import get_conn
    goal = coach_service.create_goal({"title": "Stale"})
    old_date = (date.today() - timedelta(days=30)).isoformat()
    with get_conn() as conn:
        conn.execute("UPDATE goals SET updated_at=? WHERE id=?", (old_date, goal["id"]))

    items = inbox_service.get_inbox()
    if len(items) >= 2:
        # Priority values should be non-decreasing
        priorities = [i["priority"] for i in items]
        assert priorities == sorted(priorities)


# ── Inbox count ──────────────────────────────────────────────────

def test_get_inbox_count_with_items():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    task_service.create_task({"title": "Overdue 1", "due_date": yesterday, "status": "todo"})
    task_service.create_task({"title": "Overdue 2", "due_date": yesterday, "status": "in_progress"})
    counts = inbox_service.get_inbox_count()
    assert counts["total"] >= 2
    assert counts["by_type"].get("overdue_task", 0) >= 2
