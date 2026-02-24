"""Tests for calendar_service — events, time blocking, deadlines."""

import pytest
from datetime import date, timedelta
from products.fred_assistant.services import calendar_service


# ── Event CRUD ────────────────────────────────────────────────────

def test_create_event_minimal():
    event = calendar_service.create_event({
        "title": "Team standup",
        "start_date": "2026-03-01",
    })
    assert event["title"] == "Team standup"
    assert event["start_date"] == "2026-03-01"
    assert event["event_type"] == "event"
    assert event["id"]


def test_create_event_all_fields():
    event = calendar_service.create_event({
        "title": "Workshop",
        "description": "AI workshop",
        "event_type": "meeting",
        "start_date": "2026-03-01",
        "start_time": "09:00",
        "end_date": "2026-03-01",
        "end_time": "17:00",
        "all_day": False,
        "recurring": "weekly",
        "color": "green",
        "location": "Office",
    })
    assert event["event_type"] == "meeting"
    assert event["start_time"] == "09:00"
    assert event["end_time"] == "17:00"
    assert event["location"] == "Office"
    assert event["color"] == "green"


def test_get_event():
    event = calendar_service.create_event({"title": "Fetch me", "start_date": "2026-03-01"})
    fetched = calendar_service.get_event(event["id"])
    assert fetched["title"] == "Fetch me"


def test_get_event_not_found():
    assert calendar_service.get_event("nonexistent") is None


def test_update_event_title():
    event = calendar_service.create_event({"title": "Old title", "start_date": "2026-03-01"})
    updated = calendar_service.update_event(event["id"], {"title": "New title"})
    assert updated["title"] == "New title"


def test_update_event_time():
    event = calendar_service.create_event({
        "title": "Reschedule me",
        "start_date": "2026-03-01",
        "start_time": "09:00",
    })
    updated = calendar_service.update_event(event["id"], {"start_time": "14:00"})
    assert updated["start_time"] == "14:00"


def test_update_event_not_found():
    result = calendar_service.update_event("nonexistent", {"title": "nope"})
    assert result is None


def test_delete_event():
    event = calendar_service.create_event({"title": "Delete me", "start_date": "2026-03-01"})
    calendar_service.delete_event(event["id"])
    assert calendar_service.get_event(event["id"]) is None


# ── Listing + date range filtering ───────────────────────────────

def test_list_events_empty():
    assert calendar_service.list_events() == []


def test_list_events_returns_all():
    calendar_service.create_event({"title": "A", "start_date": "2026-03-01"})
    calendar_service.create_event({"title": "B", "start_date": "2026-03-02"})
    assert len(calendar_service.list_events()) == 2


def test_list_events_filter_by_date_range():
    calendar_service.create_event({"title": "March 1", "start_date": "2026-03-01"})
    calendar_service.create_event({"title": "March 5", "start_date": "2026-03-05"})
    calendar_service.create_event({"title": "March 10", "start_date": "2026-03-10"})
    results = calendar_service.list_events(start_date="2026-03-01", end_date="2026-03-05")
    assert len(results) == 2


def test_list_events_filter_by_type():
    calendar_service.create_event({"title": "Meeting", "start_date": "2026-03-01", "event_type": "meeting"})
    calendar_service.create_event({"title": "Deadline", "start_date": "2026-03-01", "event_type": "deadline"})
    meetings = calendar_service.list_events(event_type="meeting")
    assert len(meetings) == 1
    assert meetings[0]["event_type"] == "meeting"


# ── Today / week / upcoming ──────────────────────────────────────

def test_get_today_events():
    today = date.today().isoformat()
    calendar_service.create_event({"title": "Today event", "start_date": today})
    calendar_service.create_event({"title": "Tomorrow", "start_date": (date.today() + timedelta(days=1)).isoformat()})
    today_events = calendar_service.get_today_events()
    assert len(today_events) == 1
    assert today_events[0]["title"] == "Today event"


def test_get_week_events():
    today = date.today()
    calendar_service.create_event({"title": "This week", "start_date": today.isoformat()})
    far_future = (today + timedelta(days=30)).isoformat()
    calendar_service.create_event({"title": "Far future", "start_date": far_future})
    week = calendar_service.get_week_events()
    titles = [e["title"] for e in week]
    assert "This week" in titles
    assert "Far future" not in titles


def test_get_upcoming():
    today = date.today()
    calendar_service.create_event({"title": "Soon", "start_date": (today + timedelta(days=2)).isoformat()})
    calendar_service.create_event({"title": "Far", "start_date": (today + timedelta(days=30)).isoformat()})
    upcoming = calendar_service.get_upcoming(days=7)
    titles = [e["title"] for e in upcoming]
    assert "Soon" in titles
    assert "Far" not in titles
