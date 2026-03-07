"""Tests for nlp_parser — heuristic parsing, JSON extraction, and AI integration."""

import json
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from products.fred_assistant.services.nlp_parser import (
    parse_capture_text,
    _heuristic_parse,
    _extract_json,
)


# ── Heuristic: priority ─────────────────────────────────────────────


def test_heuristic_urgent_priority():
    r = _heuristic_parse("Fix the login bug urgent", "work")
    assert r["priority"] == 1


def test_heuristic_asap_priority():
    r = _heuristic_parse("Deploy ASAP", "work")
    assert r["priority"] == 1


def test_heuristic_critical_priority():
    r = _heuristic_parse("Critical production outage", "work")
    assert r["priority"] == 1


def test_heuristic_important_priority():
    r = _heuristic_parse("Important client meeting", "work")
    assert r["priority"] == 2


def test_heuristic_high_priority():
    r = _heuristic_parse("High priority review", "work")
    assert r["priority"] == 2


def test_heuristic_low_priority():
    r = _heuristic_parse("Low priority cleanup", "work")
    assert r["priority"] == 5


def test_heuristic_no_priority():
    r = _heuristic_parse("Buy groceries", "work")
    assert "priority" not in r


# ── Heuristic: board detection ───────────────────────────────────────


def test_heuristic_gym_board():
    r = _heuristic_parse("Go to the gym", "work")
    assert r["board_id"] == "health"


def test_heuristic_research_board():
    r = _heuristic_parse("Research new frameworks", "work")
    assert r["board_id"] == "ideas"


def test_heuristic_personal_board():
    r = _heuristic_parse("Call the dentist for appointment", "work")
    assert r["board_id"] == "personal"


def test_heuristic_code_board():
    r = _heuristic_parse("Fix the deploy script", "work")
    assert r["board_id"] == "elgringo"


def test_heuristic_default_board_preserved():
    r = _heuristic_parse("Some random task", "myboard")
    assert r["board_id"] == "myboard"


# ── Heuristic: tags ──────────────────────────────────────────────────


def test_heuristic_extracts_hashtags():
    r = _heuristic_parse("Fix login #backend #auth", "work")
    assert "backend" in r["tags"]
    assert "auth" in r["tags"]
    assert "#" not in r["title"]


def test_heuristic_no_tags():
    r = _heuristic_parse("Simple task", "work")
    assert "tags" not in r


# ── Heuristic: dates ─────────────────────────────────────────────────


def test_heuristic_tomorrow():
    r = _heuristic_parse("Submit report tomorrow", "work")
    expected = (date.today() + timedelta(days=1)).isoformat()
    assert r["due_date"] == expected


def test_heuristic_today():
    r = _heuristic_parse("Finish this today", "work")
    assert r["due_date"] == date.today().isoformat()


def test_heuristic_by_friday():
    r = _heuristic_parse("Fix the bug by friday", "work")
    assert r.get("due_date") is not None
    # Should be a valid ISO date
    parsed = date.fromisoformat(r["due_date"])
    assert parsed.weekday() == 4  # Friday


def test_heuristic_on_monday():
    r = _heuristic_parse("Meeting on monday", "work")
    assert r.get("due_date") is not None
    parsed = date.fromisoformat(r["due_date"])
    assert parsed.weekday() == 0  # Monday


def test_heuristic_no_date():
    r = _heuristic_parse("Random task", "work")
    assert "due_date" not in r


# ── Heuristic: recurring ─────────────────────────────────────────────


def test_heuristic_every_day():
    r = _heuristic_parse("Check emails every day", "work")
    assert r["recurring"] == "daily"


def test_heuristic_every_week():
    r = _heuristic_parse("Team standup every week", "work")
    assert r["recurring"] == "weekly"


def test_heuristic_monthly():
    r = _heuristic_parse("Monthly invoice review", "work")
    assert r["recurring"] == "monthly"


# ── Heuristic: title cleanup ─────────────────────────────────────────


def test_heuristic_title_strips_urgent():
    r = _heuristic_parse("Fix login urgent", "work")
    assert "urgent" not in r["title"].lower()
    assert "fix login" in r["title"].lower()


def test_heuristic_title_strips_date_ref():
    r = _heuristic_parse("Submit report by friday", "work")
    assert "by friday" not in r["title"].lower()
    assert "submit report" in r["title"].lower()


def test_heuristic_title_strips_recurring():
    r = _heuristic_parse("Check emails every day", "work")
    assert "every day" not in r["title"].lower()
    assert "check emails" in r["title"].lower()


# ── JSON extraction ──────────────────────────────────────────────────


def test_extract_plain_json():
    result = _extract_json('{"title": "Test", "priority": 1}')
    assert result == {"title": "Test", "priority": 1}


def test_extract_fenced_json():
    result = _extract_json('```json\n{"title": "Test", "priority": 2}\n```')
    assert result == {"title": "Test", "priority": 2}


def test_extract_embedded_json():
    result = _extract_json('Here is the result: {"title": "Test"} that I parsed.')
    assert result == {"title": "Test"}


def test_extract_invalid_json():
    result = _extract_json("This is not JSON at all")
    assert result is None


def test_extract_empty():
    assert _extract_json("") is None
    assert _extract_json(None) is None


# ── Integration: AI available ────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_available_uses_ai_result():
    """When AI returns valid JSON, result should be marked as AI-parsed."""
    ai_response = json.dumps({
        "title": "Fix the login bug",
        "priority": 1,
        "due_date": "2026-02-28",
        "board_id": "work",
        "tags": ["backend"],
    })
    mock_agent = MagicMock()
    mock_resp = MagicMock()
    mock_resp.error = None
    mock_resp.content = ai_response
    mock_agent.generate_response = AsyncMock(return_value=mock_resp)

    with patch("products.fred_assistant.services.assistant._get_gemini", return_value=mock_agent):
        result = await parse_capture_text("Fix the login bug by Friday urgent #backend")

    assert result["_parsed_by"] == "ai"
    assert result["title"] == "Fix the login bug"
    assert result["priority"] == 1
    assert "backend" in result["tags"]


@pytest.mark.asyncio
async def test_ai_unavailable_falls_back():
    """When Gemini is not available, should use heuristic."""
    with patch("products.fred_assistant.services.assistant._get_gemini", return_value=None):
        result = await parse_capture_text("Fix the login bug urgent")

    assert result["_parsed_by"] == "heuristic"
    assert result["priority"] == 1


@pytest.mark.asyncio
async def test_ai_returns_garbage_falls_back():
    """When AI returns unparseable text, should gracefully fall back."""
    mock_agent = MagicMock()
    mock_resp = MagicMock()
    mock_resp.error = None
    mock_resp.content = "I don't understand the request"
    mock_agent.generate_response = AsyncMock(return_value=mock_resp)

    with patch("products.fred_assistant.services.assistant._get_gemini", return_value=mock_agent):
        result = await parse_capture_text("Fix the login bug urgent")

    assert result["_parsed_by"] == "heuristic"
    assert result["priority"] == 1


@pytest.mark.asyncio
async def test_ai_null_fields_filled_by_heuristic():
    """When AI returns null for some fields, heuristic fills gaps."""
    ai_response = json.dumps({
        "title": "Fix the login bug",
        "priority": None,
        "board_id": None,
        "tags": None,
    })
    mock_agent = MagicMock()
    mock_resp = MagicMock()
    mock_resp.error = None
    mock_resp.content = ai_response
    mock_agent.generate_response = AsyncMock(return_value=mock_resp)

    with patch("products.fred_assistant.services.assistant._get_gemini", return_value=mock_agent):
        result = await parse_capture_text("Fix the login bug urgent #backend", "elgringo")

    assert result["_parsed_by"] == "ai"
    # Heuristic should fill in priority and board
    assert result["priority"] == 1  # from heuristic "urgent"
    assert "backend" in result.get("tags", [])  # from heuristic hashtag


@pytest.mark.asyncio
async def test_ai_invalid_board_replaced():
    """When AI suggests a board that doesn't exist, default is used."""
    ai_response = json.dumps({
        "title": "Some task",
        "board_id": "nonexistent_board_xyz",
        "priority": 2,
    })
    mock_agent = MagicMock()
    mock_resp = MagicMock()
    mock_resp.error = None
    mock_resp.content = ai_response
    mock_agent.generate_response = AsyncMock(return_value=mock_resp)

    with patch("products.fred_assistant.services.assistant._get_gemini", return_value=mock_agent):
        result = await parse_capture_text("Some task important", "work")

    assert result["_parsed_by"] == "ai"
    assert result["board_id"] == "work"  # fallback to default


@pytest.mark.asyncio
async def test_ai_exception_falls_back():
    """When AI call raises an exception, should fall back to heuristic."""
    mock_agent = MagicMock()
    mock_agent.generate_response = AsyncMock(side_effect=Exception("API timeout"))

    with patch("products.fred_assistant.services.assistant._get_gemini", return_value=mock_agent):
        result = await parse_capture_text("Deploy the fix asap")

    assert result["_parsed_by"] == "heuristic"
    assert result["priority"] == 1


@pytest.mark.asyncio
async def test_priority_clamped():
    """AI returning out-of-range priority should be clamped to 1-5."""
    ai_response = json.dumps({"title": "Test", "priority": 10})
    mock_agent = MagicMock()
    mock_resp = MagicMock()
    mock_resp.error = None
    mock_resp.content = ai_response
    mock_agent.generate_response = AsyncMock(return_value=mock_resp)

    with patch("products.fred_assistant.services.assistant._get_gemini", return_value=mock_agent):
        result = await parse_capture_text("Test task", "work")

    assert result["priority"] <= 5
